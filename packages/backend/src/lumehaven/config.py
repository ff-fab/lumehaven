"""Application configuration via pydantic-settings.

Configuration is loaded from environment variables and/or .env files.
All settings have sensible defaults for local development.
"""

from enum import StrEnum
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class SmartHomeType(StrEnum):
    """Supported smart home system types."""

    OPENHAB = "openhab"
    # HOMEASSISTANT = "homeassistant"  # Future: ADR pending


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Attributes:
        smart_home_type: The type of smart home system to connect to.
        openhab_url: Base URL for OpenHAB REST API.
        openhab_tag: Filter OpenHAB items by this tag (empty = all items).
        log_level: Logging level for the application.
        cors_origins: Allowed CORS origins for the frontend.
    """

    model_config = SettingsConfigDict(
        # Look for .env in multiple locations (first found wins).
        # Paths are relative to cwd, so we cover common run scenarios:
        # - From workspace root: .env
        # - From packages/backend: ../../.env
        # - From packages/backend/src: ../../../.env
        # Missing .env is fine — all settings have defaults
        env_file=(".env", "../../.env", "../../../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Smart home connection
    smart_home_type: SmartHomeType = SmartHomeType.OPENHAB
    openhab_url: str = "http://localhost:8080"
    openhab_tag: str = ""

    # Application settings
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    cors_origins: list[str] = ["http://localhost:5173"]  # Vite dev server default

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000

    # Subscriber settings
    subscriber_queue_size: int = 10000  # Max queued signals per SSE client


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings.

    Returns:
        Settings instance (cached after first call).
    """
    return Settings()
