"""Unit tests for config.py — Application configuration via pydantic-settings.

Test Techniques Used:
- Specification-based: Verifying Settings defaults and type constraints
- Decision Table: Discriminated union type routing
- Branch Coverage: _expand_env_vars_recursive type dispatch
- Error Guessing: Missing keys, invalid types, malformed YAML
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from pydantic import TypeAdapter, ValidationError

from lumehaven.config import (
    AdapterConfig,
    HomeAssistantAdapterConfig,
    OpenHABAdapterConfig,
    _expand_env_vars,
    _expand_env_vars_recursive,
    _find_config_file,
    _load_from_yaml,
    get_settings,
    load_adapter_configs,
)
from tests.fixtures.config import (
    valid_homeassistant_config,
    valid_openhab_config,
    valid_yaml_config,
)

if TYPE_CHECKING:
    from pytest import MonkeyPatch


# =============================================================================
# Tests
# =============================================================================


class TestSettings:
    """Specification-based tests for Settings pydantic model.

    Technique: Specification-based Testing — verifying documented defaults
    and environment variable override behavior.
    """

    def test_env_override_log_level(
        self, _reset_settings_cache: None, monkeypatch: MonkeyPatch
    ) -> None:
        """LOG_LEVEL environment variable overrides default."""
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")

        settings = get_settings()

        assert settings.log_level == "DEBUG"

    def test_env_override_port_type_coercion(
        self, _reset_settings_cache: None, monkeypatch: MonkeyPatch
    ) -> None:
        """PORT env var is coerced from string to int."""
        monkeypatch.setenv("PORT", "3000")

        settings = get_settings()

        assert settings.port == 3000
        assert isinstance(settings.port, int)

    def test_env_override_subscriber_queue_size(
        self, _reset_settings_cache: None, monkeypatch: MonkeyPatch
    ) -> None:
        """SUBSCRIBER_QUEUE_SIZE env var overrides default."""
        monkeypatch.setenv("SUBSCRIBER_QUEUE_SIZE", "5000")

        settings = get_settings()

        assert settings.subscriber_queue_size == 5000

    def test_get_settings_caching(self, _reset_settings_cache: None) -> None:
        """get_settings() returns same instance on repeated calls (LRU cache)."""
        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_cors_origins_default_is_list(self, _reset_settings_cache: None) -> None:
        """cors_origins is a list by default, not a string."""
        settings = get_settings()

        assert isinstance(settings.cors_origins, list)
        assert len(settings.cors_origins) == 1
        assert settings.cors_origins[0] == "http://localhost:5173"


class TestAdapterConfigModels:
    """Specification-based tests for adapter configuration models.

    Technique: Specification-based Testing — verifying defaults and
    custom value acceptance for each adapter type.
    """

    def test_openhab_config_defaults(self) -> None:
        """OpenHABAdapterConfig has documented defaults."""
        config = OpenHABAdapterConfig()

        assert config.type == "openhab"
        assert config.name == "openhab"
        assert config.prefix == "oh"
        assert config.url == "http://localhost:8080"
        assert config.tag == ""

    def test_openhab_config_custom_values(self) -> None:
        """OpenHABAdapterConfig accepts custom values."""
        config = OpenHABAdapterConfig(
            name="home_openhab",
            prefix="home",
            url="http://192.168.1.100:8080",
            tag="Dashboard",
        )

        assert config.name == "home_openhab"
        assert config.prefix == "home"
        assert config.url == "http://192.168.1.100:8080"
        assert config.tag == "Dashboard"

    def test_homeassistant_config_defaults(self) -> None:
        """HomeAssistantAdapterConfig has documented defaults."""
        config = HomeAssistantAdapterConfig()

        assert config.type == "homeassistant"
        assert config.name == "homeassistant"
        assert config.prefix == "ha"
        assert config.url == "http://localhost:8123"
        assert config.token == ""

    def test_homeassistant_config_custom_values(self) -> None:
        """HomeAssistantAdapterConfig accepts custom values."""
        config = HomeAssistantAdapterConfig(
            name="cabin_ha",
            prefix="cabin",
            url="http://cabin.local:8123",
            token="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9",
        )

        assert config.name == "cabin_ha"
        assert config.prefix == "cabin"
        assert config.url == "http://cabin.local:8123"
        assert config.token == "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9"


class TestDiscriminatedUnion:
    """Decision table tests for discriminated union type routing.

    Technique: Decision Table — mapping discriminator values to model types.

    | type           | Result Model              |
    |----------------|---------------------------|
    | "openhab"      | OpenHABAdapterConfig      |
    | "homeassistant"| HomeAssistantAdapterConfig|
    | "invalid"      | ValidationError           |
    | (missing)      | ValidationError           |
    """

    @pytest.mark.parametrize(
        ("input_factory", "expected_model", "expected_error", "error_match"),
        [
            (valid_openhab_config, OpenHABAdapterConfig, None, None),
            (valid_homeassistant_config, HomeAssistantAdapterConfig, None, None),
            (
                lambda: {"type": "invalid", "name": "test"},
                None,
                ValidationError,
                "Input tag 'invalid' found",
            ),
            (
                lambda: {"name": "test", "url": "http://localhost"},
                None,
                ValidationError,
                "Unable to extract tag",
            ),
        ],
        ids=["openhab-routes", "homeassistant-routes", "invalid-type", "missing-type"],
    )
    def test_discriminated_union_routing(
        self,
        input_factory: Any,
        expected_model: type[AdapterConfig] | None,
        expected_error: type[Exception] | None,
        error_match: str | None,
    ) -> None:
        """Parametrized decision table for AdapterConfig discriminated union."""
        adapter_type = TypeAdapter(AdapterConfig)
        payload = input_factory()

        if expected_error is not None:
            with pytest.raises(expected_error, match=error_match):
                adapter_type.validate_python(payload)
        else:
            config = adapter_type.validate_python(payload)
            assert isinstance(config, expected_model)
            assert config.type == payload["type"]


class TestEnvVarExpansion:
    """Branch coverage tests for environment variable expansion.

    Technique: Branch Coverage — testing each type dispatch branch in
    _expand_env_vars_recursive (dict, list, str, other).
    """

    def test_expand_single_var(self, monkeypatch: MonkeyPatch) -> None:
        """Single ${VAR} is expanded to its value."""
        monkeypatch.setenv("TEST_HOST", "192.168.1.100")

        result = _expand_env_vars("http://${TEST_HOST}:8080")

        assert result == "http://192.168.1.100:8080"

    def test_expand_multiple_vars(self, monkeypatch: MonkeyPatch) -> None:
        """Multiple ${VAR} patterns in same string are all expanded."""
        monkeypatch.setenv("HOST", "myhost")
        monkeypatch.setenv("PORT", "9000")

        result = _expand_env_vars("http://${HOST}:${PORT}/api")

        assert result == "http://myhost:9000/api"

    def test_missing_var_becomes_empty_string(self, monkeypatch: MonkeyPatch) -> None:
        """Missing environment variable expands to empty string."""
        monkeypatch.delenv("NONEXISTENT_VAR", raising=False)

        result = _expand_env_vars("prefix_${NONEXISTENT_VAR}_suffix")

        assert result == "prefix__suffix"

    def test_no_vars_returns_unchanged(self) -> None:
        """String without ${} patterns is returned unchanged."""
        result = _expand_env_vars("http://localhost:8080")

        assert result == "http://localhost:8080"

    def test_recursive_expands_dict(self, monkeypatch: MonkeyPatch) -> None:
        """_expand_env_vars_recursive handles nested dicts."""
        monkeypatch.setenv("MY_URL", "http://custom:8080")
        obj: dict[str, Any] = {
            "adapter": {
                "url": "${MY_URL}",
                "name": "test",
            }
        }

        result = _expand_env_vars_recursive(obj)

        assert result == {"adapter": {"url": "http://custom:8080", "name": "test"}}

    def test_recursive_expands_list(self, monkeypatch: MonkeyPatch) -> None:
        """_expand_env_vars_recursive handles lists."""
        monkeypatch.setenv("ORIGIN1", "http://app1.local")
        monkeypatch.setenv("ORIGIN2", "http://app2.local")
        obj = ["${ORIGIN1}", "${ORIGIN2}", "static"]

        result = _expand_env_vars_recursive(obj)

        assert result == ["http://app1.local", "http://app2.local", "static"]

    def test_recursive_preserves_non_strings(self) -> None:
        """_expand_env_vars_recursive passes through non-string scalars."""
        obj: dict[str, Any] = {
            "port": 8080,
            "enabled": True,
            "timeout": 30.5,
            "data": None,
        }

        result = _expand_env_vars_recursive(obj)

        assert result == {"port": 8080, "enabled": True, "timeout": 30.5, "data": None}

    def test_recursive_handles_mixed_structure(self, monkeypatch: MonkeyPatch) -> None:
        """_expand_env_vars_recursive handles complex nested structures."""
        monkeypatch.setenv("API_KEY", "secret123")
        obj: dict[str, Any] = {
            "adapters": [
                {"name": "test", "token": "${API_KEY}"},
                {"name": "other", "port": 8080},
            ],
            "debug": False,
        }

        result = _expand_env_vars_recursive(obj)

        assert result == {
            "adapters": [
                {"name": "test", "token": "secret123"},
                {"name": "other", "port": 8080},
            ],
            "debug": False,
        }


class TestFindConfigFile:
    """Tests for _find_config_file path resolution.

    Technique: Specification-based Testing — verifying file discovery
    in expected locations (current dir, ../../, ../../../) and None
    return when not found.
    """

    def test_finds_file_in_current_directory(self, tmp_path: Path) -> None:
        """Finds config file in current working directory."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("adapters: []")

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = _find_config_file("config.yaml")
        finally:
            os.chdir(original_cwd)

        assert result is not None
        assert result.name == "config.yaml"

    def test_finds_file_in_grandparent_directory(self, tmp_path: Path) -> None:
        """Finds config file via ../../ path (packages/backend → project root).

        The function searches three paths in order:
        1. Current directory
        2. ../../ (for running from packages/backend/)
        3. ../../../ (for running from packages/backend/src/)

        This test verifies the ../../ fallback works correctly.
        """
        # Create nested structure simulating packages/backend/
        nested_dir = tmp_path / "packages" / "backend"
        nested_dir.mkdir(parents=True)

        # Config file in project root (grandparent of working dir)
        config_file = tmp_path / "config.yaml"
        config_file.write_text("adapters: []")

        original_cwd = os.getcwd()
        try:
            os.chdir(nested_dir)
            result = _find_config_file("config.yaml")
        finally:
            os.chdir(original_cwd)

        assert result is not None
        assert result == config_file.resolve()

    def test_returns_none_when_not_found(self, tmp_path: Path) -> None:
        """Returns None when config file doesn't exist."""
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = _find_config_file("nonexistent.yaml")
        finally:
            os.chdir(original_cwd)

        assert result is None


