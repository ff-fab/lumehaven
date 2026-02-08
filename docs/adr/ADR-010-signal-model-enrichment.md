# ADR-010: Signal Model Enrichment

## Status

Accepted **Date:** 2026-02-08

**Amends:** [ADR-005](ADR-005-signal-abstraction.md) (Signal Identity and Metadata
Abstraction)

## Context

ADR-005 established a minimal Signal model: `id`, `value` (string), `unit`, `label`.
This was proven sufficient for the backend implementation phase. However, as frontend
development begins, the minimal model creates a tension:

**The "dumb frontend" principle is undermined by string-only values.**

The PoC (`old/frontend/home-front/`) demonstrates the problem. Dashboard components
must interpret string values to make rendering decisions:

```jsx
// Checking for undefined states — requires knowing platform-specific strings
{items?.DryerOpState
  && !["aus","unbekannt"].includes(items.DryerOpState.value) && ...}

// Boolean logic via string comparison
{items?.Sauna.value === "ON" && ...}

// Special-value filtering with mixed-case platform strings
{!["Aus","NULL","UNDEF"].includes(items.DishWasherOpState.value) && ...}
```

This pushes type interpretation into the frontend, where it becomes:
- **Fragile** — hardcoded string lists that must match platform-specific values
- **Duplicated** — every component re-implements NULL/UNDEF handling
- **Coupling** — the frontend must know about OpenHAB's `"UNDEF"` vs
  HomeAssistant's `"unavailable"` vs German `"unbekannt"`

The backend already has this knowledge in adapters. The fix: **formalize the contract**
so the backend tells the frontend what kind of value this is and whether it's available.

This was tracked as TODO item T6 ("Signal Value Type — String-Only vs. Rich Types")
and gate task `lh-6yy.2`.

## Decision Drivers

1. **Frontend simplicity** — the frontend should not parse strings to determine types,
   availability, or boolean states. The "dumb frontend" principle must be preserved at
   the contract level, not just by convention
2. **Adapter-contained normalization** — all platform-specific logic (UNDEF, NULL,
   unavailable, unknown, ON/OFF, UP/DOWN, aus/unbekannt) must be resolved in adapters,
   not leaked to the API contract
3. **CSS-driven conditional rendering** — with ADR-008's `data-available` attribute,
   the `<Signal>` component can hide unavailable signals purely via CSS, but only if the
   backend provides a boolean `available` flag
4. **Future dashboard modes** — widget engines and template-driven dashboards need typed
   values for conditional logic without string parsing
5. **Backward compatibility** — existing REST and SSE API consumers should not break;
   new fields are additive

## Considered Options

### Option 1: Keep String-Only, Add `available` Flag

```python
@dataclass
class Signal:
    id: str
    value: str           # Still string-only
    unit: str = ""
    label: str = ""
    available: bool = True   # NEW: False for UNDEF/NULL/unavailable
```

**Pros:** Minimal change; frontend only gains visibility control.
**Cons:** Frontend still cannot do logic (thresholds, toggles) without parsing strings.

### Option 2: Widen `value` Type with `display_value`

```python
@dataclass
class Signal:
    id: str
    value: str | int | float | bool | None   # Typed for logic
    display_value: str                         # Pre-formatted for rendering
    unit: str = ""
    label: str = ""
    available: bool = True
    signal_type: SignalType = SignalType.STRING
```

**Pros:** Frontend can use native types for logic AND display pre-formatted text.
**Cons:** Wider `value` type touches all serialization paths; `signal_type` adds a new
enum.

### Option 3: Typed Value + Discriminator (No `display_value`)

```python
@dataclass
class Signal:
    id: str
    value: str | int | float | bool | None
    unit: str = ""
    label: str = ""
    signal_type: SignalType = SignalType.STRING
```

**Pros:** Simpler than Option 2; fewer fields.
**Cons:** Frontend must format numbers itself (locale, decimals) — re-introduces
formatting logic that should be backend-owned.

