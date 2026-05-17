# AGENTS.md

This repository is agent-ready. Follow these guidelines for coding agents:

## Build, Lint, and Format
- **Run main script (interactive UI):**
  ```bash
  uv run main.py
  ```
- **Run with CLI flags (power users):**
  ```bash
  uv run main.py -n gpt-4 --context-min 128000 --sort-by price-in
  uv run main.py --search vision --output json --limit 10
  ```
- **Lint:**
  ```bash
  make lint        # ruff check .
  ```
- **Format & sort imports:**
  ```bash
  make format      # ruff check --fix . && ruff format .
  ```

## Code Style
- **Imports:** Use absolute imports, sorted by `ruff` (isort).
- **Formatting:**
  - Line length: 88 characters
  - Use `ruff` for formatting and linting
- **Types:** Prefer type hints for function signatures and variables.
- **Naming:**
  - Functions/variables: `snake_case`
  - Classes: `PascalCase`
- **Error Handling:**
  - Use exceptions for error cases
  - Log or print errors clearly
- **General:**
  - Keep code modular and readable
  - Document public functions/classes
- **Interactive UI:**
  - Use `inquirer` for dropdowns and prompts in terminal UI.
  - Use `types.SimpleNamespace` for dynamic argument objects in interactive mode.

## Testing
- No explicit test commands or files found. If adding tests, use standard Python `unittest` or `pytest` conventions and place tests in a `tests/` directory.

---
For more details, see README.md. Agents should follow these rules for all code contributions.