class TestLoadFromYaml:
    """Error guessing and specification tests for YAML loading.

    Technique: Error Guessing — anticipating malformed YAML, missing keys,
    and invalid adapter types.
    """

    def test_valid_single_adapter_config(self, tmp_config_file) -> None:
        """Valid YAML with single adapter parses correctly."""
        content = """
adapters:
  - type: openhab
    name: home
    prefix: oh
    url: http://localhost:8080
    tag: Dashboard
"""
        config_path = tmp_config_file(content)

        result = _load_from_yaml(config_path)

        assert len(result) == 1
        assert isinstance(result[0], OpenHABAdapterConfig)
        assert result[0].name == "home"
        assert result[0].tag == "Dashboard"

    def test_valid_multiple_adapters(self, tmp_config_file) -> None:
        """Valid YAML with multiple adapters parses correctly."""
        content = """
adapters:
  - type: openhab
    name: home_oh
    prefix: oh
    url: http://openhab.local:8080
  - type: homeassistant
    name: home_ha
    prefix: ha
    url: http://homeassistant.local:8123
    token: my-token
"""
        config_path = tmp_config_file(content)

        result = _load_from_yaml(config_path)

        assert len(result) == 2
        assert isinstance(result[0], OpenHABAdapterConfig)
        assert isinstance(result[1], HomeAssistantAdapterConfig)
        assert result[1].token == "my-token"

    def test_env_var_interpolation_in_yaml(
        self, tmp_config_file, monkeypatch: MonkeyPatch
    ) -> None:
        """Environment variables in YAML values are expanded."""
        monkeypatch.setenv("OPENHAB_HOST", "192.168.1.50")
        monkeypatch.setenv("HA_TOKEN", "secret-token-123")
        content = """
adapters:
  - type: openhab
    name: home
    url: http://${OPENHAB_HOST}:8080
  - type: homeassistant
    name: cabin
    token: ${HA_TOKEN}
"""
        config_path = tmp_config_file(content)

        result = _load_from_yaml(config_path)

        assert isinstance(result[0], OpenHABAdapterConfig)
        assert result[0].url == "http://192.168.1.50:8080"
        assert isinstance(result[1], HomeAssistantAdapterConfig)
        assert result[1].token == "secret-token-123"

    def test_missing_adapters_key_raises_valueerror(self, tmp_config_file) -> None:
        """YAML without 'adapters' key raises ValueError."""
        content = """
other_key: value
"""
        config_path = tmp_config_file(content)

        with pytest.raises(ValueError, match="must have an 'adapters' key"):
            _load_from_yaml(config_path)

    def test_non_dict_root_raises_valueerror(self, tmp_config_file) -> None:
        """YAML with non-dict root raises ValueError."""
        content = """
- item1
- item2
"""
        config_path = tmp_config_file(content)

        with pytest.raises(ValueError, match="must contain a YAML mapping"):
            _load_from_yaml(config_path)

    def test_adapters_not_list_raises_valueerror(self, tmp_config_file) -> None:
        """YAML with 'adapters' as non-list raises ValueError."""
        content = """
adapters:
  type: openhab
  name: test
"""
        config_path = tmp_config_file(content)

        with pytest.raises(ValueError, match="'adapters' must be a list"):
            _load_from_yaml(config_path)

    def test_invalid_adapter_type_raises_validation_error(
        self, tmp_config_file
    ) -> None:
        """Invalid adapter type in YAML raises ValidationError."""
        content = """
adapters:
  - type: invalid_type
    name: test
"""
        config_path = tmp_config_file(content)

        with pytest.raises(ValidationError, match="Input tag 'invalid_type' found"):
            _load_from_yaml(config_path)

    def test_adapter_with_defaults_only(self, tmp_config_file) -> None:
        """Adapter with only type field uses defaults for other fields."""
        content = """
adapters:
  - type: openhab
"""
        config_path = tmp_config_file(content)

        result = _load_from_yaml(config_path)

        assert len(result) == 1
        assert result[0].name == "openhab"
        assert result[0].prefix == "oh"
        assert result[0].url == "http://localhost:8080"


