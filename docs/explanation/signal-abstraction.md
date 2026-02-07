# Signal Abstraction

!!! warning "Work in progress" This explanation will be expanded as part of the
documentation content phase.

## The Model

A Signal is the universal data unit in lumehaven. It's deliberately minimal:

| Field   | Type                                  | Description                                        |
| ------- | ------------------------------------- | -------------------------------------------------- |
| `id`    | `str`                                 | Unique identifier (e.g., `LivingRoom_Temperature`) |
| `value` | `str \| float \| int \| bool \| None` | Current value, normalized                          |
| `unit`  | `str \| None`                         | Unit of measurement (e.g., `°C`, `%`)              |
| `label` | `str \| None`                         | Human-readable label                               |

For the full API, see the [Signal API reference](../reference/api/core.md).

## Why Minimal?

The Signal model is intentionally small — four fields. This decision
([ADR-005](../adr/ADR-005-signal-abstraction.md)) was driven by:

1. **Universality** — Every smart home system can produce these four fields
2. **Frontend simplicity** — The dashboard doesn't need to understand system-specific
   metadata
3. **Extensibility** — Additional metadata can be added later without breaking existing
   consumers

## Normalization

The backend normalizes raw smart home data before creating Signals:

- **Units** are standardized (e.g., OpenHAB's `°F` → `°C` if configured)
- **Values** are parsed from strings to native types
- **Labels** are cleaned (e.g., encoding fixes via `ftfy`)
- **Special states** like `NULL`, `UNDEF` are handled consistently

## Related Decisions

- [ADR-005: Signal Identity and Metadata Abstraction](../adr/ADR-005-signal-abstraction.md)
- [ADR-001: State Management](../adr/ADR-001-state-management.md)
