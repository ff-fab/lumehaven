#!/usr/bin/env python3
"""Print a unified summary of pytest (unit) and Robot Framework (integration) results.

Reads machine-readable output from both test runners and prints a combined
pass/fail table. Designed to run after both suites complete (even if one failed),
giving developers a single glance at the full picture.

pytest results come from JUnit XML (--junitxml flag).
Robot Framework results come from output.xml (default Robot output).

Optionally includes module-level coverage threshold validation when
``--coverage-file`` is provided. Without it, the script produces a
test-only summary (backward compatible).

Usage:
    # Test summary only (backward compatible):
    python tests/scripts/summarize_tests.py

    # Combined test + coverage summary:
    python tests/scripts/summarize_tests.py --coverage-file=coverage.json

    # With custom paths:
    python tests/scripts/summarize_tests.py \
        --unit-results results-unit.xml \
        --robot-output output.xml \
        --coverage-file coverage.json

Exit codes:
    0 - All tests passed (or skipped) and coverage thresholds met
    1 - Test failures/errors, missing suites, or coverage violations
    2 - Neither results file was found / coverage file missing
"""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

# Add tests/ and tests/scripts/ to path so sibling modules can be imported
# when running as a script.  tests/ holds coverage_config.py, while
# tests/scripts/ holds check_coverage_thresholds.py (neither directory is a
# proper Python package — they lack __init__.py on purpose).
_scripts_dir = str(Path(__file__).resolve().parent)
_tests_dir = str(Path(__file__).resolve().parent.parent)
sys.path.insert(0, _tests_dir)
sys.path.insert(0, _scripts_dir)

if TYPE_CHECKING:
    from check_coverage_thresholds import ThresholdViolation

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
# Coverage Integration
# =============================================================================


@dataclass
class CoverageResult:
    """Compact coverage threshold check result for embedding in the summary."""

    module_count: int
    violations: list[ThresholdViolation]

    @property
    def ok(self) -> bool:
        return len(self.violations) == 0


def check_coverage(coverage_file: Path) -> CoverageResult | None:
    """Run coverage threshold validation and return a compact result.

    Returns ``None`` if the coverage file doesn't exist or can't be parsed.
    Imports the coverage threshold script as a library to reuse its logic.
    """
    if not coverage_file.exists():
        print(
            f"  ⚠ Coverage file not found: {coverage_file}",
            file=sys.stderr,
        )
        return None

    # Late import — only needed when --coverage-file is provided
    from check_coverage_thresholds import (  # noqa: PLC0415
        check_thresholds,
        extract_module_coverage,
        load_coverage_data,
    )

    try:
        data = load_coverage_data(coverage_file)
    except SystemExit:
        # load_coverage_data calls sys.exit(2) on invalid JSON;
        # convert to None so the summary can report the failure gracefully.
        return None

    modules = extract_module_coverage(data)
    violations = check_thresholds(modules)
    return CoverageResult(module_count=len(modules), violations=violations)


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


def _render_summary(
    results: list[SuiteResult],
    coverage: CoverageResult | None = None,
) -> None:
    """Print a compact summary table to stdout.

    When *coverage* is provided, a coverage threshold line is appended after
    the totals row.  On violations the failing modules are listed inline.
    """
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

    # -- Coverage line (compact) ---------------------------------------------
    coverage_lines: list[str] = []
    if coverage is not None:
        if coverage.ok:
            coverage_lines.append(
                f"  Coverage: {coverage.module_count} modules, all thresholds met ✓"
            )
        else:
            n = len(coverage.violations)
            coverage_lines.append(
                f"  Coverage: {coverage.module_count} modules, {n} violation(s) ✗"
            )
            for v in coverage.violations:
                coverage_lines.append(
                    f"    {v.module}: {v.metric} {v.actual:.1f}% < {v.required}%"
                )

    # -- Result line ---------------------------------------------------------
    tests_ok = total_failed == 0
    coverage_ok = coverage is None or coverage.ok
    all_ok = tests_ok and coverage_ok

    if all_ok:
        result_line = "  Result: ALL PASSED ✓"
        result_colored = f"  Result: {_GREEN}ALL PASSED ✓{_RESET}"
    else:
        parts: list[str] = []
        if not tests_ok:
            parts.append(f"{total_failed} test failure(s)")
        if not coverage_ok:
            assert coverage is not None  # for type narrowing
            parts.append(f"{len(coverage.violations)} coverage violation(s)")
        detail = ", ".join(parts)
        result_line = f"  Result: FAILED ✗ — {detail}"
        result_colored = f"  Result: {_RED}FAILED ✗ — {detail}{_RESET}"

    # Width = widest content line + padding for visual breathing room
    # Use plain text (no ANSI codes) for width calculation
    all_lines = [header, totals_row, result_line, *data_rows, *coverage_lines]
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
    if coverage_lines:
        for line in coverage_lines:
            print(line)
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
    parser.add_argument(
        "--coverage-file",
        type=Path,
        default=None,
        help="Path to coverage JSON file. When provided, module-level "
        "threshold validation is included in the summary.",
    )
    parser.add_argument(
        "--unit-only",
        action="store_true",
        help="Only check unit test results; skip Robot Framework. "
        "Useful in CI where integration tests run as a separate job.",
    )
    return parser


def main() -> int:
    """Entry point. Returns the process exit code."""
    args = _build_parser().parse_args()

    unit_result = parse_junit_xml(args.unit_results)
    robot_result = None if args.unit_only else parse_robot_output(args.robot_output)

    found: list[SuiteResult] = []
    not_found: list[str] = []

    if unit_result is not None:
        found.append(unit_result)
    else:
        not_found.append("Unit (pytest)")

    if args.unit_only:
        pass  # Robot not expected — skip
    elif robot_result is not None:
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

    # Optional coverage threshold check
    coverage_result: CoverageResult | None = None
    if args.coverage_file is not None:
        coverage_result = check_coverage(args.coverage_file)
        if coverage_result is None:
            # Coverage file was explicitly requested but couldn't be loaded
            # (missing or corrupt).  Fail hard so CI doesn't silently skip.
            print(
                "  ✗ Cannot validate coverage — file missing or corrupt",
                file=sys.stderr,
            )
            _render_summary(found)
            return 2

    _render_summary(found, coverage=coverage_result)

    # Exit code: 1 if any failures, missing suites, or coverage violations
    has_failures = any(not r.ok for r in found)
    has_missing = len(not_found) > 0
    has_coverage_violations = coverage_result is not None and not coverage_result.ok
    return 1 if (has_failures or has_missing or has_coverage_violations) else 0


if __name__ == "__main__":
    sys.exit(main())
