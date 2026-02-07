# Coding Standards

!!! warning "Work in progress" This page will be expanded as part of the documentation
content phase.

## Python (Backend)

| Aspect     | Standard               | Reference                         |
| ---------- | ---------------------- | --------------------------------- |
| Style      | PEP 8                  | Enforced by Ruff                  |
| Docstrings | PEP 257 (Google style) | Enforced by Ruff                  |
| Type hints | PEP 484 / PEP 604      | Enforced by mypy (strict mode)    |
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

!!! note "Phase 3" Frontend coding standards will be documented when the frontend is
implemented.

## Tooling

| Tool            | Purpose              | Command                             |
| --------------- | -------------------- | ----------------------------------- |
| Ruff            | Linting + formatting | `task lint:be` / `task lint:be:fix` |
| mypy            | Type checking        | `task typecheck:be`                 |
| pytest          | Unit testing         | `task test:be:unit`                 |
| Robot Framework | Integration testing  | `task test:be:integration`          |
| pre-commit      | Git hooks            | Runs automatically on commit        |
