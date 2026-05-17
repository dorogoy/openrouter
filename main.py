#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "requests>=2.32.4",
#   "rich>=14.1.0",
#   "inquirer",
# ]
# ///
"""
OpenRouter Model Viewer — browse, filter, sort, and export AI model listings
with precise pricing, context windows, and modality support.
"""

import argparse
import csv
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta
from io import StringIO
from typing import Any

import inquirer
import requests
from rich.console import Console
from rich.table import Table
from rich.text import Text

API_URL = "https://openrouter.ai/api/v1/models"
HEADERS = ["Model", "Provider", "Context", "Modality", "Cost/1M In", "Cost/1M Out"]
SORT_COLUMNS = {
    "model": "Model",
    "provider": "Provider",
    "context": "Context",
    "price-in": "Cost/1M In",
    "price-out": "Cost/1M Out",
}
OUTPUT_FORMATS = ("table", "json", "csv")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fmt_context(tokens: int | None) -> str:
    """Human-readable context length."""
    if not tokens:
        return "-"
    if tokens >= 1_000_000:
        return f"{tokens / 1_000_000:.1f}M"
    if tokens >= 1_000:
        return f"{tokens // 1_000:,}K"
    return str(tokens)


def _fmt_modality(arch: dict | None) -> str:
    """Short modality description: T=text, I=image, F=file."""
    if not arch or not arch.get("input_modalities"):
        return "-"
    modalities = arch["input_modalities"]
    chars = []
    for m in modalities:
        if m == "text":
            chars.append("T")
        elif m == "image":
            chars.append("I")
        elif m == "file":
            chars.append("F")
        elif m == "audio":
            chars.append("A")
        elif m == "video":
            chars.append("V")
        else:
            chars.append(m[0].upper())
    return "+".join(chars) + "→T"


def _price_style(price_str: str) -> Text:
    """Return a Rich Text for a price, colored by magnitude."""
    text = Text(price_str)
    if price_str in ("-", "Free", "dynamic"):
        text.stylize("dim")
        return text
    try:
        val = float(price_str.lstrip("$").replace("¢", ""))
        if "¢" in price_str:
            val /= 100
        if val < 0.01:
            text.stylize("green")
        elif val < 1:
            text.stylize("yellow")
        else:
            text.stylize("red")
    except (ValueError, TypeError):
        pass
    return text


# ---------------------------------------------------------------------------
# ModelViewer
# ---------------------------------------------------------------------------


