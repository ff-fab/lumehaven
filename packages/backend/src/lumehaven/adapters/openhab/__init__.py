"""OpenHAB adapter - connects to OpenHAB smart home system."""

from lumehaven.adapters.openhab.adapter import OpenHABAdapter
from lumehaven.config import OpenHABAdapterConfig, register_adapter_factory

__all__ = ["OpenHABAdapter"]


@register_adapter_factory("openhab")
def create_openhab_adapter(config: OpenHABAdapterConfig) -> OpenHABAdapter:
    """Factory function to create an OpenHAB adapter from configuration."""
    return OpenHABAdapter(
        base_url=config.url,
        tag=config.tag,
        name=config.name,
        prefix=config.prefix,
    )
