# Add a New Adapter

!!! abstract "Goal" Implement a new smart home adapter (e.g., HomeAssistant) by
following the `SmartHomeAdapter` Protocol, registering it in the factory, and adding
tests.

!!! warning "Work in progress" This guide will be completed as part of the documentation
content phase. The structure below outlines the planned content.

## Overview

lumehaven uses a Protocol-based adapter system (see
[Adapter System](../explanation/adapter-system.md)). Adding a new adapter requires four
steps:

1. Implement the `SmartHomeAdapter` Protocol
2. Register the adapter in the factory
3. Add configuration support
4. Write tests

## Step 1: Implement the Protocol

Create a new adapter package:

```
packages/backend/src/lumehaven/adapters/homeassistant/
├── __init__.py
├── adapter.py
└── units.py          # Optional: unit mapping
```

Your adapter must satisfy the `SmartHomeAdapter` Protocol:

```python
::: lumehaven.adapters.protocol.SmartHomeAdapter
    options:
      show_source: false
      members: false
```

## Step 2: Register in the Factory

Add your adapter type to the factory registry in `adapters/__init__.py`:

```python
# In create_adapter() function
if adapter_type == "homeassistant":
    from .homeassistant import HomeAssistantAdapter
    return HomeAssistantAdapter(config)
```

## Step 3: Add Configuration

Add the adapter's configuration to the config model in `config.py`.

## Step 4: Write Tests

Follow the [testing strategy](../testing/00-index.md):

- **Unit tests:** Mock external HTTP calls, test signal parsing
- **Integration tests:** Robot Framework with a mock server
- **Coverage:** New adapters inherit the "Critical" threshold (90% line, 85% branch)

## Reference

- [SmartHomeAdapter Protocol API](../reference/api/adapters.md)
- [OpenHAB adapter](../reference/api/adapters.md) — reference implementation
- [Testing guide](testing.md)