class ModelViewer:
    """OpenRouter model browser with caching, filtering, sorting, and export."""

    def __init__(self):
        self.console = Console()

    # ---- data fetching ----

    def fetch_models(self) -> dict:
        """Fetch models from OpenRouter API with a daily temp-dir cache."""
        cache_file = os.path.join(tempfile.gettempdir(), "openrouter_models_cache.json")
        now = datetime.now()

        # load cache if fresh
        if os.path.exists(cache_file):
            try:
                with open(cache_file, encoding="utf-8") as f:
                    cache = json.load(f)
                cache_time = datetime.fromisoformat(
                    cache.get("fetched_at", "1970-01-01T00:00:00")
                )
                if now - cache_time < timedelta(days=1) and "data" in cache:
                    return {"data": cache["data"]}
            except Exception:
                pass

        # fetch fresh data
        try:
            response = requests.get(API_URL, timeout=15)
            response.raise_for_status()
            data = response.json().get("data", [])
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump({"fetched_at": now.isoformat(), "data": data}, f)
            return {"data": data}
        except requests.RequestException as exc:
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, encoding="utf-8") as f:
                        cache = json.load(f)
                    if "data" in cache:
                        self.console.print(
                            "[yellow][WARN][/] Network error — using cached data."
                        )
                        return {"data": cache["data"]}
                except Exception:
                    pass
            raise SystemExit(f"Error fetching models: {exc}") from exc

    # ---- data processing ----

    @staticmethod
    def price_per_million(raw: str | float) -> str:
        """Convert API price-per-token to a human-friendly per‑1M‑tokens string."""
        try:
            cost = float(raw) * 1_000_000
            if cost < 0:
                return "dynamic"
            if cost == 0:
                return "Free"
            if cost < 0.01:
                return f"${cost * 100:.2f}¢"
            if cost < 1:
                return f"${cost:.3f}"
            return f"${cost:.2f}"
        except (ValueError, TypeError):
            return "-"

    @staticmethod
    def price_val(price_str: str) -> float | None:
        """Parse a formatted price string back to a numeric dollar value."""
        if not price_str or price_str in ("-", "Free", "dynamic"):
            return 0.0
        try:
            cleaned = price_str.replace("$", "").replace("¢", "")
            val = float(cleaned)
            return val / 100 if "¢" in price_str else val
        except (ValueError, TypeError):
            return None

    def process_model(self, model: dict) -> dict[str, Any] | None:
        """Extract display fields from a raw API model dict."""
        try:
            raw_name = model.get("name", "-")
            name = raw_name.split("/")[-1] if "/" in raw_name else raw_name

            slug = model.get("canonical_slug", "-")
            provider = slug.split("/")[0] if "/" in slug else "-"

            pricing = model.get("pricing", {})
            price_in = self.price_per_million(pricing.get("prompt", "0"))
            price_out = self.price_per_million(pricing.get("completion", "0"))

            ctx = model.get("context_length") or model.get("top_provider", {}).get(
                "context_length"
            )

            return {
                "Model": name,
                "Provider": provider,
                "Context": _fmt_context(ctx),
                "Modality": _fmt_modality(model.get("architecture")),
                "Cost/1M In": price_in,
                "Cost/1M Out": price_out,
                # hidden helpers (not displayed)
                "_ctx_raw": ctx or 0,
                "_price_in_val": self.price_val(price_in) or 0.0,
                "_price_out_val": self.price_val(price_out) or 0.0,
            }
        except Exception:
            return None

    # ---- filtering & sorting ----

    def filter_models(self, models: list[dict], args) -> list[dict[str, Any]]:
        """Apply CLI / interactive filters and return processed rows."""
        include_free = getattr(args, "include_free", False)
        context_min = self._parse_numeric(
            getattr(args, "context_min", None), "context-min"
        )
        query = (getattr(args, "search", "") or "").lower()

        rows: list[dict[str, Any]] = []
        for model in models:
            row = self.process_model(model)
            if not row:
                continue
            if row["Model"].strip().lower() == "auto router":
                continue

            # text filters
            if args.name and args.name.lower() not in row["Model"].lower():
                continue
            if args.provider and args.provider.lower() not in row["Provider"].lower():
                continue
            slug = model.get("canonical_slug", "").lower()
            if args.slug and args.slug.lower() not in slug:
                continue
            if query:
                desc = (model.get("description") or "").lower()
                if query not in row["Model"].lower() and query not in desc:
                    continue

            # price filters
            is_free = row["_price_in_val"] == 0.0 and row["_price_out_val"] == 0.0
            if not include_free and is_free:
                continue
            if not is_free:
                for attr, field in [
                    ("min_price", "_price_in_val"),
                    ("max_price", "_price_in_val"),
                    ("min_out_price", "_price_out_val"),
                    ("max_out_price", "_price_out_val"),
                ]:
                    val = getattr(args, attr, None)
                    if val is not None:
                        val = float(val)
                        if "min" in attr and row[field] < val:
                            break
                        if "max" in attr and row[field] > val:
                            break
                else:
                    # context filter
                    if context_min is not None and row["_ctx_raw"] < context_min:
                        continue
                    rows.append(row)
                    continue
            else:
                if context_min is not None and row["_ctx_raw"] < context_min:
                    continue
                rows.append(row)

        # sorting
        sort_col = SORT_COLUMNS.get(getattr(args, "sort_by", "price-in"), "Cost/1M In")
        reverse = getattr(args, "sort_dir", "desc") != "asc"

        if sort_col == "Context":
            rows.sort(key=lambda r: r["_ctx_raw"], reverse=reverse)
        elif sort_col == "Cost/1M In":
            rows.sort(key=lambda r: r["_price_in_val"], reverse=reverse)
        elif sort_col == "Cost/1M Out":
            rows.sort(key=lambda r: r["_price_out_val"], reverse=reverse)
        else:
            rows.sort(key=lambda r: r.get(sort_col, "").lower(), reverse=reverse)

        return rows

    # ---- output ----

    def display_table(
        self, rows: list[dict[str, Any]], limit: int | None = None
    ) -> str:
        """Render a Rich table and return the plain-text equivalent for exports."""
        if not rows:
            self.console.print("[bold red]No models match your criteria.[/bold red]")
            return ""

        if limit:
            rows = rows[:limit]

        table = Table(
            title=f"{len(rows)} OpenRouter Models",
            header_style="bold cyan",
            expand=True,
        )
        for col in HEADERS:
            no_wrap = col not in ("Model", "Modality")
            table.add_column(col, style="white", no_wrap=no_wrap)

        for r in rows:
            table.add_row(
                r["Model"],
                r["Provider"],
                r["Context"],
                r["Modality"],
                _price_style(r["Cost/1M In"]),
                _price_style(r["Cost/1M Out"]),
            )

        self.console.print(table)
        self.console.print(
            f"[green]💰 Per 1M tokens  |  {datetime.now().strftime('%H:%M')}[/green]"
        )

        # Return a plain-text version for export
        buf = StringIO()
        plain_console = Console(file=buf, width=200, force_terminal=False)
        plain_table = Table(show_lines=False, expand=False, title=None)
        for col in HEADERS:
            plain_table.add_column(col)
        for r in rows[:limit] if limit else rows:
            plain_table.add_row(*(str(r[c]) for c in HEADERS))
        plain_console.print(plain_table)
        return buf.getvalue()

    def export_json(self, rows: list[dict[str, Any]], limit: int | None = None) -> str:
        """Export rows as JSON."""
        if limit:
            rows = rows[:limit]
        clean = [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]
        return json.dumps(clean, indent=2, ensure_ascii=False)

    def export_csv(self, rows: list[dict[str, Any]], limit: int | None = None) -> str:
        """Export rows as CSV."""
        if limit:
            rows = rows[:limit]
        buf = StringIO()
        writer = csv.DictWriter(
            buf,
            fieldnames=[h for h in HEADERS if not h.startswith("_")],
            extrasaction="ignore",
        )
        writer.writeheader()
        for r in rows:
            writer.writerow({k: v for k, v in r.items() if not k.startswith("_")})
        return buf.getvalue()

    # ---- main entry point ----

    def run(self, args):
        """Execute the full pipeline: fetch → filter → output."""
        self.console.print("[dim]⏳ Fetching OpenRouter model list…[/dim]")

        data = self.fetch_models()
        models = data.get("data", [])
        rows = self.filter_models(models, args)

        limit = getattr(args, "limit", None)
        fmt = getattr(args, "output", "table")

        if fmt == "json":
            print(self.export_json(rows, limit))
        elif fmt == "csv":
            print(self.export_csv(rows, limit))
        else:
            self.display_table(rows, limit)

    # ---- utility ----

    @staticmethod
    def _parse_numeric(raw: str | float | None, label: str) -> float | None:
        if raw in (None, ""):
            return None
        try:
            return float(raw)
        except (ValueError, TypeError) as e:
            raise SystemExit(
                f"Invalid value for --{label}: {raw!r}. Expected a number."
            ) from e


