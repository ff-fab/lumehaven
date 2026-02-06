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

from collections.abc import Generator
from unittest.mock import patch

import pytest

from tests.coverage_config import (
    MODULE_THRESHOLDS,
    get_module_for_file,
    get_threshold,
    normalize_path,
)

# Synthetic thresholds for algorithm-only tests — completely
# decoupled from production MODULE_THRESHOLDS so that changes
# to real thresholds or module clustering never break these tests.
_SYNTH_THRESHOLDS: dict[str, tuple[int, int]] = {
    "widgets": (80, 70),
    "widgets/*": (90, 85),
    "gizmos": (85, 80),
    "__root__": (30, 0),
}

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
    """Tests for get_module_for_file() — matching algorithm.

    Uses synthetic MODULE_THRESHOLDS so tests verify the algorithm
    rules only, not production module names or thresholds.

    Technique: Decision Table — the four matching rules documented
    in the function docstring, plus edge cases around wildcard priority.
    """

    @pytest.fixture(autouse=True)
    def _use_synthetic_thresholds(self) -> Generator[None]:
        """Replace MODULE_THRESHOLDS with synthetic data."""
        with patch.dict(
            "tests.coverage_config.MODULE_THRESHOLDS",
            _SYNTH_THRESHOLDS,
            clear=True,
        ):
            yield

    # -- Rule 1: Directory prefix match

    def test_directory_prefix_match(self) -> None:
        """Direct child of a module directory matches that key."""
        assert get_module_for_file("widgets/foo.py") == "widgets"

    def test_directory_prefix_match_init(self) -> None:
        """__init__.py in a module directory matches that key."""
        assert get_module_for_file("widgets/__init__.py") == "widgets"

    # -- Rule 2: Single-file module match

    def test_single_file_module(self) -> None:
        """<key>.py at the package root matches the key."""
        assert get_module_for_file("gizmos.py") == "gizmos"

    # -- Rule 3: Wildcard match (key/*)

    def test_wildcard_matches_subdir_file(self) -> None:
        """File in a subdirectory of a wildcard base is matched."""
        assert get_module_for_file("widgets/sub/foo.py") == "widgets/*"

    def test_wildcard_matches_deeply_nested(self) -> None:
        """Multi-level subdirectory still matches wildcard."""
        result = get_module_for_file("widgets/sub/deep/foo.py")
        assert result == "widgets/*"

    def test_wildcard_does_not_match_direct_child(self) -> None:
        """Direct child of base dir matches the concrete key,
        NOT the wildcard (wildcard requires a subdir)."""
        assert get_module_for_file("widgets/foo.py") == "widgets"

    # -- Rule 4: Fallback to __root__

    def test_fallback_to_root_for_init(self) -> None:
        """__init__.py at the package root falls back to __root__."""
        assert get_module_for_file("__init__.py") == "__root__"

    def test_fallback_to_root_for_unknown(self) -> None:
        """File not matching any key falls back to __root__."""
        assert get_module_for_file("unknown_module.py") == "__root__"


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
        list(MODULE_THRESHOLDS.items()),
        ids=list(MODULE_THRESHOLDS.keys()),
    )
    def test_known_keys_return_configured_threshold(
        self, module_key: str, expected: tuple[int, int]
    ) -> None:
        """Each configured key returns its (line, branch) threshold pair.

        Values derived from MODULE_THRESHOLDS — no hardcoded thresholds.
        """
        assert get_threshold(module_key) == expected

    def test_unknown_key_falls_back_to_root(self) -> None:
        """Unknown module key returns __root__ threshold."""
        assert get_threshold("nonexistent_module") == MODULE_THRESHOLDS["__root__"]

    def test_wildcard_key_resolves_from_dict(self) -> None:
        """Wildcard rule keys (e.g. 'adapters/*') look up directly.

        A *concrete* subdir name like 'adapters/openhab' is NOT a key
        and falls back to __root__.  Tests derive from MODULE_THRESHOLDS.
        """
        # Find a wildcard key dynamically
        wildcard_keys = [k for k in MODULE_THRESHOLDS if k.endswith("/*")]
        assert wildcard_keys, "Need at least one wildcard key"
        wk = wildcard_keys[0]
        base = wk[:-2]  # strip /*

        assert get_threshold(wk) == MODULE_THRESHOLDS[wk]
        # Concrete subdir is unknown → fallback
        assert get_threshold(f"{base}/unknown") == MODULE_THRESHOLDS["__root__"]
