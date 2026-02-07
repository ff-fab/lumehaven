#!/usr/bin/env python3
"""Validate module-level coverage thresholds based on ADR-006 risk levels.

Coverage.py doesn't support per-module thresholds natively. This script reads
the coverage JSON report, aggregates file-level data into logical modules, and
enforces risk-based targets from our test strategy.

Additionally, this script can synchronise Codecov component definitions in
``codecov.yml`` with ``MODULE_THRESHOLDS`` from ``coverage_config.py``.  This
keeps Codecov PR comments and the local enforcement script aligned on the same
module boundaries.

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

    # Sync codecov.yml components from coverage_config.py (local dev)
    python tests/scripts/check_coverage_thresholds.py --sync-codecov

    # Validate codecov.yml components are in sync (CI — fails if out of date)
    python tests/scripts/check_coverage_thresholds.py --sync-codecov --check

Exit codes:
    0 - All thresholds met / components in sync
    1 - One or more thresholds violated / components out of sync
    2 - Coverage file not found or invalid
"""

from __future__ import annotations

import argparse
import json
import re
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


# =============================================================================
# Codecov Component Sync
# =============================================================================

# Marker comments delimiting the auto-generated section in codecov.yml.
# Everything between these markers is replaced on sync; content outside is
# preserved (hand-written coverage targets, comment settings, etc.).
_BEGIN_MARKER = "# BEGIN GENERATED COMPONENTS — do not edit manually."
_END_MARKER = "# END GENERATED COMPONENTS"

# Base path prefix for all backend source files in the monorepo.
_BACKEND_SRC = "packages/backend/src/lumehaven"


def _module_key_to_component(
    key: str, line_thresh: int, branch_thresh: int
) -> dict[str, str | list[str]]:
    """Convert a MODULE_THRESHOLDS key to a Codecov component definition.

    The mapping rules mirror ``get_module_for_file`` in coverage_config.py:

    * ``__root__``   → root-level ``*.py`` files (``__init__.py``, ``_version.py``, …)
    * ``adapters/*`` → any adapter implementation subdirectory
    * ``adapters``   → direct files in ``adapters/`` (framework code)
    * ``config``     → single-file module ``config.py``
    * ``state``      → directory module ``state/``
    """
    if key == "__root__":
        return {
            "component_id": "be-root",
            "name": "Backend: Root",
            # Regex: files directly in lumehaven/ (not in subdirs)
            "paths": [rf"^{_BACKEND_SRC}/[^/]+\.py$"],
        }

    if key.endswith("/*"):
        parent = key[:-2]  # "adapters/*" → "adapters"
        return {
            "component_id": f"be-{parent}-impl",
            "name": f"Backend: {parent.title()} (implementations)",
            # Regex: any file in a subdirectory of parent
            "paths": [rf"^{_BACKEND_SRC}/{parent}/[^/]+/.+"],
        }

    # Directory or single-file module — Codecov will ignore non-matching paths
    return {
        "component_id": f"be-{key}",
        "name": f"Backend: {key.title()}",
        "paths": [f"{_BACKEND_SRC}/{key}/", f"{_BACKEND_SRC}/{key}.py"],
    }


def _generate_components_block() -> str:
    """Generate the YAML block for codecov.yml component_management.

    Reads MODULE_THRESHOLDS from coverage_config.py and produces a
    component_management section with ``target: auto`` (no regression from
    current level). Absolute thresholds remain in coverage_config.py — single
    source of truth.
    """
    from coverage_config import MODULE_THRESHOLDS

    lines = [
        _BEGIN_MARKER,
        f"# Source: {Path(__file__).name} ← coverage_config.MODULE_THRESHOLDS",
        "# Run:    task sync:codecov",
        "component_management:",
        "  default_rules:",
        "    statuses:",
        "      - type: project",
        "        target: auto # No regression — absolute thresholds enforced by script",
        "  individual_components:",
    ]

    for key, (line_thresh, branch_thresh) in MODULE_THRESHOLDS.items():
        comp = _module_key_to_component(key, line_thresh, branch_thresh)
        lines.append(f"    - component_id: {comp['component_id']}")
        lines.append(f"      name: '{comp['name']}'")
        lines.append("      paths:")
        for path in comp["paths"]:
            # Always use single quotes — Prettier normalises YAML strings
            # to single quotes, so we match that style for idempotency.
            lines.append(f"        - '{path}'")

    lines.append(_END_MARKER)
    return "\n".join(lines)


def _find_codecov_yml() -> Path:
    """Locate codecov.yml at the repository root.

    Walks up from the script's location to find the repo root (where .git is),
    then expects codecov.yml there.
    """
    current = Path(__file__).resolve().parent
    for parent in [current, *current.parents]:
        if (parent / ".git").exists():
            return parent / "codecov.yml"
    # Fallback: assume CWD-based structure
    return Path("codecov.yml")


def sync_codecov_components(*, check_only: bool = False) -> int:
    """Sync or validate Codecov component definitions in codecov.yml.

    Args:
        check_only: If True, only validate (don't write). Returns 1 if
            codecov.yml is out of date.

    Returns:
        0 if in sync (or updated), 1 if out of sync (check_only mode).
    """
    codecov_path = _find_codecov_yml()

    if not codecov_path.exists():
        print(f"Error: {codecov_path} not found", file=sys.stderr)
        return 2

    current_content = codecov_path.read_text()
    new_block = _generate_components_block()

    # Check if markers exist
    has_markers = _BEGIN_MARKER in current_content and _END_MARKER in current_content

    if has_markers:
        # Replace content between markers (inclusive)
        pattern = re.compile(
            re.escape(_BEGIN_MARKER) + r".*?" + re.escape(_END_MARKER),
            re.DOTALL,
        )
        updated_content = pattern.sub(new_block, current_content)
    else:
        # First time: append the block at the end
        separator = "\n" if current_content.endswith("\n") else "\n\n"
        updated_content = (
            current_content.rstrip("\n") + separator + "\n" + new_block + "\n"
        )

    if updated_content == current_content:
        print("✓ codecov.yml components are in sync with coverage_config.py")
        return 0

    if check_only:
        print(
            "✗ codecov.yml components are OUT OF SYNC with coverage_config.py",
            file=sys.stderr,
        )
        print("  Run 'task sync:codecov' to update.", file=sys.stderr)
        return 1

    codecov_path.write_text(updated_content)
    print(f"✓ Updated {codecov_path} components from coverage_config.py")
    return 0


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
    parser.add_argument(
        "--sync-codecov",
        action="store_true",
        help="Sync codecov.yml components from coverage_config.py",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="With --sync-codecov: validate only, fail if out of sync (for CI)",
    )

    args = parser.parse_args()

    # Codecov sync mode — independent of coverage data
    if args.sync_codecov:
        return sync_codecov_components(check_only=args.check)

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
