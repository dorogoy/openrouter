# OpenRouter.ai Model Viewer

Browse, filter, sort, and export the OpenRouter AI model catalog — with precise pricing, context windows, and modality support — right from your terminal.

---

## 🛠️ Project Dependencies

- Python 3.12+
- `requests`
- `rich`
- `inquirer`
- `ruff` (linting & formatting, dev only)

## ⚡ Usage with `uv`

```bash
uv run main.py                      # interactive mode
uv run main.py --help               # see all CLI flags
```

### 🚀 Install as a global CLI tool

```bash
chmod +x main.py
cp main.py ~/bin/openrouter         # drop .py for a clean command
~/bin/openrouter
```

---

## 🖱️ Interactive Mode (recommended)

Run without arguments and get a guided questionnaire with dropdowns for every filter:

```bash
uv run main.py
```

Prompts cover: provider, model name, slug, free-text search, context length, price ranges (in/out), sort column & direction, result limit, and output format (table / JSON / CSV).

## 🛠️ CLI Mode (power users)

```bash
uv run main.py -n gpt-4 --context-min 128000 --sort-by price-in --output table
```

### All CLI flags

| Flag | Description |
|---|---|
| `-n, --name TEXT` | Filter by model name substring |
| `-p, --provider TEXT` | Filter by provider substring |
| `--slug TEXT` | Filter by canonical slug substring |
| `--search TEXT` | Search in model name **and description** |
| `--context-min N` | Minimum context window (e.g. `128000`) |
| `--min PRICE` | Min **input** price per 1M tokens |
| `--max PRICE` | Max **input** price per 1M tokens |
| `--min-out PRICE` | Min **output** price per 1M tokens |
| `--max-out PRICE` | Max **output** price per 1M tokens |
| `--include-free` | Include free models (excluded by default) |
| `--sort-by COL` | Sort column: `model`, `provider`, `context`, `price-in`, `price-out` |
| `--sort-dir DIR` | Sort direction: `asc` or `desc` (default: `desc`) |
| `--limit N` | Show only first N results |
| `--output FMT` | Output format: `table`, `json`, or `csv` |

### Examples

```bash
# Anthropic models with ≥200K context, cheapest first
uv run main.py -p anthropic --context-min 200000 --sort-by price-in --sort-dir asc

# Search descriptions for "vision", export as JSON
uv run main.py --search vision --output json

# Top 5 most expensive output prices as CSV
uv run main.py --sort-by price-out --limit 5 --output csv

# Text-only models (exclude image/file)
uv run main.py --search "text" --output table
```

---

## 📊 Table Columns

| Column | Description |
|---|---|
| **Model** | Clean model name |
| **Provider** | Provider prefix from the canonical slug |
| **Context** | Context window (human-readable: `200K`, `1.0M`) |
| **Modality** | Input→output: `T`=text, `I`=image, `F`=file (e.g. `T+I→T`) |
| **Cost/1M In** | Input (prompt) price per 1 million tokens |
| **Cost/1M Out** | Output (completion) price per 1 million tokens |

Prices are color-coded: 🟢 cheap &nbsp; 🟡 mid-range &nbsp; 🔴 expensive

---

## 🧹 Lint & Format

```bash
make lint          # ruff check .
make format        # ruff check --fix . && ruff format .
```

---

## 📦 Caching

The model list is cached in your system temp directory and refreshed once per day. On network errors the script falls back to the last cached copy.
