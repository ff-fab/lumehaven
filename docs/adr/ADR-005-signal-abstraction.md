# ADR-005: Signal Identity and Metadata Abstraction

## Status

Accepted

## Context

Lumehaven needs a unified way to represent smart home data (signals) from different
platforms (OpenHAB, HomeAssistant). The core challenge is:

1. **Different data models:** OpenHAB uses "Items" with types like `Number:Temperature`,
   while HomeAssistant uses "Entities" with domain-based `entity_id` (e.g.,
   `sensor.temperature_living_room`)
2. **Unit handling differs:** OpenHAB embeds units in state values (`"19.6 °C"`) and
   provides `stateDescription.pattern` for formatting. HomeAssistant stores units in
   `attributes.unit_of_measurement`
3. **Metadata richness varies:** HomeAssistant provides richer attributes
   (friendly_name, device_class), while OpenHAB relies on tags and transformations
4. **Frontend requirements:** The dashboard needs pre-formatted, display-ready values
   with separated unit information

The PoC established a working pattern in
[smarthome.py](../../old/backend/home-observer/smarthome.py) with `SmartHomeItem`
storing `name`, `value`, `unit`, and `format`. This proved sufficient for OpenHAB but
needs evaluation for HomeAssistant support.

## Considered Options

### Option 1: Minimal Signal (PoC-Based)

Preserve the PoC's simple approach with minor enhancements.

```python
@dataclass
class Signal:
    """Minimal representation focused on display needs"""
    id: str           # Unique identifier (OpenHAB item name / HA entity_id)
    value: str        # Pre-formatted, display-ready value
    unit: str         # Unit symbol (e.g., "°C", "%", "W")

    # Optional enrichments
    label: str = ""   # Human-readable name (if available)
```

**Adapter responsibility:** Each platform adapter fully normalizes data before creating
a Signal:

- OpenHAB adapter: Extracts unit from `stateDescription.pattern`, applies formatting
- HomeAssistant adapter: Uses `attributes.unit_of_measurement`, formats value

**Pros:**

- Simplest possible abstraction
- Proven in PoC for OpenHAB
- Frontend stays trivially simple (just display `value` and `unit`)
- Easy to understand and maintain

**Cons:**

- Loses metadata that might be useful later (device_class, last_changed)
- String-only values limit backend-side calculations
- No type information for smarter UI rendering

### Option 2: Typed Signal with Metadata

Richer model preserving type information and common metadata.

```python
from enum import Enum
from typing import Any, Optional
from datetime import datetime

class SignalType(str, Enum):
    NUMBER = "number"
    STRING = "string"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    ENUM = "enum"        # For finite option sets
    UNDEFINED = "undefined"

@dataclass
class Signal:
    """Typed signal with rich metadata"""
    id: str
    signal_type: SignalType

    # Value representation
    raw_value: Any              # Original typed value (float, bool, str, etc.)
    display_value: str          # Pre-formatted for display
    unit: str = ""              # Unit symbol

    # Common metadata
    label: str = ""             # Human-readable name
    device_class: str = ""      # Semantic type (temperature, humidity, power, etc.)
    last_updated: Optional[datetime] = None

    # Platform-specific (optional, for debugging/advanced features)
    source_platform: str = ""   # "openhab" | "homeassistant"
    source_id: str = ""         # Original platform ID
```

**Pros:**

- Enables type-aware UI (different widgets for boolean vs number)
- Preserves `device_class` for semantic grouping (all temperatures together)
- `raw_value` enables backend calculations (aggregations, conversions)
- Better debugging with `source_platform` and `source_id`

**Cons:**

- More complex adapter logic
- Larger data payloads
- Frontend might not need most of this initially

### Option 3: Layered Model (Separate Storage and Transfer)

Different models for internal storage vs frontend transfer.

```python
# Internal storage model (full fidelity)
@dataclass
class StoredSignal:
    id: str
    platform: str               # "openhab" | "homeassistant"
    platform_id: str            # Original ID
    signal_type: SignalType
    raw_value: Any
    unit: str
    label: str
    device_class: str
    attributes: dict            # Platform-specific extras
    last_updated: datetime
    last_changed: datetime

# Transfer model (optimized for frontend)
@dataclass
class SignalDTO:
    id: str
    value: str                  # Pre-formatted
    unit: str
    label: str
```

**Pros:**

- Best of both worlds: rich storage, lean transfer
- Can evolve storage without changing frontend contract
- Enables future features without payload bloat

**Cons:**

- Two models to maintain
- Mapping logic between layers
- Premature optimization if we don't need rich storage

## Decision

Use **Option 1: Minimal Signal** with a clear extension path.

The abstraction will be:

```python
from dataclasses import dataclass
from typing import Protocol, Dict, Generator

@dataclass
class Signal:
    """A normalized smart home signal ready for display.

    The backend is responsible for all normalization:
    - Extracting values from platform-specific formats
    - Applying formatting (decimals, rounding)
    - Extracting units from patterns or attributes
    - Handling special states (UNDEF, NULL, unavailable)
    """
    id: str           # Unique, stable identifier
    value: str        # Pre-formatted display value
    unit: str         # Unit symbol (empty string if unitless)
    label: str = ""   # Optional human-readable name


class SmartHomeAdapter(Protocol):
    """Protocol for smart home platform adapters."""

    def get_signals(self) -> Dict[str, Signal]:
        """Load all signals from the platform."""
        ...

    def get_signal(self, signal_id: str) -> Signal:
        """Load a specific signal."""
        ...

    def subscribe_events(self) -> Generator[Signal, None, None]:
        """Subscribe to real-time signal updates."""
        ...
```

