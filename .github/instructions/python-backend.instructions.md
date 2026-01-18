---
description: 'Python backend development - FastAPI, pydantic, uv, Signal model'
applyTo: 'packages/backend/**/*.py'
---

# Python Backend Instructions

## Technology Stack

| Component       | Choice       | Notes                          |
| --------------- | ------------ | ------------------------------ |
| Runtime         | Python 3.14+ |                                |
| Framework       | FastAPI      | Async, OpenAPI support         |
| Package Manager | uv           | Fast, replaces pip/poetry      |
| Validation      | pydantic v2  | Use v2 patterns, not v1        |
| State Storage   | In-memory    | Abstracted interface (ADR-001) |

## Signal Model (ADR-005)

The core data model for smart home signals:

```python
@dataclass
class Signal:
    id: str           # Unique identifier (OpenHAB item name / HA entity_id)
    value: str        # Pre-formatted, display-ready value
    unit: str         # Unit symbol (e.g., "°C", "%", "W")
    label: str = ""   # Human-readable name
```

**Key principle:** Backend normalizes ALL data. Frontend just displays `value` and
`unit`.

## Adapter Protocol

Smart home adapters implement this protocol (ADR-005):

```python
class SmartHomeAdapter(Protocol):
    def get_signals(self) -> Dict[str, Signal]: ...
    def get_signal(self, signal_id: str) -> Signal: ...
    def subscribe_events(self) -> Generator[Signal, None, None]: ...
```

## SSE Event Flow

```
OpenHAB → [SSE] → Backend (normalize) → [SSE] → Frontend (render)
```

Backend handles: unit extraction, value formatting, encoding fixes.

## OpenHAB Integration

- See `old/backend/home-observer/` for PoC reference
- Parse `stateDescription.pattern` like `"%.1f °C"` to extract unit
- Unit mapping in `old/backend/home-observer/units_of_measurement.json`

## Common Pitfalls

1. **OpenHAB special values** — `"UNDEF"` and `"NULL"` are valid states, not errors
2. **Error swallowing** — PoC has `except: continue` patterns; use proper logging
3. **Hardcoded URLs** — Use `config.py` with pydantic-settings, not literals
4. **Encoding issues** — OpenHAB SSE may have encoding problems (see `ftfy` in PoC)

## Code Style

Follow PEP 8 for code style and PEP 257 for docstrings.

### Type Hints

- Use `typing` module for type annotations on all public functions
- Prefer `async def` for I/O-bound operations
- Use pydantic models for API request/response schemas

### Error Handling

- Use specific exceptions (`ValueError`, `TypeError`), not bare `except:`
- Fail fast with meaningful error messages
- Use context managers (`with`) for resource handling

### Code Organization

- Keep functions focused and under ~50 lines
- Avoid global variables
- Follow existing patterns in `src/lumehaven/`