# ---------------------------------------------------------------------------
# Interactive mode
# ---------------------------------------------------------------------------


def prompt_for_filters(viewer: ModelViewer) -> argparse.Namespace:
    """Interactive questionnaire for users who run without CLI args."""
    import types

    data = viewer.fetch_models()
    models = data.get("data", [])
    providers = sorted(
        {(m.get("canonical_slug", "") or "/").split("/")[0] for m in models}
    )
    providers = [p for p in providers if p]

    questions = [
        inquirer.List(
            "provider",
            message="Provider (or skip)",
            choices=["<Any>"] + providers,
            default="<Any>",
        ),
        inquirer.Text("name", message="Model name contains (optional)", default=""),
        inquirer.Text("slug", message="Slug contains (optional)", default=""),
        inquirer.Text(
            "search", message="Search description/name (optional)", default=""
        ),
        inquirer.Text(
            "context_min",
            message="Minimum context length (e.g. 128000, optional)",
            default="",
        ),
        inquirer.Text(
            "min_price",
            message="Min input price (USD per 1M tokens, optional)",
            default="",
        ),
        inquirer.Text(
            "max_price",
            message="Max input price (USD per 1M tokens, optional)",
            default="",
        ),
        inquirer.Text(
            "min_out_price",
            message="Min output price (USD per 1M tokens, optional)",
            default="",
        ),
        inquirer.Text(
            "max_out_price",
            message="Max output price (USD per 1M tokens, optional)",
            default="",
        ),
        inquirer.Confirm("include_free", message="Include free models?", default=False),
        inquirer.List(
            "sort_by",
            message="Sort by",
            choices=list(SORT_COLUMNS.keys()),
            default="price-in",
        ),
        inquirer.List(
            "sort_dir",
            message="Sort direction",
            choices=["desc", "asc"],
            default="desc",
        ),
        inquirer.Text("limit", message="Max results (optional)", default=""),
        inquirer.List(
            "output",
            message="Output format",
            choices=list(OUTPUT_FORMATS),
            default="table",
        ),
    ]
    answers = inquirer.prompt(questions)
    if answers is None:
        sys.exit(0)

    def _blank_to_none(val):
        return None if val == "" else val

    return types.SimpleNamespace(
        provider=None if answers["provider"] == "<Any>" else answers["provider"],
        name=_blank_to_none(answers["name"]),
        slug=_blank_to_none(answers["slug"]),
        search=_blank_to_none(answers["search"]),
        context_min=_blank_to_none(answers["context_min"]),
        min_price=_blank_to_none(answers["min_price"]),
        max_price=_blank_to_none(answers["max_price"]),
        min_out_price=_blank_to_none(answers["min_out_price"]),
        max_out_price=_blank_to_none(answers["max_out_price"]),
        include_free=answers["include_free"],
        sort_by=answers["sort_by"],
        sort_dir=answers["sort_dir"],
        limit=int(answers["limit"]) if answers["limit"] else None,
        output=answers["output"],
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Browse OpenRouter AI models — filter, sort, and export.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                     # interactive mode
  %(prog)s -n gpt-4                            # filter by name
  %(prog)s -p anthropic --context-min 200000   # Anthropic, ≥200K context
  %(prog)s --search vision --sort-by price-in  # search descriptions
  %(prog)s --min 0.01 --max 0.10 --output json # price range → JSON
  %(prog)s --sort-by context --sort-dir asc    # smallest context first
  %(prog)s --limit 10 --output csv             # top 10 → CSV
        """,
    )

    # filters
    parser.add_argument("-n", "--name", help="Filter by model name (substring)")
    parser.add_argument("-p", "--provider", help="Filter by provider (substring)")
    parser.add_argument("--slug", help="Filter by canonical slug (substring)")
    parser.add_argument("--search", help="Search in model name and description")
    parser.add_argument(
        "--context-min", type=str, help="Minimum context length (e.g. 128000)"
    )
    parser.add_argument(
        "--min", dest="min_price", type=str, help="Min input price (per 1M tokens)"
    )
    parser.add_argument(
        "--max", dest="max_price", type=str, help="Max input price (per 1M tokens)"
    )
    parser.add_argument(
        "--min-out",
        dest="min_out_price",
        type=str,
        help="Min output price (per 1M tokens)",
    )
    parser.add_argument(
        "--max-out",
        dest="max_out_price",
        type=str,
        help="Max output price (per 1M tokens)",
    )
    parser.add_argument(
        "--include-free", action="store_true", help="Include free models"
    )

    # sorting & display
    parser.add_argument(
        "--sort-by",
        choices=list(SORT_COLUMNS.keys()),
        default="price-in",
        help="Column to sort by (default: price-in)",
    )
    parser.add_argument(
        "--sort-dir",
        choices=["asc", "desc"],
        default="desc",
        help="Sort direction (default: desc)",
    )
    parser.add_argument("--limit", type=int, help="Show only the first N results")
    parser.add_argument(
        "--output",
        choices=list(OUTPUT_FORMATS),
        default="table",
        help="Output format (default: table)",
    )
    return parser


def main():
    parser = build_parser()

    if len(sys.argv) == 1:
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            print(
                "[ERROR] Interactive mode needs a real terminal (TTY). "
                "Use --help for CLI options."
            )
            sys.exit(1)
        viewer = ModelViewer()
        args = prompt_for_filters(viewer)
        viewer.run(args)
    else:
        args = parser.parse_args()
        viewer = ModelViewer()
        viewer.run(args)


if __name__ == "__main__":
    main()