## Decision Drivers

1. **Proven pattern:** The PoC's `SmartHomeItem` with `name`, `value`, `unit` worked
   well for OpenHAB - validated against real-world data
2. **YAGNI:** We don't have concrete requirements for type-aware UI or backend
   calculations yet
3. **Frontend simplicity:** Dashboard just needs to display values - keeping it "dumb"
   is a project goal
4. **Extension path:** Adding fields to a dataclass is backward-compatible; we can
   enrich later
5. **Adapter complexity focus:** Complex logic belongs in platform-specific adapters,
   not the abstraction

## Decision Matrix

| Criterion            | Option 1 (Minimal) | Option 2 (Typed) | Option 3 (Layered) |
| -------------------- | ------------------ | ---------------- | ------------------ |
| Simplicity           | 5                  | 3                | 2                  |
| Proven pattern (PoC) | 5                  | 3                | 2                  |
| HomeAssistant ready  | 4                  | 5                | 5                  |
| Extension potential  | 3                  | 5                | 5                  |
| Frontend simplicity  | 5                  | 4                | 5                  |
| Maintenance burden   | 5                  | 3                | 2                  |
| **Total**            | **27**             | **23**           | **21**             |

_Scale: 1 (poor) to 5 (excellent)_

## Platform Mapping Strategy

### OpenHAB → Signal

Based on PoC's [openhab.py](../../old/backend/home-observer/openhab.py):

| OpenHAB Field              | Signal Field          | Notes                                 |
| -------------------------- | --------------------- | ------------------------------------- |
| `name`                     | `id`                  | Direct mapping                        |
| `state` (processed)        | `value`               | After unit extraction, format applied |
| `stateDescription.pattern` | (extracted to) `unit` | Parse `"%d Wh"` → `"Wh"`              |
| `label` (if available)     | `label`               | From item definition                  |
| `transformedState`         | `value`               | If present, use instead of state      |

**Special cases (from PoC):**

- `"UNDEF"`, `"NULL"` → pass through as `value`, empty `unit`
- `DateTime` items → no unit extraction
- `Rollershutter`, `Dimmer` → implicit `%` unit
- `Number:Temperature` → derive unit from measurement system (SI/US)

### HomeAssistant → Signal

Based on
[HomeAssistant WebSocket API](https://developers.home-assistant.io/docs/api/websocket/):

| HomeAssistant Field              | Signal Field | Notes                                       |
| -------------------------------- | ------------ | ------------------------------------------- |
| `entity_id`                      | `id`         | Direct mapping                              |
| `state`                          | `value`      | May need formatting based on `device_class` |
| `attributes.unit_of_measurement` | `unit`       | Direct if present                           |
| `attributes.friendly_name`       | `label`      | Direct mapping                              |

**Special cases:**

- `state = "unavailable"`, `"unknown"` → pass through, empty `unit`
- Boolean domains (`binary_sensor`, `switch`) → `"on"`/`"off"`, no unit
- Numeric values may need rounding based on `device_class`

## Extension Path

When requirements emerge, the Signal can be extended:

```python
# Phase 2: Add typing if needed for smart UI
@dataclass
class Signal:
    id: str
    value: str
    unit: str
    label: str = ""
    signal_type: str = ""      # "number", "boolean", etc.
    device_class: str = ""     # "temperature", "power", etc.

# Phase 3: Add temporal data if needed
@dataclass
class Signal:
    ...
    last_updated: Optional[str] = None  # ISO timestamp as string
```

## Consequences

### Positive

- Matches PoC's proven approach - low risk
- Simple to implement, test, and debug
- Clear separation: adapters handle complexity, Signal stays simple
- Frontend development can proceed with stable contract

### Negative

- May need to revisit if rich metadata requirements emerge
- Some HomeAssistant features (device_class grouping) deferred
- No built-in support for value history or change tracking

### Risks & Mitigations

| Risk                             | Mitigation                                                |
| -------------------------------- | --------------------------------------------------------- |
| Need typed values for UI widgets | Add `signal_type` field when needed (backward compatible) |
| HomeAssistant has richer data    | Store in adapter, expose via Signal extension when needed |
| String values limit calculations | Adapters can maintain typed internal state if needed      |

## Implementation Notes

1. **Location:** `packages/shared/` for Signal definition (used by both backend and can
   generate TS types)
2. **Validation:** Use pydantic v2 for runtime validation
3. **Serialization:** JSON-compatible by design (all fields are primitives)
4. **Testing:** Unit tests for each adapter's normalization logic

## Related Decisions

- [ADR-001: State Management](ADR-001-state-management.md) - Signal instances stored in
  state layer
- [ADR-002: Backend Runtime](ADR-002-backend-runtime.md) - Adapters implemented in
  Python
- [ADR-004: Frontend Stack](ADR-004-frontend-stack.md) - TypeScript types generated from
  Signal schema

## References

- PoC implementation:
  [old/backend/home-observer/smarthome.py](../../old/backend/home-observer/smarthome.py)
- PoC OpenHAB adapter:
  [old/backend/home-observer/openhab.py](../../old/backend/home-observer/openhab.py)
- OpenHAB API examples:
  [docs/ll/openhab-example-api-calls.md](../ll/openhab-example-api-calls.md)
- HomeAssistant WebSocket API: https://developers.home-assistant.io/docs/api/websocket/

Note: The PoC references are not checked into the main codebase.

_January 5, 2026_
