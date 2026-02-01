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

if TYPE_CHECKING:
    from pytest import Session

# =============================================================================
# Coverage Threshold Validation Hook
# =============================================================================
# This hook runs after pytest completes and validates per-module coverage
# against risk-based thresholds defined in docs/testing/03-coverage-strategy.md
#
# Triggered automatically when --cov is used and coverage.json exists.

# Risk-based thresholds: (line_threshold, branch_threshold)
COVERAGE_THRESHOLDS: dict[str, tuple[int, int]] = {
    # Critical risk (90% line, 85% branch)
    "adapters/openhab/adapter.py": (90, 85),
    "adapters/manager.py": (90, 85),
    # High risk (85% line, 80% branch)
    "config.py": (85, 80),
    "state/store.py": (85, 80),
    # Medium risk (80% line, 75% branch)
    "api/routes.py": (80, 75),
    "api/sse.py": (80, 75),
    # Default for all other modules (80% line, 70% branch)
    "__default__": (80, 70),
}


def _get_threshold(module_path: str) -> tuple[int, int]:
    """Get (line, branch) threshold for a module, with fallback to default."""
    # Normalize: extract path relative to lumehaven/
    normalized = module_path
    for prefix in ("src/lumehaven/", "lumehaven/"):
        if prefix in normalized:
            normalized = normalized.split(prefix)[-1]
            break

    # Exact match
    if normalized in COVERAGE_THRESHOLDS:
        return COVERAGE_THRESHOLDS[normalized]

    # Directory prefix match (longest wins)
    best_match = "__default__"
    best_len = 0
    for pattern in COVERAGE_THRESHOLDS:
        if pattern == "__default__":
            continue
        prefix = pattern.removesuffix(".py").rstrip("/")
        if normalized.startswith(prefix) and len(pattern) > best_len:
            best_match = pattern
            best_len = len(pattern)

    return COVERAGE_THRESHOLDS[best_match]


def _check_coverage_thresholds(coverage_file: Path) -> list[str]:
    """Check coverage.json against thresholds, return list of violations."""
    if not coverage_file.exists():
        return []  # No coverage data, skip validation

    with coverage_file.open() as f:
        data: dict[str, Any] = json.load(f)

    violations: list[str] = []
    files = data.get("files", {})

    for filepath, file_data in files.items():
        summary = file_data.get("summary", {})

        total_lines = summary.get("num_statements", 0)
        covered_lines = summary.get("covered_lines", 0)
        line_rate = (covered_lines / total_lines * 100) if total_lines > 0 else 100.0

        total_branches = summary.get("num_branches", 0)
        covered_branches = summary.get("covered_branches", 0)
        branch_rate = (
            (covered_branches / total_branches * 100) if total_branches > 0 else 100.0
        )

        line_thresh, branch_thresh = _get_threshold(filepath)

        # Shorten path for display
        display_path = filepath
        if "src/lumehaven/" in display_path:
            display_path = display_path.split("src/lumehaven/")[-1]

        if line_rate < line_thresh:
            violations.append(
                f"{display_path}: line coverage {line_rate:.1f}% < {line_thresh}%"
            )
        if branch_rate < branch_thresh:
            violations.append(
                f"{display_path}: branch coverage {branch_rate:.1f}% < {branch_thresh}%"
            )

    return violations


def pytest_sessionfinish(session: Session, exitstatus: int) -> None:
    """Validate per-module coverage thresholds after test session.

    Only runs when:
    1. Tests passed (exitstatus == 0)
    2. Coverage was collected (coverage.json exists)

    This provides immediate feedback on coverage regressions without
    requiring a separate CI step.
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
