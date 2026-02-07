# Coding Standards

## Python (Backend)

| Aspect     | Standard               | Reference                         |
| ---------- | ---------------------- | --------------------------------- |
| Style      | PEP 8                  | Enforced by Ruff                  |
| Docstrings | PEP 257 (Google style) | Enforced by Ruff                  |
| Type hints | PEP 484 / PEP 604     | Enforced by mypy (strict mode)    |
| Formatting | 88 char line length    | Ruff formatter (Black-compatible) |
| Imports    | isort (via Ruff)       | First-party: `lumehaven`          |

### Docstring Example

```python
def normalize_value(raw: str, unit: str | None = None) -> float | str:
    """Normalize a raw smart home value to a Python type.

    Handles OpenHAB-specific state strings (NULL, UNDEF) and numeric
    parsing with unit extraction.

    Args:
        raw: The raw value string from the smart home API.
        unit: Optional unit hint for parsing context.

    Returns:
        The normalized value as a float (for numeric values) or string.

    Raises:
        ValueError: If the value cannot be parsed.

    Example:
        >>> normalize_value("21.5 °C")
        21.5
    """
```

### Error Handling

- Use the `LumehavenError` hierarchy (see [Core API](../reference/api/core.md))
- Never catch bare `Exception` unless re-raising
- Document all raised exceptions in docstrings

## TypeScript (Frontend)

!!! note "Phase 3"
    Frontend coding standards will be documented when the frontend is implemented.

## Tooling

| Tool            | Purpose              | Command                             |
| --------------- | -------------------- | ----------------------------------- |
| Ruff            | Linting + formatting | `task lint:be` / `task lint:be:fix` |
| mypy            | Type checking        | `task typecheck:be`                 |
| pytest          | Unit testing         | `task test:be:unit`                 |
| Robot Framework | Integration testing  | `task test:be:integration`          |
| Prettier        | JS/TS/JSON/MD/YAML   | Runs via pre-commit + format-on-save|
| ESLint          | JS/TS linting        | `task lint:fe`                      |
| pre-commit      | Git hooks            | Runs automatically on commit        |

**Format on save** is enabled in the dev container — your code auto-formats when you
save.

## Pre-commit Hooks

Pre-commit hooks run automatically on `git commit`, catching issues before they enter
the repository.

### Setup (One-time)

The dev container sets up pre-commit automatically. If you need to re-install:

```bash
uv run pre-commit install
```

### What Gets Checked

| Check                | Tool      | Behavior                                 |
| -------------------- | --------- | ---------------------------------------- |
| Trailing whitespace  | built-in  | Auto-removed                             |
| File endings         | built-in  | Ensures newline at end of file           |
| YAML/JSON/TOML       | built-in  | Validates syntax                         |
| Merge conflicts      | built-in  | Detects unresolved conflict markers      |
| Private keys         | built-in  | Prevents committing secrets              |
| Spelling             | codespell | Catches common typos                     |
| Markdown/YAML format | Prettier  | Auto-formatted (88 char line width)      |
| Python lint + format | Ruff      | Auto-formatted, lint issues flagged      |
| Python types         | mypy      | Strict mode type checking                |

### How It Works

When you commit:

- **Pass** → commit succeeds
- **Auto-fixable** → files are fixed automatically, re-stage them (`git add`) and commit
  again
- **Manual fix needed** → commit blocked; fix the issue and retry

### Bypass (Emergency Only)

```bash
git commit --no-verify  # Skips all hooks — use sparingly
```

## Related

- [Testing How-To](../how-to/testing.md) — run tests, coverage thresholds
- [Development Setup](../tutorials/development-setup.md) — full environment setup
- [Contributing Guide](index.md) — workflow and PR process
