# AGENTS.md

This repository is agent-ready. Follow these guidelines for coding agents:

## Build, Lint, and Format
- **Run main script:**
  ```bash
  uv run main.py [args]
  ```
- **Lint:**
  ```bash
  make lint        # or ruff check .
  ```
- **Format & sort imports:**
  ```bash
  make format      # or ruff check --fix . && ruff format .
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

## Testing
- No explicit test commands or files found. If adding tests, use standard Python `unittest` or `pytest` conventions and place tests in a `tests/` directory.

---
For more details, see README.md. Agents should follow these rules for all code contributions.