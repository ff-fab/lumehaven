"""Smart home adapters - implementations of the SmartHomeAdapter protocol.

This package auto-registers all adapter factories when imported.
To add a new adapter:
1. Create the adapter module (e.g., adapters/homeassistant/)
2. Add @register_adapter_factory decorator to its factory function
3. Import the module below to trigger registration
"""

# Import adapter modules to trigger factory registration.
# Each module uses @register_adapter_factory to self-register.
from lumehaven.adapters import openhab as _openhab  # noqa: F401
from lumehaven.adapters.protocol import SmartHomeAdapter

# Future adapters:
# from lumehaven.adapters import homeassistant as _homeassistant  # noqa: F401

__all__ = ["SmartHomeAdapter"]
