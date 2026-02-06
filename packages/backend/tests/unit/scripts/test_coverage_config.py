"""Unit tests for tests/coverage_config.py — module-level threshold configuration.

Test Techniques Used:
- Specification-based Testing: Verifying normalize_path,
  get_module_for_file, get_threshold contracts
- Equivalence Partitioning: Path formats
  (src/lumehaven/, lumehaven/, bare), module types
- Boundary Value Analysis: Wildcard vs. concrete
  match priority, fallback behavior
- Decision Table: get_module_for_file matching rules
  (dir prefix, single-file, wildcard, fallback)
"""

from __future__ import annotations

import pytest

from tests.coverage_config import (
    MODULE_THRESHOLDS,
    get_module_for_file,
    get_threshold,
    normalize_path,
)

# =============================================================================
# normalize_path
# =============================================================================


class TestNormalizePath:
    """Tests for normalize_path() — stripping source prefixes.

    Technique: Equivalence Partitioning — three input classes:
    src/lumehaven/ prefix, lumehaven/ prefix, and already-normalized paths.
    """

    def test_strips_src_lumehaven_prefix(self) -> None:
        """Standard coverage.py output: src/lumehaven/..."""
        assert normalize_path("src/lumehaven/api/routes.py") == "api/routes.py"

    def test_strips_lumehaven_prefix(self) -> None:
        """Alternative prefix: lumehaven/ (without src/)."""
        assert normalize_path("lumehaven/core/signal.py") == "core/signal.py"

    def test_already_normalized_passthrough(self) -> None:
        """Path without known prefix is returned as-is."""
        result = normalize_path("adapters/openhab/adapter.py")
        assert result == "adapters/openhab/adapter.py"

    def test_deeply_nested_path(self) -> None:
        """Multi-level nesting is preserved after prefix strip."""
        result = normalize_path("src/lumehaven/adapters/openhab/units.py")
        assert result == "adapters/openhab/units.py"

    def test_root_init_file(self) -> None:
        """Package __init__.py at the root."""
        assert normalize_path("src/lumehaven/__init__.py") == "__init__.py"


# =============================================================================
# get_module_for_file
# =============================================================================


class TestGetModuleForFile:
    """Tests for get_module_for_file() — module matching logic.

    Technique: Decision Table — the four matching rules documented in the
    function docstring, plus edge cases around wildcard priority.
    """

    # -- Rule 1: Directory prefix match ("adapters/" matches adapters/manager.py)

    def test_directory_prefix_match(self) -> None:
        """Files directly in a module directory match the directory key."""
        assert get_module_for_file("adapters/manager.py") == "adapters"

    def test_directory_prefix_match_protocol(self) -> None:
        """Another direct child of adapters/."""
        assert get_module_for_file("adapters/protocol.py") == "adapters"

    def test_directory_prefix_match_init(self) -> None:
        """__init__.py in adapters/ matches the directory key."""
        assert get_module_for_file("adapters/__init__.py") == "adapters"

    # -- Rule 2: Single-file module match ("config" matches config.py)

    def test_single_file_module_config(self) -> None:
        """config.py at the package root matches the 'config' key."""
        assert get_module_for_file("config.py") == "config"

    # -- Rule 3: Wildcard match ("adapters/*" matches adapters/<subdir>/...)

    def test_wildcard_matches_adapter_subdir(self) -> None:
        """adapters/openhab/adapter.py matched by adapters/* wildcard."""
        assert get_module_for_file("adapters/openhab/adapter.py") == "adapters/*"

    def test_wildcard_matches_different_adapter(self) -> None:
        """A future adapter subdir auto-inherits via wildcard."""
        assert get_module_for_file("adapters/homeassistant/client.py") == "adapters/*"

    def test_wildcard_matches_nested_files(self) -> None:
        """Deeply nested files in adapter subdir still match wildcard."""
        assert get_module_for_file("adapters/openhab/units.py") == "adapters/*"

    def test_wildcard_does_not_match_direct_child(self) -> None:
        """adapters/manager.py is a direct child, NOT a subdir — matches 'adapters'."""
        # This tests the important distinction: wildcard requires subdir + nested file
        assert get_module_for_file("adapters/manager.py") == "adapters"

    # -- Rule 4: Fallback to __root__

    def test_fallback_to_root_for_init(self) -> None:
        """__init__.py at the package root falls back to __root__."""
        assert get_module_for_file("__init__.py") == "__root__"

    def test_fallback_to_root_for_unknown(self) -> None:
        """Any file not matching known keys falls back to __root__."""
        assert get_module_for_file("unknown_module.py") == "__root__"

    # -- Cross-cutting: other module directories

    def test_api_directory(self) -> None:
        """api/routes.py matches 'api' key."""
        assert get_module_for_file("api/routes.py") == "api"

    def test_api_sse(self) -> None:
        """api/sse.py matches 'api' key."""
        assert get_module_for_file("api/sse.py") == "api"

    def test_state_directory(self) -> None:
        """state/store.py matches 'state' key."""
        assert get_module_for_file("state/store.py") == "state"

    def test_core_directory(self) -> None:
        """core/signal.py matches 'core' key."""
        assert get_module_for_file("core/signal.py") == "core"


# =============================================================================
# get_threshold
# =============================================================================


class TestGetThreshold:
    """Tests for get_threshold() — threshold lookup with fallback.

    Technique: Equivalence Partitioning — known keys return their thresholds,
    unknown keys fall back to __root__.
    """

    @pytest.mark.parametrize(
        ("module_key", "expected"),
        [
            ("adapters", (85, 80)),
            ("adapters/*", (90, 85)),
            ("config", (85, 80)),
            ("state", (85, 80)),
            ("api", (80, 75)),
            ("core", (80, 70)),
            ("__root__", (30, 0)),
        ],
    )
    def test_known_keys_return_configured_threshold(
        self, module_key: str, expected: tuple[int, int]
    ) -> None:
        """Each configured key returns its (line, branch) threshold pair."""
        assert get_threshold(module_key) == expected

    def test_unknown_key_falls_back_to_root(self) -> None:
        """Unknown module key returns __root__ threshold."""
        assert get_threshold("nonexistent_module") == MODULE_THRESHOLDS["__root__"]

    def test_wildcard_resolved_key_uses_wildcard_threshold(self) -> None:
        """A concrete resolved wildcard key like 'adapters/openhab' is unknown —
        get_threshold looks up by the *rule key*, not the resolved module name.

        In practice, get_module_for_file returns the rule key 'adapters/*',
        which IS in MODULE_THRESHOLDS. This test documents that behavior.
        """
        # The wildcard rule key itself is valid
        assert get_threshold("adapters/*") == (90, 85)
        # A concrete subdir name is NOT a key — falls back
        assert get_threshold("adapters/openhab") == MODULE_THRESHOLDS["__root__"]
