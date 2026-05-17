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
OpenRouter Model Viewer - Terminal optimized with precise pricing
"""

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta

import inquirer
import requests
from rich.console import Console
from rich.table import Table

API_URL = "https://openrouter.ai/api/v1/models"
HEADERS = ["Model", "Provider", "Slug", "Cost/1M In", "Cost/1M Out"]


class ModelViewer:
    """Optimized model viewer with precise pricing display"""

    def __init__(self):
        pass

    def fetch_models(self) -> dict:
        """Fetch latest models from OpenRouter API, using a daily cache in temp dir"""
        cache_dir = tempfile.gettempdir()
        cache_file = os.path.join(cache_dir, "openrouter_models_cache.json")
        now = datetime.now()

        # Try to read cache
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
                pass  # If error, force reload

        # If no valid cache, download
        try:
            response = requests.get(API_URL, timeout=10)
            response.raise_for_status()
            data = response.json().get("data", [])
            # Save to cache
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump({"fetched_at": now.isoformat(), "data": data}, f)
            return {"data": data}
        except requests.RequestException as fetch_error:
            # If error and previous cache exists, use it even if old
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, encoding="utf-8") as f:
                        cache = json.load(f)
                    if "data" in cache:
                        print("[WARN] Using old cache data due to network error.")
                        return {"data": cache["data"]}
                except Exception:
                    pass
            raise SystemExit(f"Error fetching models: {fetch_error}") from fetch_error

    def format_price_per_million(self, price: str) -> str:
        """Format price per 1M tokens with currency"""
        try:
            value = float(price)
            cost_per_million = value * 1_000_000

            # Format according to magnitude
            if cost_per_million < 0.01:
                return f"${cost_per_million * 100:.2f}¢"
            elif cost_per_million < 1:
                return f"${cost_per_million:.3f}"
            else:
                return f"${cost_per_million:.2f}"
        except (ValueError, TypeError):
            return "-"

    def parse_price_val(self, price_str: str) -> float | None:
        """Parse a formatted price string back to a numeric dollar value."""
        if not price_str or not price_str.startswith("$"):
            return None
        try:
            cleaned = price_str.replace("$", "").replace("¢", "")
            val = float(cleaned)
            if "¢" in price_str:
                val /= 100
            return val
        except (ValueError, TypeError):
            return None

    def get_provider_name(self, slug: str) -> str:
        """Extract clean provider name from canonical slug"""
        if not slug:
            return "-"

        parts = slug.split("/")
        if not parts:
            return "-"

        provider_map = {
            "openai": "OpenAI",
            "anthropic": "Anthropic",
            "google": "Google",
            "meta-llama": "Meta",
            "mistralai": "Mistral",
            "cohere": "Cohere",
            "microsoft": "Microsoft",
            "perplexity": "Perplexity",
            "deepseek": "DeepSeek",
            "qwen": "Qwen",
        }

        for key, value in provider_map.items():
            if key in parts[0].lower():
                return value

        return parts[0][:12] if len(parts[0]) > 12 else parts[0]

    def get_clean_slug(self, slug: str) -> str:
        """Clean and shorten slug for display"""
        if not slug:
            return "-"

        # Show only the last segment after "/"
        if "/" in slug:
            return slug.split("/")[-1].replace(
                "https://openrouter.ai/api/v1/models/", ""
            )
        else:
            return slug[:20] if len(slug) > 20 else slug

    def process_model(self, model: dict) -> dict[str, str] | None:
        """Process single model data for display"""
        try:
            # Clean name
            raw_name = model.get("name", "-")
            name = raw_name.split("/")[-1] if "/" in raw_name else raw_name

            # Slug and provider (original, not mapped)
            canonical_slug = model.get("canonical_slug", "-")
            if "/" in canonical_slug:
                orig_provider = canonical_slug.split("/")[0]
                slug_part = canonical_slug.split("/")[-1]
                slug_display = f"{orig_provider}/{slug_part}"
            else:
                slug_display = canonical_slug

            # Provider (mapped)
            provider = self.get_provider_name(canonical_slug)

            # Pricing - cost per 1M tokens
            pricing = model.get("pricing", {})
            input_price_1m = self.format_price_per_million(pricing.get("prompt", "0"))
            output_price_1m = self.format_price_per_million(
                pricing.get("completion", "0")
            )

            return {
                "Model": name,
                "Provider": provider,
                "Slug": slug_display,
                "Cost/1M In": input_price_1m,
                "Cost/1M Out": output_price_1m,
            }
        except (KeyError, ValueError):
            return None

    def filter_models(self, models: list[dict], args) -> list[dict[str, str]]:
        """
        Filter, process, and sort models based on criteria.

        Omits 'Auto Router' and free models by default, with
        optional filtering by name, provider, slug, and price.
        """
        processed = []
        raw_min = getattr(args, "min_price", None)
        raw_max = getattr(args, "max_price", None)
        raw_min_out = getattr(args, "min_out_price", None)
        raw_max_out = getattr(args, "max_out_price", None)
        min_price = float(raw_min) if raw_min else None
        max_price = float(raw_max) if raw_max else None
        min_out_price = float(raw_min_out) if raw_min_out else None
        max_out_price = float(raw_max_out) if raw_max_out else None
        include_free = getattr(args, "include_free", False)

        for model in models:
            data = self.process_model(model)
            if not data:
                continue

            # Omit "Auto Router"
            if data["Model"].strip().lower() == "auto router":
                continue

            # Apply text filters
            name_checks = data["Model"].lower()
            provider_checks = data["Provider"].lower()
            slug_checks = data["Slug"].lower()

            if args.name and args.name.lower() not in name_checks:
                continue
            if args.provider and args.provider.lower() not in provider_checks:
                continue
            if args.slug and args.slug.lower() not in slug_checks:
                continue

            # Apply price filters (input and output price)
            # Apply price filters using raw numeric data (converted to per 1M tokens)
            pricing = model.get("pricing", {})
            try:
                price_in = float(pricing.get("prompt", 0)) * 1_000_000
                price_out = float(pricing.get("completion", 0)) * 1_000_000
            except (ValueError, TypeError):
                price_in = price_out = 0.0

            # Exclude free models unless overridden
            is_free = (price_in is None or price_in == 0.0) and (
                price_out is None or price_out == 0.0
            )
            if not include_free and is_free:
                continue

            # Filter by input price range
            if (
                not is_free
                and min_price is not None
                and (price_in is None or price_in < min_price)
            ):
                continue
            if (
                not is_free
                and max_price is not None
                and (price_in is None or price_in > max_price)
            ):
                continue

            # Filter by output price range
            if (
                not is_free
                and min_out_price is not None
                and (price_out is None or price_out < min_out_price)
            ):
                continue
            if (
                not is_free
                and max_out_price is not None
                and (price_out is None or price_out > max_out_price)
            ):
                continue

            # Add numeric value for sorting (by input price)
            data["_price_val"] = str(price_in if price_in is not None else -1)
            processed.append(data)

        # Sort by descending price (input)
        processed.sort(key=lambda x: float(x["_price_val"]), reverse=True)
        # Remove helper field before displaying
        for d in processed:
            if "_price_val" in d:
                del d["_price_val"]
        return processed

    def display_table(self, models: list[dict[str, str]]) -> None:
        """Display models in optimized terminal table using rich"""
        console = Console()
        if not models:
            console.print("[bold red]No models found matching criteria.[/bold red]")
            return

        table = Table(
            title=f"{len(models)} OpenRouter Models",
            show_lines=False,
            header_style="bold magenta",
            expand=True,
        )
        for col in HEADERS:
            if col == "Model" or col == "Slug":
                table.add_column(col, style="white", no_wrap=False)
            else:
                table.add_column(col, style="white", no_wrap=True)

        for m in models:
            table.add_row(*(m[field] for field in HEADERS))

        console.print(table)
        date_str = datetime.now().strftime("%H:%M")
        console.print(f"[green]💰 Prices per mln tokens | Updated: {date_str}[/green]")

    def run(self, args):
        """Main execution flow"""
        print("⏳ Fetching OpenRouter models...")

        data = self.fetch_models()
        models = data.get("data", [])

        filtered_models = self.filter_models(models, args)
        self.display_table(filtered_models)


def prompt_for_filters(viewer):
    # Fetch models to get provider options
    data = viewer.fetch_models()
    models = data.get("data", [])
    providers = sorted(
        {
            viewer.get_provider_name(m.get("canonical_slug", ""))
            for m in models
            if m.get("canonical_slug")
        }
    )
    providers = [p for p in providers if p and p != "-"]

    questions = [
        inquirer.List(
            "provider",
            message="Select provider (or skip)",
            choices=["<Any>"] + providers,
            default="<Any>",
        ),
        inquirer.Text("name", message="Model name contains (optional)", default=""),
        inquirer.Text("slug", message="Slug contains (optional)", default=""),
        inquirer.Text(
            "min_price",
            message="Min input price (USD per 1K tokens, optional)",
            default="",
        ),
        inquirer.Text(
            "max_price",
            message="Max input price (USD per 1K tokens, optional)",
            default="",
        ),
        inquirer.Text(
            "min_out_price",
            message="Min output price (USD per 1K tokens, optional)",
            default="",
        ),
        inquirer.Text(
            "max_out_price",
            message="Max output price (USD per 1K tokens, optional)",
            default="",
        ),
        inquirer.Confirm("include_free", message="Include free models?", default=False),
    ]
    answers = inquirer.prompt(questions)

    # Map answers to argparse-like namespace
    import types

    args = types.SimpleNamespace(
        provider=None if answers["provider"] == "<Any>" else answers["provider"],
        name=answers["name"] or None,
        slug=answers["slug"] or None,
        min_price=answers["min_price"] or None,
        max_price=answers["max_price"] or None,
        min_out_price=answers["min_out_price"] or None,
        max_out_price=answers["max_out_price"] or None,
        include_free=answers["include_free"],
    )
    return args


def main():
    parser = argparse.ArgumentParser(
        description="View OpenRouter AI models with precise pricing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                  # All models
  %(prog)s -n gpt-4         # Filter by model name
  %(prog)s -p openai        # Filter by provider
  %(prog)s --slug llama-3   # Filter by slug
  %(prog)s --min 0.005 --max 0.015  # Filter by input price range
  %(prog)s --min-out 0.01 --max-out 0.03  # Filter by output price range
  %(prog)s --min 0.005 --min-out 0.01  # Filter by both input and output price
        """,
    )

    parser.add_argument("-n", "--name", type=str, help="Filter by model name substring")
    parser.add_argument(
        "-p", "--provider", type=str, help="Filter by provider substring"
    )
    parser.add_argument("--slug", type=str, help="Filter by slug substring")
    parser.add_argument(
        "--min",
        dest="min_price",
        type=str,
        help="Minimum price (prompt, per 1K tokens)",
    )
    parser.add_argument(
        "--max",
        dest="max_price",
        type=str,
        help="Maximum price (prompt, per 1K tokens)",
    )
    parser.add_argument(
        "--min-out",
        dest="min_out_price",
        type=str,
        help="Minimum output price (completion, per 1M tokens)",
    )
    parser.add_argument(
        "--max-out",
        dest="max_out_price",
        type=str,
        help="Maximum output price (completion, per 1M tokens)",
    )
    parser.add_argument(
        "--include-free",
        action="store_true",
        help="Include free models in the table",
    )

    # If no CLI args, launch interactive mode
    if len(sys.argv) == 1:
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            print(
                "[ERROR] Interactive mode requires a real terminal (TTY)."
                " Please run with CLI arguments or in a terminal window."
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
