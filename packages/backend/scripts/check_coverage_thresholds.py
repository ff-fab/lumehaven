#!/usr/bin/env python3
"""Validate per-module coverage thresholds based on ADR-006 risk levels.

Coverage.py doesn't support per-module thresholds natively. This script reads
the coverage JSON report and enforces risk-based targets from our test strategy.

Usage:
    # Generate JSON report first
    pytest --cov=lumehaven --cov-report=json

    # Then validate thresholds
    python scripts/check_coverage_thresholds.py

    # Or specify custom coverage file
    python scripts/check_coverage_thresholds.py --coverage-file=custom.json

Exit codes:
    0 - All thresholds met
    1 - One or more thresholds violated
    2 - Coverage file not found or invalid
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

# =============================================================================
# Risk-Based Thresholds (from docs/testing/03-coverage-strategy.md)
# =============================================================================
# Format: "module_path_pattern": (line_threshold, branch_threshold)
#
# Patterns are matched against the module path relative to src/lumehaven/
# More specific patterns take precedence over general ones.

THRESHOLDS: dict[str, tuple[int, int]] = {
    # Critical risk (90% line, 85% branch)
    "adapters/openhab/adapter.py": (90, 85),
    "adapters/manager.py": (90, 85),
    # High risk (85% line, 80% branch)
    "config.py": (85, 80),
    "state/store.py": (85, 80),
    # Medium risk (80% line, 75% branch)
    "api/routes.py": (80, 75),
    "api/sse.py": (80, 75),
    # Low risk / default (80% line, 70% branch)
    "__default__": (80, 70),
}


@dataclass
class ModuleCoverage:
    """Coverage data for a single module."""

    path: str
    line_rate: float
    branch_rate: float
    covered_lines: int
    total_lines: int
    covered_branches: int
    total_branches: int


@dataclass
class ThresholdViolation:
    """A threshold violation for reporting."""

    module: str
    metric: str  # "line" or "branch"
    actual: float
    required: float


def load_coverage_data(coverage_file: Path) -> dict[str, Any]:
    """Load and parse the coverage JSON file."""
    if not coverage_file.exists():
        print(f"Error: Coverage file not found: {coverage_file}", file=sys.stderr)
        print("Run 'pytest --cov --cov-report=json' first.", file=sys.stderr)
        sys.exit(2)

    try:
        with coverage_file.open() as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in coverage file: {e}", file=sys.stderr)
        sys.exit(2)


def extract_module_coverage(data: dict[str, Any]) -> list[ModuleCoverage]:
    """Extract per-module coverage from coverage.py JSON format."""
    modules = []

    files = data.get("files", {})
    for filepath, file_data in files.items():
        summary = file_data.get("summary", {})

        # Calculate rates as percentages
        total_lines = summary.get("num_statements", 0)
        covered_lines = summary.get("covered_lines", 0)
        line_rate = (covered_lines / total_lines * 100) if total_lines > 0 else 100.0

        total_branches = summary.get("num_branches", 0)
        covered_branches = summary.get("covered_branches", 0)
        branch_rate = (
            (covered_branches / total_branches * 100) if total_branches > 0 else 100.0
        )

        modules.append(
            ModuleCoverage(
                path=filepath,
                line_rate=line_rate,
                branch_rate=branch_rate,
                covered_lines=covered_lines,
                total_lines=total_lines,
                covered_branches=covered_branches,
                total_branches=total_branches,
            )
        )

    return modules


def get_threshold_for_module(module_path: str) -> tuple[int, int]:
    """Get the (line, branch) threshold for a module path.

    Matches against THRESHOLDS patterns. More specific matches win.
    Falls back to __default__ if no pattern matches.
    """
    # Normalize path: extract relative path from src/lumehaven/
    normalized = module_path
    if "src/lumehaven/" in normalized:
        normalized = normalized.split("src/lumehaven/")[-1]
    elif "lumehaven/" in normalized:
        normalized = normalized.split("lumehaven/")[-1]

    # Try exact match first
    if normalized in THRESHOLDS:
        return THRESHOLDS[normalized]

    # Try prefix matches (for directory-level thresholds)
    best_match = "__default__"
    best_match_len = 0

    for pattern in THRESHOLDS:
        if pattern == "__default__":
            continue
        # Check if pattern is a prefix (directory match)
        prefix = pattern.rstrip(".py").rstrip("/")
        if normalized.startswith(prefix) and len(pattern) > best_match_len:
            best_match = pattern
            best_match_len = len(pattern)

    return THRESHOLDS[best_match]


def check_thresholds(modules: list[ModuleCoverage]) -> list[ThresholdViolation]:
    """Check all modules against their thresholds."""
    violations = []

    for module in modules:
        line_threshold, branch_threshold = get_threshold_for_module(module.path)

        if module.line_rate < line_threshold:
            violations.append(
                ThresholdViolation(
                    module=module.path,
                    metric="line",
                    actual=module.line_rate,
                    required=line_threshold,
                )
            )

        if module.branch_rate < branch_threshold:
            violations.append(
                ThresholdViolation(
                    module=module.path,
                    metric="branch",
                    actual=module.branch_rate,
                    required=branch_threshold,
                )
            )

    return violations


def format_report(
    modules: list[ModuleCoverage],
    violations: list[ThresholdViolation],
    *,
    verbose: bool = False,
) -> str:
    """Format the coverage threshold report."""
    lines = []

    if verbose:
        lines.append("=" * 70)
        lines.append("Per-Module Coverage Thresholds Report")
        lines.append("=" * 70)
        lines.append("")

        for module in sorted(modules, key=lambda m: m.path):
            line_thresh, branch_thresh = get_threshold_for_module(module.path)
            line_ok = "✓" if module.line_rate >= line_thresh else "✗"
            branch_ok = "✓" if module.branch_rate >= branch_thresh else "✗"

            # Shorten path for display
            display_path = module.path
            if "src/lumehaven/" in display_path:
                display_path = display_path.split("src/lumehaven/")[-1]

            lines.append(f"{display_path}")
            lines.append(
                f"  Line:   {module.line_rate:5.1f}% (>={line_thresh}%) {line_ok}"
            )
            lines.append(
                f"  Branch: {module.branch_rate:5.1f}% (>={branch_thresh}%) {branch_ok}"
            )
            lines.append("")

    if violations:
        lines.append("-" * 70)
        lines.append(f"FAILED: {len(violations)} threshold violation(s)")
        lines.append("-" * 70)

        for v in violations:
            display_path = v.module
            if "src/lumehaven/" in display_path:
                display_path = display_path.split("src/lumehaven/")[-1]

            lines.append(
                f"  {display_path}: {v.metric} coverage {v.actual:.1f}% < {v.required}%"
            )
    else:
        lines.append("-" * 70)
        lines.append("PASSED: All coverage thresholds met")
        lines.append("-" * 70)

    return "\n".join(lines)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check per-module coverage against risk-based thresholds"
    )
    parser.add_argument(
        "--coverage-file",
        type=Path,
        default=Path("coverage.json"),
        help="Path to coverage JSON file (default: coverage.json)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show coverage for all modules, not just violations",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Only output on failure",
    )

    args = parser.parse_args()

    # Load coverage data
    data = load_coverage_data(args.coverage_file)

    # Extract module coverage
    modules = extract_module_coverage(data)

    if not modules:
        print("Warning: No modules found in coverage data", file=sys.stderr)
        return 0

    # Check thresholds
    violations = check_thresholds(modules)

    # Report
    if not args.quiet or violations:
        report = format_report(modules, violations, verbose=args.verbose)
        print(report)

    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
