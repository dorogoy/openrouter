# OpenRouter.ai Model Viewer

This project fetches the list of public models from OpenRouter.ai, extracts the main data, and displays a table in the terminal sorted by input price (prompt, per 1K tokens), using `uv` for environment and dependency management.

---

## ⚡ Usage with `uv`

With `pyproject.toml` and `uv.lock` already present, just run the script directly. `uv` will create the virtual environment and handle dependencies automatically:

```bash
uv run main.py [filter options]
```

**Example with filters:**

```bash
uv run main.py --name=gpt --min-price=0.005 --max-price=0.015
```

---

## Available filter options

You can filter the results table with the following optional arguments:

- `--name <text>`
  - Filter models whose name contains the text (case-insensitive).
- `--provider <text>`
  - Filter by provider (case-insensitive).
- `--slug <text>`
  - Filter by slug.
- `--min-price <value>`
  - Minimum price (prompt, per 1K tokens).
- `--max-price <value>`
  - Maximum price (prompt, per 1K tokens).
- `--include-free`
  - Include free models in the table (by default they are omitted).

**Sorting and filtering notes:**

- By default, models are sorted from highest to lowest price (prompt, per 1K tokens).
- The "Auto Router" model is never shown.
- Free models are only shown if you use `--include-free`.

You can combine several filters at once. For example:

```bash
uv run main.py --provider=openai --min-price=0.001 --max-price=0.01
```

---

## Notes

- Filtering is inclusive and flexible: only models that meet all filters will be shown.
- Models without an explicit prompt price will not appear if you use price filters.
- You can easily adapt the script to add more columns or filtering logic if needed.

### ⚡ About the automatic cache

The script uses an automatic local cache to avoid downloading the model list on every run:

- The cache is stored in the system's temporary directory and is automatically updated once a day.
- If you run the script multiple times in the same day, it will only download the data the first time.
- If there is a network error, the script will use the last available cache (even if outdated), showing a warning.
- You don't need to worry about cleaning the cache: it is managed automatically and overwritten daily.
