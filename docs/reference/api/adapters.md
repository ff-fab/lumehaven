# Adapters

The adapter system connects lumehaven to smart home platforms. It uses Python's
`Protocol` pattern (PEP 544) for structural subtyping — adapters don't need to inherit
from a base class, they just need to implement the right methods.

## Protocol

::: lumehaven.adapters.protocol
    options:
      show_root_heading: true
      members_order: source

## Adapter Manager

::: lumehaven.adapters.manager
    options:
      show_root_heading: true
      members_order: source

## Factory

::: lumehaven.adapters
    options:
      show_root_heading: true
      members_order: source
      members:
        - create_adapter

## OpenHAB Adapter

::: lumehaven.adapters.openhab.adapter
    options:
      show_root_heading: true
      members_order: source

### Unit Mapping

::: lumehaven.adapters.openhab.units
    options:
      show_root_heading: true
      members_order: source
