#!/usr/bin/env python3
"""
OpenRouter Model Viewer - Terminal optimized with precise pricing
"""

import argparse
import json
import os
import tempfile
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests
from rich.console import Console
from rich.table import Table

API_URL = "https://openrouter.ai/api/v1/models"
HEADERS = ["Model", "Provider", "Slug", "Cost/1M In", "Cost/1M Out"]


class ModelViewer:
    """Optimized model viewer with precise pricing display"""

    def __init__(self):
        pass

    def fetch_models(self) -> Dict:
        """Fetch latest models from OpenRouter API, using a daily cache in temp dir"""
        cache_dir = tempfile.gettempdir()
        cache_file = os.path.join(cache_dir, "openrouter_models_cache.json")
        now = datetime.now()

        # Try to read cache
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
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
        except requests.RequestException as e:
            # If error and previous cache exists, use it even if old
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        cache = json.load(f)
                    if "data" in cache:
                        print("[WARN] Using old cache data due to network error.")
                        return {"data": cache["data"]}
                except Exception:
                    pass
            raise SystemExit(f"Error fetching models: {e}")

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
            "microsoft": "MS",
            "perplexity": "Pplx",
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

    def process_model(self, model: Dict) -> Optional[Dict[str, str]]:
        """Process single model data for display"""
        try:
            # Clean name
            raw_name = model.get("name", "-")
            name = raw_name.split("/")[-1] if "/" in raw_name else raw_name
            name = name[:25] + "..." if len(name) > 25 else name

            # Slug
            canonical_slug = model.get("canonical_slug", "-")
            slug_display = self.get_clean_slug(canonical_slug)

            # Provider
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

    def filter_models(self, models: List[Dict], args) -> List[Dict[str, str]]:
        """Filter, process, and sort models based on criteria, omitting 'Auto Router' and free models by default"""
        processed = []
        min_price = float(args.min_price) if getattr(args, "min_price", None) else None
        max_price = float(args.max_price) if getattr(args, "max_price", None) else None
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

            # Apply price filters (input price)
            price_str = data["Cost/1M In"]
            price_val = None
            if price_str.startswith("$"):
                try:
                    # Remove $ and ¢, handle cents
                    if "¢" in price_str:
                        price_val = (
                            float(price_str.replace("$", "").replace("¢", "")) / 100
                        )
                    else:
                        price_val = float(price_str.replace("$", ""))
                except Exception:
                    price_val = None

            # Exclude free models unless specified
            if not include_free:
                if price_val is None or price_val == 0.0:
                    continue

            if min_price is not None:
                if price_val is None or price_val < min_price:
                    continue
            if max_price is not None:
                if price_val is None or price_val > max_price:
                    continue

            # Add numeric value for sorting (as string to avoid type error)
            data["_price_val"] = str(price_val if price_val is not None else -1)
            processed.append(data)

        # Sort by descending price (input)
        processed.sort(key=lambda x: float(x["_price_val"]), reverse=True)
        # Remove helper field before displaying
        for d in processed:
            if "_price_val" in d:
                del d["_price_val"]
        return processed

    def display_table(self, models: List[Dict[str, str]]) -> None:
        """Display models in optimized terminal table using rich"""
        console = Console()
        if not models:
            console.print("[bold red]No models found matching criteria.[/bold red]")
            return

        table = Table(
            title=f"{len(models)} OpenRouter Models",
            show_lines=False,
            header_style="bold magenta",
        )
        for col in HEADERS:
            if col == "Model":
                table.add_column(col, style="white", no_wrap=False, max_width=55)
            elif col == "Slug":
                table.add_column(col, style="white", no_wrap=False)
            else:
                table.add_column(col, style="white", no_wrap=True)

        for m in models:
            table.add_row(*(m[field] for field in HEADERS))

        console.print(table)
        date_str = datetime.now().strftime("%H:%M")
        console.print(
            f"\n[green]💰 Prices shown per 1 million tokens | Updated: {date_str}[/green]"
        )

    def run(self, args):
        """Main execution flow"""
        print("⏳ Fetching OpenRouter models...")

        data = self.fetch_models()
        models = data.get("data", [])

        filtered_models = self.filter_models(models, args)
        self.display_table(filtered_models)


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
  %(prog)s --min-price 0.005 --max-price 0.015  # Filter by price range (USD per 1K tokens)
        """,
    )

    parser.add_argument("-n", "--name", type=str, help="Filter by model name substring")
    parser.add_argument(
        "-p", "--provider", type=str, help="Filter by provider substring"
    )
    parser.add_argument("--slug", type=str, help="Filter by slug substring")
    parser.add_argument(
        "--min-price", type=str, help="Minimum price (prompt, per 1K tokens)"
    )
    parser.add_argument(
        "--max-price", type=str, help="Maximum price (prompt, per 1K tokens)"
    )
    parser.add_argument(
        "--include-free",
        action="store_true",
        help="Include free models in the table",
    )

    args = parser.parse_args()
    viewer = ModelViewer()
    viewer.run(args)


if __name__ == "__main__":
    main()
