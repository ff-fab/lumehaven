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

## Signal Model (ADR-005, amended by ADR-010)

The core data model for smart home signals (enriched per ADR-010):

```python
class SignalType(StrEnum):
    STRING   = "string"      # Weather descriptions, messages
    NUMBER   = "number"      # Temperature, humidity, power
    BOOLEAN  = "boolean"     # ON/OFF, OPEN/CLOSED, motion
    ENUM     = "enum"        # Heat/Cool/Auto/Off
    DATETIME = "datetime"    # Timestamps

@dataclass(frozen=True)
class Signal:
    id: str                                    # Unique identifier
    value: str | int | float | bool | None     # Typed native value
    unit: str = ""                             # Unit symbol ("°C", "%")
    label: str = ""                            # Human-readable name
    display_value: str = ""                    # Pre-formatted for display
    available: bool = True                     # Device reachable?
    signal_type: SignalType = SignalType.STRING # Discriminator for UI
```

**Key principle:** Backend normalizes ALL data. Frontend uses `display_value` for
rendering and `value` for logic (thresholds, sorting).

## Adapter Protocol

Smart home adapters implement this protocol (ADR-005, ADR-011):

```python
from collections.abc import AsyncIterator

class SmartHomeAdapter(Protocol):
    async def get_signals(self) -> dict[str, Signal]: ...
    async def get_signal(self, signal_id: str) -> Signal | None: ...
    def subscribe_events(self) -> AsyncIterator[Signal]: ...
    async def send_command(self, signal_id: str, command: str) -> None: ...  # ADR-011
    async def close(self) -> None: ...
```

> **Note:** `send_command()` is the target protocol shape per ADR-011. It is not yet
> implemented in `protocol.py` — that work is tracked in task `lh-6yy.14`.

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