class TestLoadAdapterConfigs:
    """Integration tests for load_adapter_configs() fallback behavior.

    Technique: Specification-based Testing — verifying YAML priority
    over environment variables and correct fallback behavior.
    """

    def test_uses_yaml_when_file_exists(
        self,
        _reset_settings_cache: None,
        tmp_path: Path,
    ) -> None:
        """load_adapter_configs uses YAML file when it exists."""
        config_file = tmp_path / "config.yaml"
        config_content = yaml.dump(
            valid_yaml_config(
                adapters=[
                    valid_openhab_config(name="from_yaml", url="http://yaml-host:8080"),
                ]
            )
        )
        config_file.write_text(config_content)

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = load_adapter_configs()
        finally:
            os.chdir(original_cwd)

        assert len(result) == 1
        assert result[0].name == "from_yaml"
        assert result[0].url == "http://yaml-host:8080"

    def test_falls_back_to_env_when_no_yaml(
        self,
        _reset_settings_cache: None,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
    ) -> None:
        """load_adapter_configs falls back to env vars when no YAML file."""
        monkeypatch.setenv("OPENHAB_URL", "http://env-openhab:8080")
        monkeypatch.setenv("OPENHAB_TAG", "EnvTag")

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = load_adapter_configs()
        finally:
            os.chdir(original_cwd)

        assert len(result) == 1
        assert isinstance(result[0], OpenHABAdapterConfig)
        assert result[0].url == "http://env-openhab:8080"
        assert result[0].tag == "EnvTag"

    def test_fallback_uses_settings_defaults(
        self,
        _reset_settings_cache: None,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
    ) -> None:
        """Fallback adapter uses Settings defaults when env vars not set."""
        monkeypatch.delenv("OPENHAB_URL", raising=False)
        monkeypatch.delenv("OPENHAB_TAG", raising=False)

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = load_adapter_configs()
        finally:
            os.chdir(original_cwd)

        assert len(result) == 1
        assert isinstance(result[0], OpenHABAdapterConfig)
        assert result[0].name == "openhab"
        assert result[0].prefix == "oh"
        assert result[0].url == "http://localhost:8080"
        assert result[0].tag == ""

    def test_yaml_env_interpolation_with_settings(
        self,
        _reset_settings_cache: None,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
    ) -> None:
        """YAML values with ${VAR} are interpolated from actual environment."""
        monkeypatch.setenv("CUSTOM_HOST", "dynamic-host.local")
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
adapters:
  - type: openhab
    name: dynamic
    url: http://${CUSTOM_HOST}:8080
""")

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = load_adapter_configs()
        finally:
            os.chdir(original_cwd)

        assert result[0].url == "http://dynamic-host.local:8080"
