# Adapter System

!!! warning "Work in progress" This explanation will be expanded as part of the
documentation content phase.

## Overview

The adapter system is how lumehaven connects to smart home platforms. It uses three key
patterns:

1. **Protocol** (PEP 544) — Structural subtyping for adapter interface
2. **Factory** — `create_adapter()` instantiates the right adapter from config
3. **Manager** — `AdapterManager` handles lifecycle, retry, and backoff

## The Protocol Pattern

Instead of inheritance, lumehaven uses Python's `Protocol` for adapter interfaces. This
means:

- Adapters don't need to inherit from a base class
- Any class with the right methods satisfies the interface
- Type checkers validate compliance at development time
- `runtime_checkable` enables runtime validation too

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class SmartHomeAdapter(Protocol):
    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    async def fetch_signals(self) -> list[Signal]: ...
    async def subscribe(self, callback: SignalCallback) -> None: ...
```

For the full interface, see the
[SmartHomeAdapter API reference](../reference/api/adapters.md).

## Factory Pattern

The factory function maps adapter type strings (from config) to concrete
implementations:

```python
adapter = create_adapter(adapter_config)
```

New adapters auto-register by adding a branch to the factory. See the
[Add a New Adapter](../how-to/add-adapter.md) how-to guide.

## Adapter Manager

The `AdapterManager` orchestrates adapter lifecycle:

- **Startup:** Connect all configured adapters
- **Retry:** Exponential backoff on connection failures
- **Monitoring:** Health checks for adapter status
- **Shutdown:** Graceful disconnect on app termination

## Current Adapters

| Adapter       | Status         | Smart Home System                                |
| ------------- | -------------- | ------------------------------------------------ |
| OpenHAB       | ✅ Implemented | [OpenHAB](https://www.openhab.org/)              |
| HomeAssistant | ⏳ Planned     | [Home Assistant](https://www.home-assistant.io/) |

## Related Decisions

- [ADR-001: State Management](../adr/ADR-001-state-management.md)
- [ADR-005: Signal Abstraction](../adr/ADR-005-signal-abstraction.md)
