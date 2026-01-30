"""Smart home adapters - implementations of the SmartHomeAdapter protocol.

This package provides:
- SmartHomeAdapter protocol for implementing new adapters
- AdapterManager for lifecycle management (startup, retry, shutdown)
- Factory registry for creating adapters from configuration

To add a new adapter:
1. Create the adapter module (e.g., adapters/homeassistant/)
2. Implement a _register() function that adds your factory to ADAPTER_FACTORIES
3. Import the module and call _register() at the bottom of this file
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from lumehaven.adapters.manager import AdapterManager
from lumehaven.adapters.protocol import SmartHomeAdapter

if TYPE_CHECKING:
    from lumehaven.config import AdapterConfig

# Registry mapping adapter type to factory function.
# Factory functions are registered by adapter modules to avoid circular imports.
# Key: type string (e.g., "openhab"), Value: callable that creates an adapter.
# Using Any for flexibility - each factory takes its specific config subtype.
ADAPTER_FACTORIES: dict[str, Callable[..., Any]] = {}


def create_adapter(config: AdapterConfig) -> SmartHomeAdapter:
    """Create an adapter instance from configuration.

    Uses the ADAPTER_FACTORIES registry to find the appropriate factory
    function based on the config's type field. Adapters register themselves
    by implementing a _register() function that's called during module init.

    Args:
        config: Adapter configuration (discriminated by type field).

    Returns:
        Configured adapter instance.

    Raises:
        NotImplementedError: If no factory is registered for the adapter type.
    """
    adapter_type = config.type
    factory = ADAPTER_FACTORIES.get(adapter_type)

    if factory is None:
        raise NotImplementedError(
            f"No factory registered for adapter type '{adapter_type}'. "
            f"Available types: {list(ADAPTER_FACTORIES.keys())}"
        )

    adapter: SmartHomeAdapter = factory(config)
    return adapter


# Import adapter modules and trigger factory registration.
# Each module implements a _register() function that adds its factory to the registry.
# NOTE: Must be after registry definition to avoid circular import.
from lumehaven.adapters import openhab as _openhab  # noqa: F401, E402

_openhab._register()

# Future adapters:
# from lumehaven.adapters import homeassistant as _homeassistant  # noqa: F401
# _homeassistant._register()

__all__ = [
    "AdapterManager",
    "ADAPTER_FACTORIES",
    "SmartHomeAdapter",
    "create_adapter",
]
