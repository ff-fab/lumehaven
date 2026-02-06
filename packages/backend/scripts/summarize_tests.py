#!/usr/bin/env python3
"""Print a unified summary of pytest (unit) and Robot Framework (integration) results.

Reads machine-readable output from both test runners and prints a combined
pass/fail table. Designed to run after both suites complete (even if one failed),
giving developers a single glance at the full picture.

pytest results come from JUnit XML (--junitxml flag).
Robot Framework results come from output.xml (default Robot output).

Usage:
    # After running both suites:
    python scripts/summarize_tests.py

    # With custom paths:
    python scripts/summarize_tests.py \
        --unit-results results-unit.xml \
        --robot-output output.xml

Exit codes:
    0 - All tests passed (or skipped)
    1 - One or more test failures or errors
    2 - Neither results file was found
"""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

# =============================================================================
# Data Model
# =============================================================================


@dataclass
class SuiteResult:
    """Aggregated results for one test suite."""

    name: str
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0

    @property
    def total(self) -> int:
        return self.passed + self.failed + self.errors + self.skipped

    @property
    def ok(self) -> bool:
        return self.failed == 0 and self.errors == 0


# =============================================================================
# Parsers
# =============================================================================


def parse_junit_xml(path: Path) -> SuiteResult | None:
    """Parse pytest JUnit XML into a SuiteResult.

    JUnit XML schema (pytest flavour):
        <testsuites>
          <testsuite name="..." tests="N" errors="E" failures="F" skipped="S">
            <testcase .../>
          </testsuite>
        </testsuites>

    Some pytest versions emit a single <testsuite> root instead of wrapping in
    <testsuites>. We handle both.
    """
    if not path.exists():
        return None

    try:
        tree = ET.parse(path)  # noqa: S314 – trusted local file
    except ET.ParseError as exc:
        print(f"  ⚠ Could not parse {path}: {exc}", file=sys.stderr)
        return None

    root = tree.getroot()

    # Collect all <testsuite> elements regardless of nesting
    suites = root.iter("testsuite") if root.tag == "testsuites" else iter([root])

    total_tests = 0
    total_failures = 0
    total_errors = 0
    total_skipped = 0

    for suite in suites:
        total_tests += int(suite.get("tests", 0))
        total_failures += int(suite.get("failures", 0))
        total_errors += int(suite.get("errors", 0))
        total_skipped += int(suite.get("skipped", 0))

    passed = total_tests - total_failures - total_errors - total_skipped
    return SuiteResult(
        name="Unit (pytest)",
        passed=max(passed, 0),
        failed=total_failures,
        errors=total_errors,
        skipped=total_skipped,
    )


def parse_robot_output(path: Path) -> SuiteResult | None:
    """Parse Robot Framework output.xml into a SuiteResult.

    Uses robot.api.ExecutionResult for robust, version-safe parsing.
    Falls back to manual XML parsing if robot is not importable (shouldn't
    happen since robotframework is a dev dependency).
    """
    if not path.exists():
        return None

    try:
        from robot.api import ExecutionResult  # type: ignore[import-untyped]

        result = ExecutionResult(str(path))
        stats = result.statistics.total
        return SuiteResult(
            name="Integration (Robot)",
            passed=stats.passed,
            failed=stats.failed,
            skipped=getattr(stats, "skipped", 0),
        )
    except ImportError:
        # Fallback: parse XML manually (Robot output.xml schema)
        return _parse_robot_xml_fallback(path)
    except Exception as exc:
        print(f"  ⚠ Could not parse {path}: {exc}", file=sys.stderr)
        return None


def _parse_robot_xml_fallback(path: Path) -> SuiteResult | None:
    """Manual XML fallback for Robot output.xml.

    The <stat> element inside <total> holds pass/fail/skip attributes.
    """
    try:
        tree = ET.parse(path)  # noqa: S314
    except ET.ParseError as exc:
        print(f"  ⚠ Could not parse {path}: {exc}", file=sys.stderr)
        return None

    root = tree.getroot()
    # Robot 7+ uses <statistics><total><stat>
    total_stat = root.find(".//statistics/total/stat")
    if total_stat is None:
        print(f"  ⚠ Unexpected Robot output.xml structure in {path}", file=sys.stderr)
        return None

    passed = int(total_stat.get("pass", 0))
    failed = int(total_stat.get("fail", 0))
    skipped = int(total_stat.get("skip", 0))
    return SuiteResult(
        name="Integration (Robot)",
        passed=passed,
        failed=failed,
        skipped=skipped,
    )


