"""OpenHAB adapter - connects to OpenHAB smart home system."""

from lumehaven.adapters.openhab.adapter import OpenHABAdapter
from lumehaven.adapters.protocol import SmartHomeAdapter
from lumehaven.config import OpenHABAdapterConfig

__all__ = ["OpenHABAdapter"]


def _register() -> None:
    """Register the OpenHAB adapter factory.

    Called by adapters/__init__.py after ADAPTER_FACTORIES is defined.
    """
    from lumehaven.adapters import ADAPTER_FACTORIES

    def create_openhab_adapter(config: OpenHABAdapterConfig) -> SmartHomeAdapter:
        """Factory function to create an OpenHAB adapter from configuration."""
        return OpenHABAdapter(
            base_url=config.url,
            tag=config.tag,
            name=config.name,
            prefix=config.prefix,
        )

    ADAPTER_FACTORIES["openhab"] = create_openhab_adapter
