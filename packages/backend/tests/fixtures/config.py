"""Configuration test fixtures and factories.

Provides fixtures for testing config.py:
- Settings LRU cache management
- Temporary YAML config files
- Valid configuration dictionaries for mutation testing
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from lumehaven.config import get_settings


@pytest.fixture
def _reset_settings_cache():
    """Clear Settings LRU cache before and after test.

    The get_settings() function is cached with @lru_cache. Tests that modify
    environment variables or config files need a fresh Settings instance.

    Usage:
        def test_env_override(_reset_settings_cache, monkeypatch):
            monkeypatch.setenv("OPENHAB_URL", "http://custom:8080")
            settings = get_settings()
            assert settings.openhab_url == "http://custom:8080"
    """
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def tmp_config_file(tmp_path: Path):
    """Factory fixture for creating temporary YAML config files.

    Returns a callable that creates a config file with the given content
    and returns its path. Useful for testing YAML loading and validation.

    Usage:
        def test_yaml_loading(tmp_config_file):
            config_path = tmp_config_file('''
                adapters:
                  - type: openhab
                    name: test
                    url: http://localhost:8080
            ''')
            # config_path is a Path object pointing to the temp file
    """

    def _create_config(content: str, filename: str = "config.yaml") -> Path:
        """Create a temporary config file with the given content.

        Args:
            content: YAML content to write to the file.
            filename: Name of the config file (default: config.yaml).

        Returns:
            Path to the created config file.
        """
        config_file = tmp_path / filename
        config_file.write_text(content)
        return config_file

    return _create_config


def valid_openhab_config(**overrides: Any) -> dict[str, Any]:
    """Create a valid OpenHAB adapter config dict with optional overrides.

    All fields have sensible defaults. Pass keyword arguments to override
    specific fields for testing validation or edge cases.

    Args:
        **overrides: Fields to override in the config.

    Returns:
        Dictionary suitable for YAML serialization or direct validation.

    Examples:
        # Default config
        config = valid_openhab_config()

        # Override URL
        config = valid_openhab_config(url="http://custom:8080")

        # Invalid type for testing
        config = valid_openhab_config(type="invalid")
    """
    base = {
        "type": "openhab",
        "name": "openhab",
        "prefix": "oh",
        "url": "http://localhost:8080",
        "tag": "",
    }
    return {**base, **overrides}


def valid_homeassistant_config(**overrides: Any) -> dict[str, Any]:
    """Create a valid Home Assistant adapter config dict with optional overrides.

    All fields have sensible defaults. Pass keyword arguments to override
    specific fields for testing validation or edge cases.

    Args:
        **overrides: Fields to override in the config.

    Returns:
        Dictionary suitable for YAML serialization or direct validation.

    Examples:
        # Default config
        config = valid_homeassistant_config()

        # Override token
        config = valid_homeassistant_config(token="my-secret-token")
    """
    base = {
        "type": "homeassistant",
        "name": "homeassistant",
        "prefix": "ha",
        "url": "http://localhost:8123",
        "token": "",
    }
    return {**base, **overrides}


def valid_yaml_config(
    adapters: list[dict[str, Any]] | None = None,
    **extra_keys: Any,
) -> dict[str, Any]:
    """Create a valid root config dict suitable for YAML serialization.

    Args:
        adapters: List of adapter config dicts. Defaults to single OpenHAB adapter.
        **extra_keys: Additional top-level keys to include.

    Returns:
        Dictionary representing a complete config.yaml structure.

    Examples:
        # Single OpenHAB adapter
        config = valid_yaml_config()

        # Multiple adapters
        config = valid_yaml_config(adapters=[
            valid_openhab_config(name="home"),
            valid_homeassistant_config(name="cabin"),
        ])

        # With extra keys (for testing unknown key handling)
        config = valid_yaml_config(version="1.0")
    """
    if adapters is None:
        adapters = [valid_openhab_config()]
    return {"adapters": adapters, **extra_keys}