# =============================================================================
# Rendering
# =============================================================================

# Box drawing characters for the summary table
_DOUBLE = "═"
_SINGLE = "─"
_PADDING = 2  # extra characters beyond widest content line

# ANSI color codes for terminal output
_GREEN = "\033[32m"
_RED = "\033[31m"
_RESET = "\033[0m"


def _hline(char: str, width: int) -> str:
    return char * width


def _format_row(name: str, passed: int, failed: int, skipped: int, total: int) -> str:
    """Format a single data row with consistent column alignment."""
    return f"  {name:<25} {passed:>7} {failed:>7} {skipped:>8} {total:>6}"


def _render_summary(results: list[SuiteResult]) -> None:
    """Print a compact summary table to stdout."""
    header = f"  {'Suite':<25} {'Passed':>7} {'Failed':>7} {'Skipped':>8} {'Total':>6}"

    # Pre-compute all rows to determine the dynamic width
    total_passed = 0
    total_failed = 0
    total_skipped = 0
    total_total = 0

    data_rows: list[str] = []
    for r in results:
        failures = r.failed + r.errors
        data_rows.append(_format_row(r.name, r.passed, failures, r.skipped, r.total))
        total_passed += r.passed
        total_failed += failures
        total_skipped += r.skipped
        total_total += r.total

    totals_row = _format_row(
        "TOTAL", total_passed, total_failed, total_skipped, total_total
    )

    if total_failed > 0:
        result_line = f"  Result: FAILURES DETECTED ✗ ({total_failed} failed)"
        result_colored = (
            f"  Result: {_RED}FAILURES DETECTED ✗ ({total_failed} failed){_RESET}"
        )
    else:
        result_line = "  Result: ALL TESTS PASSED ✓"
        result_colored = f"  Result: {_GREEN}ALL TESTS PASSED ✓{_RESET}"

    # Width = widest content line + padding for visual breathing room
    # Use plain text (no ANSI codes) for width calculation
    all_lines = [header, totals_row, result_line, *data_rows]
    width = max(len(line) for line in all_lines) + _PADDING

    # Print the table
    print()
    print(_hline(_DOUBLE, width))
    print("Test Summary".center(width))
    print(_hline(_DOUBLE, width))
    print(header)
    print(_hline(_SINGLE, width))
    for row in data_rows:
        print(row)
    print(_hline(_SINGLE, width))
    print(totals_row)
    print(_hline(_DOUBLE, width))
    print(result_colored)
    print(_hline(_DOUBLE, width))
    print()


# =============================================================================
# CLI
# =============================================================================


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Unified test summary for pytest + Robot Framework.",
    )
    parser.add_argument(
        "--unit-results",
        type=Path,
        default=Path("results-unit.xml"),
        help="Path to pytest JUnit XML file (default: results-unit.xml)",
    )
    parser.add_argument(
        "--robot-output",
        type=Path,
        default=Path("output.xml"),
        help="Path to Robot Framework output.xml (default: output.xml)",
    )
    return parser


def main() -> int:
    """Entry point. Returns the process exit code."""
    args = _build_parser().parse_args()

    unit_result = parse_junit_xml(args.unit_results)
    robot_result = parse_robot_output(args.robot_output)

    found: list[SuiteResult] = []
    not_found: list[str] = []

    if unit_result is not None:
        found.append(unit_result)
    else:
        not_found.append("Unit (pytest)")

    if robot_result is not None:
        found.append(robot_result)
    else:
        not_found.append("Integration (Robot)")

    # Nothing at all — likely a configuration problem
    if not found:
        warning_lines = [
            f"  ⚠ {name}: results file not found — NOT RUN or output missing"
            for name in not_found
        ]
        width = max(len(line) for line in warning_lines) + _PADDING
        print()
        print(_hline(_DOUBLE, width))
        print("Test Summary".center(width))
        print(_hline(_DOUBLE, width))
        for line in warning_lines:
            print(line)
        print(_hline(_DOUBLE, width))
        print()
        return 2

    # Print warnings for missing suites, then the table
    for name in not_found:
        print(f"  ⚠ {name}: results file not found — NOT RUN or output missing")

    _render_summary(found)

    # Exit code: 1 if any failures
    has_failures = any(not r.ok for r in found)
    return 1 if has_failures else 0


if __name__ == "__main__":
    sys.exit(main())
