"""Application configuration via pydantic-settings with YAML support.

Configuration sources (in priority order):
1. YAML config file (config.yaml) for multi-adapter setups
2. Environment variables for simple single-adapter setups

YAML files support environment variable interpolation: ${VAR_NAME}
"""

from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# -----------------------------------------------------------------------------
# Adapter Configuration Models
# -----------------------------------------------------------------------------


class OpenHABAdapterConfig(BaseModel):
    """Configuration for an OpenHAB adapter instance.

    Attributes:
        type: Must be "openhab" (discriminator field).
        name: Unique identifier for this adapter instance.
        prefix: Short prefix for signal ID namespacing.
        url: Base URL for OpenHAB REST API.
        tag: Filter items by this tag (empty = all items).
    """

    type: Literal["openhab"] = "openhab"
    name: str = "openhab"
    prefix: str = "oh"
    url: str = "http://localhost:8080"
    tag: str = ""


class HomeAssistantAdapterConfig(BaseModel):
    """Configuration for a Home Assistant adapter instance.

    Attributes:
        type: Must be "homeassistant" (discriminator field).
        name: Unique identifier for this adapter instance.
        prefix: Short prefix for signal ID namespacing.
        url: Base URL for Home Assistant API.
        token: Long-lived access token for authentication.
    """

    type: Literal["homeassistant"] = "homeassistant"
    name: str = "homeassistant"
    prefix: str = "ha"
    url: str = "http://localhost:8123"
    token: str = ""


# Discriminated union: Pydantic uses 'type' field to determine which model
AdapterConfig = Annotated[
    OpenHABAdapterConfig | HomeAssistantAdapterConfig,
    Field(discriminator="type"),
]


# -----------------------------------------------------------------------------
# Main Settings
# -----------------------------------------------------------------------------


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    For multi-adapter setups, use a YAML config file instead.
    These env vars provide a simpler 12-factor-compliant single-adapter config.

    Attributes:
        openhab_url: Base URL for OpenHAB REST API.
        openhab_tag: Filter OpenHAB items by this tag.
        log_level: Logging level for the application.
        cors_origins: Allowed CORS origins for the frontend.
        config_file: Path to YAML config file (optional).
    """

    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env", "../../../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Legacy single-adapter settings (used if no YAML config)
    openhab_url: str = "http://localhost:8080"
    openhab_tag: str = ""

    # Application settings
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    cors_origins: list[str] = ["http://localhost:5173"]

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000

    # Subscriber settings
    subscriber_queue_size: int = 10000

    # Config file path (if using YAML)
    config_file: str = "config.yaml"


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings.

    Returns:
        Settings instance (cached after first call).
    """
    return Settings()


# -----------------------------------------------------------------------------
# YAML Configuration Loading
# -----------------------------------------------------------------------------


def _expand_env_vars(value: str) -> str:
    """Expand ${VAR_NAME} patterns in a string with environment variables.

    Args:
        value: String potentially containing ${VAR_NAME} patterns.

    Returns:
        String with environment variables expanded.
        Missing variables are replaced with empty string.
    """
    pattern = re.compile(r"\$\{([^}]+)\}")
    return pattern.sub(lambda m: os.environ.get(m.group(1), ""), value)


def _expand_env_vars_recursive(obj: object) -> object:
    """Recursively expand environment variables in a data structure.

    Args:
        obj: Dict, list, or scalar value.

    Returns:
        Same structure with all string values having env vars expanded.
    """
    if isinstance(obj, dict):
        return {k: _expand_env_vars_recursive(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_expand_env_vars_recursive(item) for item in obj]
    if isinstance(obj, str):
        return _expand_env_vars(obj)
    return obj


def _find_config_file(filename: str) -> Path | None:
    """Search for config file in common locations.

    Args:
        filename: Name of the config file to find.

    Returns:
        Path to config file if found, None otherwise.
    """
    search_paths = [
        Path.cwd() / filename,  # Current directory
        Path.cwd() / "../../" / filename,  # From packages/backend
        Path.cwd() / "../../../" / filename,  # From packages/backend/src
    ]
    for path in search_paths:
        resolved = path.resolve()
        if resolved.is_file():
            return resolved
    return None


def load_adapter_configs() -> list[AdapterConfig]:
    """Load adapter configurations from YAML file or environment variables.

    Priority:
    1. If config.yaml exists with 'adapters' key, use that
    2. Otherwise, create single OpenHAB adapter from env vars (backwards compat)

    Returns:
        List of adapter configurations.

    Raises:
        ValueError: If YAML file exists but is invalid.
    """
    settings = get_settings()

    # Try to find and load YAML config
    config_path = _find_config_file(settings.config_file)

    if config_path is not None:
        return _load_from_yaml(config_path)

    # Fallback: single OpenHAB adapter from env vars
    return [
        OpenHABAdapterConfig(
            name="openhab",
            prefix="oh",
            url=settings.openhab_url,
            tag=settings.openhab_tag,
        )
    ]


def _load_from_yaml(config_path: Path) -> list[AdapterConfig]:
    """Load adapter configurations from a YAML file.

    Args:
        config_path: Path to the YAML configuration file.

    Returns:
        List of adapter configurations.

    Raises:
        ValueError: If YAML is invalid or missing required keys.
    """
    # Import here to avoid dependency if not using YAML
    import yaml

    with config_path.open() as f:
        raw_config = yaml.safe_load(f)

    if not isinstance(raw_config, dict):
        msg = f"Config file {config_path} must contain a YAML mapping"
        raise ValueError(msg)

    # Expand environment variables
    config = _expand_env_vars_recursive(raw_config)
    assert isinstance(config, dict)  # Type narrowing after recursive call

    if "adapters" not in config:
        msg = f"Config file {config_path} must have an 'adapters' key"
        raise ValueError(msg)

    adapters_raw = config["adapters"]
    if not isinstance(adapters_raw, list):
        msg = "'adapters' must be a list"
        raise ValueError(msg)

    # Parse each adapter config using discriminated union
    from pydantic import TypeAdapter

    adapter_list_type = TypeAdapter(list[AdapterConfig])
    return adapter_list_type.validate_python(adapters_raw)
