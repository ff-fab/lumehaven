# Signal Abstraction

## The Model

A Signal is the universal data unit in lumehaven. It's deliberately minimal — a frozen
dataclass with just four string fields:

!!! note "Enrichment planned (ADR-010)"
    The Signal model is being enriched with typed `value`, `display_value`, `available`,
    and `signal_type` fields. See [ADR-010](../adr/ADR-010-signal-model-enrichment.md)
    for the full specification. The documentation below describes the current
    implementation.

| Field   | Type  | Default | Description                                                   |
| ------- | ----- | ------- | ------------------------------------------------------------- |
| `id`    | `str` | —       | Unique identifier, prefixed by adapter (e.g., `oh:LivingRoom_Temp`) |
| `value` | `str` | —       | Pre-formatted, display-ready value (always a string)          |
| `unit`  | `str` | `""`    | Unit symbol for display (e.g., `°C`, `%`, `W`)               |
| `label` | `str` | `""`    | Human-readable name (e.g., `Living Room Temperature`)         |

**Key design principle:** `value` is *always* a string, pre-formatted by the backend.
The frontend never parses, converts, or interprets values — it renders them as-is.
This keeps the frontend "dumb" and lightweight
([ADR-005](../adr/ADR-005-signal-abstraction.md)).

```python
from lumehaven.core.signal import Signal

# A temperature reading
Signal(id="oh:LivingRoom_Temp", value="21.5", unit="°C", label="Living Room")

# A light switch — no unit needed
Signal(id="oh:Kitchen_Light", value="ON", unit="", label="Kitchen Light")

# An undefined sensor — special state preserved as-is
Signal(id="oh:Garage_Humidity", value="UNDEF", unit="%", label="Garage Humidity")
```

For the full API, see the [Signal API reference](../reference/api/core.md).

## Why Minimal?

The Signal model is intentionally small — four fields, all strings. This decision
([ADR-005](../adr/ADR-005-signal-abstraction.md)) was driven by:

1. **Universality** — Every smart home system can produce these four fields.
   OpenHAB items, Home Assistant entities, and future systems all map naturally.
2. **Frontend simplicity** — The dashboard doesn't need to understand system-specific
   metadata or perform type conversions. It receives display-ready strings.
3. **Extensibility** — Additional metadata can be added later without breaking existing
   consumers. The frozen dataclass provides immutability guarantees.
4. **Testability** — Simple, immutable value objects are easy to construct in tests.
   No mocking or complex setup required.

!!! info "Why all strings?"
    Smart home values are inherently heterogeneous — temperatures are floats, switches
    are booleans, timestamps are datetimes. Rather than the frontend handling type
    dispatch, the backend pre-formats everything to display strings. A temperature
    becomes `"21.5"`, a switch becomes `"ON"`, and the frontend doesn't care about the
    difference.

## Normalization Pipeline

The backend transforms raw smart home API data into Signals. Each adapter is responsible
for this normalization — the frontend never sees raw data.

### How It Works

```
Raw API response → Extract fields → Format value → Build Signal → Store
```

Using OpenHAB as a concrete example, here's how a raw API item becomes a Signal:

#### Step 1: Extract unit from `stateDescription.pattern`

OpenHAB items carry a state pattern like `"%.1f °C"` that defines both the display
format and the unit. The `extract_unit_from_pattern()` function parses this:

| Raw Pattern  | Extracted Unit | Format String |
| ------------ | -------------- | ------------- |
| `"%.1f °C"`  | `°C`           | `%.1f`        |
| `"%d %%"`    | `%`            | `%d`          |
| `"%s"`       | *(empty)*      | `%s`          |

If no pattern is available, the unit falls back to defaults based on the OpenHAB
`QuantityType` (e.g., `Temperature` → `°C` for SI).

#### Step 2: Format the value

Raw states are formatted according to the pattern's format string:

| Raw State      | Format   | QuantityType? | Result   |
| -------------- | -------- | ------------- | -------- |
| `"21.5678 °C"` | `%.1f`   | Yes           | `"21.6"` |
| `"42"`         | `%d`     | No            | `"42"`   |
| `"UNDEF"`      | `%.1f`   | Yes           | `"UNDEF"` |
| `"ON"`         | `%s`     | No            | `"ON"`   |

#### Step 3: Handle special states

OpenHAB uses sentinel strings for unavailable data. These are preserved as-is — they're
valid states, not errors:

| Special Value | Meaning                          | Handling              |
| ------------- | -------------------------------- | --------------------- |
| `"UNDEF"`     | Item exists but has no value yet | Passed through as-is  |
| `"NULL"`      | Item not initialized             | Passed through as-is  |

The `is_undefined()` helper lets consumers check for these:

```python
from lumehaven.core.signal import is_undefined

if is_undefined(signal.value):
    # Show placeholder in UI instead of the raw value
    ...
```

### Before and After

Here's a complete example showing what the OpenHAB REST API returns vs. the Signal that
lumehaven produces:

=== "Raw OpenHAB API response"

    ```json
    {
      "name": "LivingRoom_Temperature",
      "label": "Living Room Temperature",
      "type": "Number:Temperature",
      "state": "21.5678 °C",
      "stateDescription": {
        "pattern": "%.1f °C"
      }
    }
    ```

=== "Resulting Signal"

    ```python
    Signal(
        id="oh:LivingRoom_Temperature",
        value="21.6",       # Formatted per pattern
        unit="°C",          # Extracted from pattern
        label="Living Room Temperature",
    )
    ```

### Adapter Responsibility

Each adapter implements its own normalization. This is by design — different smart home
systems have different raw formats, and the adapter is the right place to encapsulate
that complexity.

| Concern                | Where It Happens       | Example                              |
| ---------------------- | ---------------------- | ------------------------------------ |
| Unit extraction        | Adapter (per-system)   | `stateDescription.pattern` → `"°C"`  |
| Value formatting       | Adapter (per-system)   | `"21.5678 °C"` → `"21.6"`           |
| Label cleaning         | Adapter (per-system)   | Encoding fixes via `ftfy`            |
| ID prefixing           | Adapter (via `prefix`) | `LivingRoom_Temp` → `oh:LivingRoom_Temp` |
| Special state handling | Adapter + core helper  | `"UNDEF"` preserved, `is_undefined()` |

For how this fits into the overall architecture, see
[Architecture](architecture.md). For the adapter system design, see
[Adapter System](adapter-system.md).

## Related Decisions

- [ADR-005: Signal Identity and Metadata Abstraction](../adr/ADR-005-signal-abstraction.md)
- [ADR-010: Signal Model Enrichment](../adr/ADR-010-signal-model-enrichment.md) (amends ADR-005)
- [ADR-001: State Management](../adr/ADR-001-state-management.md)
- [ADR-011: Command Architecture](../adr/ADR-011-command-architecture.md)