## Decision Matrix

| Criterion                           | Option 1 | Option 2 | Option 3 |
| ----------------------------------- | -------- | -------- | -------- |
| Frontend simplicity (display)       | 4        | 5        | 3        |
| Frontend logic capability           | 2        | 5        | 5        |
| Backend formatting ownership        | 4        | 5        | 2        |
| Adapter impact (implementation)     | 5        | 3        | 3        |
| Backward compatibility              | 5        | 4        | 4        |
| CSS-driven visibility               | 5        | 5        | 3        |
| Future dashboard mode support       | 2        | 5        | 4        |
| **Total**                           | **27**   | **32**   | **24**   |

_Scale: 1 (poor) to 5 (excellent)_

## Decision

**Use Option 2: Full enrichment — typed `value`, `display_value`, `available` flag,
and `signal_type` discriminator.**

### Enriched Signal Model

```python
from dataclasses import dataclass
from enum import StrEnum


class SignalType(StrEnum):
    """Semantic type discriminator for signal values.

    Enables type-aware rendering without string parsing.
    """
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ENUM = "enum"        # Finite set: washing machine states, etc.
    DATETIME = "datetime"


@dataclass(frozen=True, slots=True)
class Signal:
    id: str
    value: str | int | float | bool | None  # Typed: native value for logic
    display_value: str                        # Pre-formatted: always render this
    unit: str = ""
    label: str = ""
    available: bool = True                    # False for UNDEF/NULL/unavailable
    signal_type: SignalType = SignalType.STRING
```

### Field Semantics

| Field           | Type                             | Purpose                          | Who sets it     |
| --------------- | -------------------------------- | -------------------------------- | --------------- |
| `id`            | `str`                            | Unique identifier (prefixed)     | Adapter         |
| `value`         | `str\|int\|float\|bool\|None`    | Typed value for frontend logic   | Adapter         |
| `display_value` | `str`                            | Pre-formatted for rendering      | Adapter         |
| `unit`          | `str`                            | Unit symbol for display          | Adapter         |
| `label`         | `str`                            | Human-readable name              | Adapter         |
| `available`     | `bool`                           | Whether the signal has a valid value | Adapter     |
| `signal_type`   | `SignalType`                     | Semantic type discriminator      | Adapter         |

### Adapter Mapping Rules

**Availability:**

| Platform value                  | `available` | `value`       | `display_value` |
| ------------------------------- | ----------- | ------------- | --------------- |
| OpenHAB `"UNDEF"`              | `False`     | `None`        | `""`            |
| OpenHAB `"NULL"`               | `False`     | `None`        | `""`            |
| HomeAssistant `"unavailable"`  | `False`     | `None`        | `""`            |
| HomeAssistant `"unknown"`      | `False`     | `None`        | `""`            |
| Any valid value                | `True`      | typed value   | formatted       |

**Type coercion:**

| Source                                          | `signal_type`  | `value` example | `display_value` |
| ----------------------------------------------- | -------------- | --------------- | --------------- |
| `Number:Temperature` with `"21.5 °C"`           | `NUMBER`       | `21.5` (float)  | `"21.5"`        |
| `Switch` with `"ON"`                            | `BOOLEAN`      | `True`          | `"An"` ¹        |
| `Rollershutter` with `"75"`                     | `NUMBER`       | `75` (int)      | `"75"`          |
| `String` with `"Eco 40"`                        | `STRING`       | `"Eco 40"`      | `"Eco 40"`      |
| Washing machine `opState` with known enum values | `ENUM`         | `"running"`     | `"Waschen"` ¹   |
| `DateTime` with ISO string                      | `DATETIME`     | `"2026-02-08…"` | `"08.02."`      |

¹ `display_value` is locale-formatted by the adapter if applicable.

### JSON Wire Format

REST and SSE responses include all fields:

```json
{
  "id": "oh:LivingRoom_Temp",
  "value": 21.5,
  "display_value": "21.5",
  "unit": "°C",
  "label": "Living Room Temperature",
  "available": true,
  "signal_type": "number"
}
```

When unavailable:

```json
{
  "id": "oh:DryerOpState",
  "value": null,
  "display_value": "",
  "unit": "",
  "label": "Dryer",
  "available": false,
  "signal_type": "string"
}
```

### Frontend Consumption

With this contract, the `<Signal>` component becomes trivial:

```tsx
function Signal({ id, signal }: SignalProps) {
  const resolved = signal ?? useSignalById(id);
  if (!resolved) return null;

  return (
    <span
      className="signal"
      data-available={resolved.available}
      data-type={resolved.signal_type}
      data-id={resolved.id}
    >
      <span className="signal__value">{resolved.display_value}</span>
      {resolved.unit && <span className="signal__unit">{resolved.unit}</span>}
    </span>
  );
}
```

And conditional logic uses native types — no string parsing:

```tsx
// Boolean: toggle switch
{signal.value === true && <span>Active</span>}

// Number: threshold check
{typeof signal.value === 'number' && signal.value > 30 && <HighTempWarning />}

// Availability: CSS handles it
// .signal[data-available="false"] { display: none; }
```

## Impact on Existing Code

| Component             | Change                                                       |
| --------------------- | ------------------------------------------------------------ |
| `Signal` dataclass    | Add `display_value`, `available`, `signal_type`; widen `value` |
| `SignalType` enum     | New `StrEnum` in `core/signal.py`                            |
| `is_undefined()`      | Deprecated — use `signal.available` instead                  |
| `UNDEFINED_VALUE`, `NULL_VALUE` | Kept as internal adapter constants; not in API contract |
| OpenHAB adapter       | Must set `display_value`, `available`, `signal_type`, typed `value` |
| `SignalResponse` (Pydantic) | Add new fields; `value` becomes `str\|int\|float\|bool\|None` |
| SSE event format      | New fields in JSON payload (additive, non-breaking)          |
| All existing tests    | Must update Signal construction and assertions               |

## Consequences

### Positive

- Frontend components never parse strings for type or availability information
- Conditional rendering (`data-available`) works via pure CSS
- Native typed `value` enables frontend logic without string comparison
- `display_value` preserves the "backend does all formatting" principle
- `signal_type` enables type-specific component rendering (sliders for numbers,
  toggles for booleans) without heuristics
- Additive change — existing consumers that only use `id`, `value` (as string),
  `unit`, `label` continue to work

### Negative

- Larger JSON payloads (3 new fields per signal; ~50-80 bytes each)
- Adapter implementation complexity increases (must determine type and format
  `display_value`)
- `value` being a union type requires careful handling in both Python (pydantic
  discriminated serialization) and TypeScript

### Risks & Mitigations

| Risk                                    | Mitigation                                       |
| --------------------------------------- | ------------------------------------------------ |
| `display_value` diverges from `value`   | Adapter tests verify consistency between fields  |
| Wrong `signal_type` assignment          | Adapter integration tests with real fixture data |
| Union `value` type complicates backend  | Pydantic handles serialization; TypeScript uses  |
|                                         | discriminated unions with `signal_type`           |

## Related Decisions

- [ADR-005](ADR-005-signal-abstraction.md) — Original minimal Signal model (this ADR
  amends it)
- [ADR-008](ADR-008-frontend-package-architecture.md) — `@lumehaven/core` types mirror
  this enriched model
- [ADR-009](ADR-009-dashboard-ownership.md) — Dashboard components consume enriched
  signals

## References

- TODO item T6: "Signal Value Type — String-Only vs. Rich Types"
  (`docs/TODO/README.md`)
- Gate task `lh-6yy.2`: "Evaluate signal value type"
- PoC frontend patterns: `old/frontend/home-front/src/components/Header.js`

_February 2026_
