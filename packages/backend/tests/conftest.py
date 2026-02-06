"""Global test configuration and fixtures for lumehaven backend tests.

This conftest.py provides fixtures available to all tests (unit and integration).
More specific fixtures should be placed in subdirectory conftest.py files.

Fixture Scope Guidelines (from test strategy):
- function: Default, isolated tests
- class: Shared within test class
- module: Expensive setup shared across module
- session: Very expensive, shared across all tests (use sparingly)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from lumehaven.core.signal import Signal

# Add tests directory to path so test utilities can be imported
# e.g., `from tests.fixtures.async_utils import wait_for_condition`
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import shared fixtures from fixtures/ to make them available to all tests
# pytest_plugins would be cleaner but requires package structure changes
from lumehaven.state.store import SignalStore  # noqa: E402
from tests.coverage_config import (  # noqa: E402
    get_module_for_file,
    get_threshold,
    normalize_path,
)
from tests.fixtures.config import (  # noqa: E402, F401
    _reset_settings_cache,
    tmp_config_file,
)

if TYPE_CHECKING:
    from pytest import Session


# =============================================================================
# Shared Fixtures
# =============================================================================


@pytest.fixture
def signal_store() -> SignalStore:
    """Create a fresh SignalStore instance for testing.

    Returns isolated store — not the singleton from get_signal_store().
    This fixture is available to all tests (unit and integration).
    """
    return SignalStore()


# =============================================================================
# Coverage Threshold Validation Hook
# =============================================================================
# This hook runs after pytest completes and validates module-level coverage
# against risk-based thresholds.  Threshold definitions and helpers live in
# tests/coverage_config.py (single source of truth).
#
# Triggered automatically when --cov is used and coverage.json exists.


def _check_coverage_thresholds(coverage_file: Path) -> list[str]:
    """Aggregate per-module coverage and check against thresholds."""
    if not coverage_file.exists():
        return []

    with coverage_file.open() as f:
        data: dict[str, Any] = json.load(f)

    # Accumulate totals per module
    module_totals: dict[str, dict[str, int]] = {}
    for filepath, file_data in data.get("files", {}).items():
        normalized = normalize_path(filepath)
        module = get_module_for_file(normalized)
        summary = file_data.get("summary", {})

        if module not in module_totals:
            module_totals[module] = {
                "stmts": 0,
                "cov_l": 0,
                "branches": 0,
                "cov_b": 0,
            }
        t = module_totals[module]
        t["stmts"] += summary.get("num_statements", 0)
        t["cov_l"] += summary.get("covered_lines", 0)
        t["branches"] += summary.get("num_branches", 0)
        t["cov_b"] += summary.get("covered_branches", 0)

    # Check each module aggregate against its threshold
    violations: list[str] = []
    for module, totals in sorted(module_totals.items()):
        line_thresh, branch_thresh = get_threshold(module)
        line_rate = (
            (totals["cov_l"] / totals["stmts"] * 100) if totals["stmts"] > 0 else 100.0
        )
        branch_rate = (
            (totals["cov_b"] / totals["branches"] * 100)
            if totals["branches"] > 0
            else 100.0
        )

        if line_rate < line_thresh:
            violations.append(
                f"{module}: line coverage {line_rate:.1f}% < {line_thresh}%"
            )
        if branch_rate < branch_thresh:
            violations.append(
                f"{module}: branch coverage {branch_rate:.1f}% < {branch_thresh}%"
            )

    return violations


def pytest_sessionfinish(session: Session, exitstatus: int) -> None:
    """Validate module-level coverage thresholds after test session.

    Files are grouped by directory module (e.g. ``api/``, ``adapters/openhab/``)
    and coverage is aggregated (weighted by statement/branch count) before
    checking against risk-based thresholds.

    Only runs when tests passed and coverage.json exists.
    """
    # Only check if tests passed
    if exitstatus != 0:
        return

    # Look for coverage.json in the current directory
    coverage_file = Path("coverage.json")
    if not coverage_file.exists():
        # Also check backend root (when running from repo root)
        coverage_file = Path("packages/backend/coverage.json")

    if not coverage_file.exists():
        return  # No coverage data, skip

    violations = _check_coverage_thresholds(coverage_file)

    if violations:
        print("\n" + "=" * 70, file=sys.stderr)
        print("COVERAGE THRESHOLD VIOLATIONS", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        for v in violations:
            print(f"  ✗ {v}", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        print(
            "See docs/testing/03-coverage-strategy.md for threshold rationale.",
            file=sys.stderr,
        )
        # Modify exit status to indicate failure
        session.exitstatus = 1


# =============================================================================
# Signal Fixtures
# =============================================================================


@pytest.fixture
def sample_temperature_signal() -> Signal:
    """A typical temperature signal for testing."""
    return Signal(
        id="oh:LivingRoom_Temperature",
        value="21.5",
        unit="°C",
        label="Living Room Temperature",
    )


@pytest.fixture
def sample_switch_signal() -> Signal:
    """A typical switch signal for testing."""
    return Signal(
        id="oh:LivingRoom_Light",
        value="ON",
        unit="",
        label="Living Room Light",
    )


@pytest.fixture
def sample_signals(
    sample_temperature_signal: Signal, sample_switch_signal: Signal
) -> dict[str, Signal]:
    """Collection of sample signals for bulk operations.

    Returns dict keyed by signal ID to match production APIs:
    - SignalStore.get_all() -> dict[str, Signal]
    - SignalStore.set_many(signals: dict[str, Signal])
    - SmartHomeAdapter.get_signals() -> dict[str, Signal]
    """
    return {
        sample_temperature_signal.id: sample_temperature_signal,
        sample_switch_signal.id: sample_switch_signal,
    }
