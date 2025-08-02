# OpenRouter.ai Model Viewer

This project fetches the list of public models from OpenRouter.ai, extracts the main data, and displays a table in the terminal sorted by input price (prompt, per 1K tokens), using `uv` for environment and dependency management.

---

## 🛠️ Project Dependencies

- Python 3.12+
- `requests`
- `rich`
- `ruff` (for linting and formatting)

## ⚡ Usage with `uv`

With `pyproject.toml` and `uv.lock` already present, just run the script directly. `uv` will create the virtual environment and handle dependencies automatically:

```bash
uv run main.py
```

### 🖱️ Interactive Mode (Recommended)
If you run the script with no arguments in a real terminal, you'll get an interactive menu with dropdowns and prompts for all filter options (powered by `inquirer`).

### 🛠️ Command-Line Mode (Power Users)
You can still use CLI flags for advanced filtering:

```bash
uv run main.py --name=gpt --min=0.005 --max=0.015 --provider=openai --include-free
```

---

## Available filter options

You can filter the results table with the following optional arguments (CLI mode):

- `--name <text>`
  - Filter models whose name contains the text (case-insensitive).
- `--provider <text>`
  - Filter by provider (case-insensitive).
- `--slug <text>`
  - Filter by slug.
- `--min <value>`
  - Minimum price (prompt, per 1K tokens).
- `--max <value>`
  - Maximum price (prompt, per 1K tokens).
- `--include-free`
  - Include free models in the table (by default they are omitted).

**Tip:** In interactive mode, you can select these options from dropdowns and prompts—no need to remember the flags!

**Sorting and filtering notes:**

- By default, models are sorted from highest to lowest price (prompt, per 1K tokens).
- The "Auto Router" model is never shown.
- Free models are only shown if you use `--include-free`.

You can combine several filters at once. For example:

```bash
uv run main.py --provider=openai --min-price=0.001 --max-price=0.01
```

---

## 🧹 Code Linting and Formatting

This project uses `ruff` for linting and import sorting:

### Linting

To check code quality, run:

```bash
make lint
```

Or directly with `ruff`:

```bash
ruff check .
```

### Automatic Formatting

To automatically fix linting issues and sort imports:

```bash
# Using Makefile (recommended)
make format

# Or using ruff directly
ruff check --fix .
ruff format .
```

The `make format` command will:
- Automatically fix linting issues
- Sort imports
- Apply code formatting

**Linting Configuration:**
- Line length: 88 characters
- Uses isort for import sorting
- Checks for various code quality issues (pyflakes, pycodestyle, bugbear, etc.)

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
