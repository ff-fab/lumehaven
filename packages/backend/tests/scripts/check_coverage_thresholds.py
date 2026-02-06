#!/usr/bin/env python3
"""Validate module-level coverage thresholds based on ADR-006 risk levels.

Coverage.py doesn't support per-module thresholds natively. This script reads
the coverage JSON report, aggregates file-level data into logical modules, and
enforces risk-based targets from our test strategy.

Aggregation: files are grouped by directory module (e.g. ``api/``,
``adapters/*``). Coverage is computed as a weighted average — each file
contributes proportional to its statement/branch count.

Usage:
    # Generate JSON report first
    pytest --cov=lumehaven --cov-report=json

    # Then validate thresholds
    python tests/scripts/check_coverage_thresholds.py

    # Or specify custom coverage file
    python tests/scripts/check_coverage_thresholds.py --coverage-file=custom.json

Exit codes:
    0 - All thresholds met
    1 - One or more thresholds violated
    2 - Coverage file not found or invalid
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

# Add tests/ to path so coverage_config can be imported when running as script.
# parent.parent resolves tests/scripts/ → tests/ where coverage_config.py lives.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from coverage_config import (  # noqa: E402
    get_module_for_file,
    get_threshold,
    normalize_path,
)

if TYPE_CHECKING:
    from typing import Any


@dataclass
class ModuleCoverage:
    """Aggregated coverage data for a logical module (directory grouping)."""

    name: str
    total_lines: int = 0
    covered_lines: int = 0
    total_branches: int = 0
    covered_branches: int = 0
    files: list[str] = field(default_factory=list)

    @property
    def line_rate(self) -> float:
        if self.total_lines == 0:
            return 100.0
        return self.covered_lines / self.total_lines * 100

    @property
    def branch_rate(self) -> float:
        return (
            (self.covered_branches / self.total_branches * 100)
            if self.total_branches
            else 100.0
        )


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
    """Aggregate file-level coverage into logical modules."""
    modules: dict[str, ModuleCoverage] = {}

    for filepath, file_data in data.get("files", {}).items():
        summary = file_data.get("summary", {})
        normalized = normalize_path(filepath)
        module_name = get_module_for_file(normalized)

        if module_name not in modules:
            modules[module_name] = ModuleCoverage(name=module_name)

        mod = modules[module_name]
        mod.total_lines += summary.get("num_statements", 0)
        mod.covered_lines += summary.get("covered_lines", 0)
        mod.total_branches += summary.get("num_branches", 0)
        mod.covered_branches += summary.get("covered_branches", 0)
        mod.files.append(normalized)

    return sorted(modules.values(), key=lambda m: m.name)


def check_thresholds(modules: list[ModuleCoverage]) -> list[ThresholdViolation]:
    """Check all module aggregates against their thresholds."""
    violations = []

    for module in modules:
        line_threshold, branch_threshold = get_threshold(module.name)

        if module.line_rate < line_threshold:
            violations.append(
                ThresholdViolation(
                    module=module.name,
                    metric="line",
                    actual=module.line_rate,
                    required=line_threshold,
                )
            )

        if module.branch_rate < branch_threshold:
            violations.append(
                ThresholdViolation(
                    module=module.name,
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
    """Format the module-level coverage threshold report."""
    lines = []

    if verbose:
        lines.append("=" * 70)
        lines.append("Module-Level Coverage Thresholds Report")
        lines.append("=" * 70)
        lines.append("")

        for module in modules:
            line_thresh, branch_thresh = get_threshold(module.name)
            line_ok = "✓" if module.line_rate >= line_thresh else "✗"
            branch_ok = "✓" if module.branch_rate >= branch_thresh else "✗"

            lines.append(f"{module.name}  ({len(module.files)} files)")
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
            lines.append(
                f"  {v.module}: {v.metric} coverage {v.actual:.1f}% < {v.required}%"
            )
    else:
        lines.append("-" * 70)
        lines.append("PASSED: All module coverage thresholds met")
        lines.append("-" * 70)

    return "\n".join(lines)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check module-level coverage against risk-based thresholds"
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
        print("Error: No modules found in coverage data", file=sys.stderr)
        print("This usually means:", file=sys.stderr)
        print("  - Misconfigured --cov target", file=sys.stderr)
        print("  - No code was executed during tests", file=sys.stderr)
        print("  - Coverage source path doesn't match actual code", file=sys.stderr)
        return 2

    # Check thresholds
    violations = check_thresholds(modules)

    # Report
    if not args.quiet or violations:
        report = format_report(modules, violations, verbose=args.verbose)
        print(report)

    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
