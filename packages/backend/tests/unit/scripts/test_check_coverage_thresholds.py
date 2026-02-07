"""Unit tests for tests/scripts/check_coverage_thresholds.py — coverage validation CLI.

Test Techniques Used:
- Specification-based Testing: Verifying ModuleCoverage properties, threshold checks
- Equivalence Partitioning: Passing/failing modules, verbose/quiet modes, exit codes
- Boundary Value Analysis: Zero lines/branches, rates exactly at threshold
- Error Guessing: Missing/invalid coverage files, empty module list
- Branch Coverage: All format_report branches (verbose, violations, passed)
"""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from tests.coverage_config import get_threshold as _get_threshold
from tests.scripts.check_coverage_thresholds import (
    _BEGIN_MARKER,
    _END_MARKER,
    ModuleCoverage,
    ThresholdViolation,
    _generate_components_block,
    _module_key_to_component,
    check_thresholds,
    extract_module_coverage,
    format_report,
    load_coverage_data,
    main,
    sync_codecov_components,
)

# =============================================================================
# Helpers
# =============================================================================


def _make_module(
    name: str,
    total_lines: int = 100,
    covered_lines: int = 90,
    total_branches: int = 50,
    covered_branches: int = 40,
    files: list[str] | None = None,
) -> ModuleCoverage:
    """Factory for ModuleCoverage with sensible defaults."""
    return ModuleCoverage(
        name=name,
        total_lines=total_lines,
        covered_lines=covered_lines,
        total_branches=total_branches,
        covered_branches=covered_branches,
        files=files or [f"{name}/module.py"],
    )


def _write_coverage_json(path: Path, data: dict) -> None:
    """Write coverage data as JSON to a file."""
    path.write_text(json.dumps(data))


# =============================================================================
# ModuleCoverage properties
# =============================================================================


class TestModuleCoverageProperties:
    """Tests for ModuleCoverage.line_rate and .branch_rate computed properties.

    Technique: Boundary Value Analysis — zero-division edge cases, normal calculation.
    """

    def test_line_rate_normal(self) -> None:
        """Normal line rate calculation: covered/total * 100."""
        mod = _make_module("api", total_lines=200, covered_lines=170)
        assert mod.line_rate == 85.0

    def test_line_rate_zero_lines_returns_100(self) -> None:
        """Module with no statements gets 100% — nothing to miss."""
        mod = _make_module("empty", total_lines=0, covered_lines=0)
        assert mod.line_rate == 100.0

    def test_branch_rate_normal(self) -> None:
        """Normal branch rate calculation."""
        mod = _make_module("core", total_branches=80, covered_branches=60)
        assert mod.branch_rate == 75.0

    def test_branch_rate_zero_branches_returns_100(self) -> None:
        """Module with no branches gets 100% — nothing to miss."""
        mod = _make_module("simple", total_branches=0, covered_branches=0)
        assert mod.branch_rate == 100.0

    def test_line_rate_full_coverage(self) -> None:
        """100% line coverage."""
        mod = _make_module("perfect", total_lines=50, covered_lines=50)
        assert mod.line_rate == 100.0

    def test_branch_rate_no_coverage(self) -> None:
        """0% branch coverage."""
        mod = _make_module("bad", total_branches=100, covered_branches=0)
        assert mod.branch_rate == 0.0


# =============================================================================
# load_coverage_data
# =============================================================================


class TestLoadCoverageData:
    """Tests for load_coverage_data() — file loading with error handling.

    Technique: Error Guessing — missing files, invalid JSON.
    """

    def test_loads_valid_json(self, tmp_path: Path) -> None:
        """Valid JSON file loads successfully."""
        data = {"files": {}, "totals": {}}
        path = tmp_path / "coverage.json"
        _write_coverage_json(path, data)

        result = load_coverage_data(path)
        assert result == data

    def test_missing_file_exits_with_code_2(self, tmp_path: Path) -> None:
        """Missing coverage file triggers sys.exit(2)."""
        path = tmp_path / "nonexistent.json"
        with pytest.raises(SystemExit, match="2"):
            load_coverage_data(path)

    def test_invalid_json_exits_with_code_2(self, tmp_path: Path) -> None:
        """Malformed JSON triggers sys.exit(2)."""
        path = tmp_path / "bad.json"
        path.write_text("{not valid json")
        with pytest.raises(SystemExit, match="2"):
            load_coverage_data(path)


# =============================================================================
# extract_module_coverage
# =============================================================================


class TestExtractModuleCoverage:
    """Tests for extract_module_coverage() — file-to-module aggregation.

    Technique: Specification-based Testing — verifying aggregation logic.
    """

    def test_single_file_single_module(self) -> None:
        """One file maps to one module."""
        data = {
            "files": {
                "src/lumehaven/api/routes.py": {
                    "summary": {
                        "num_statements": 50,
                        "covered_lines": 45,
                        "num_branches": 20,
                        "covered_branches": 18,
                    }
                }
            }
        }
        modules = extract_module_coverage(data)
        assert len(modules) == 1
        assert modules[0].name == "api"
        assert modules[0].total_lines == 50
        assert modules[0].covered_lines == 45

    def test_multiple_files_aggregate_into_module(self) -> None:
        """Files in the same directory aggregate into one module."""
        data = {
            "files": {
                "src/lumehaven/api/routes.py": {
                    "summary": {
                        "num_statements": 50,
                        "covered_lines": 45,
                        "num_branches": 10,
                        "covered_branches": 8,
                    }
                },
                "src/lumehaven/api/sse.py": {
                    "summary": {
                        "num_statements": 30,
                        "covered_lines": 25,
                        "num_branches": 10,
                        "covered_branches": 9,
                    }
                },
            }
        }
        modules = extract_module_coverage(data)
        assert len(modules) == 1
        api = modules[0]
        assert api.name == "api"
        assert api.total_lines == 80
        assert api.covered_lines == 70
        assert api.total_branches == 20
        assert api.covered_branches == 17

    def test_adapter_subdir_uses_wildcard_key(self) -> None:
        """Adapter implementation files map to 'adapters/*' module."""
        data = {
            "files": {
                "src/lumehaven/adapters/openhab/adapter.py": {
                    "summary": {
                        "num_statements": 100,
                        "covered_lines": 92,
                        "num_branches": 40,
                        "covered_branches": 35,
                    }
                }
            }
        }
        modules = extract_module_coverage(data)
        assert any(m.name == "adapters/*" for m in modules)

    def test_empty_files_returns_empty_list(self) -> None:
        """No files in coverage data → empty module list."""
        modules = extract_module_coverage({"files": {}})
        assert modules == []

    def test_modules_sorted_by_name(self) -> None:
        """Returned modules are sorted alphabetically."""
        data = {
            "files": {
                "src/lumehaven/state/store.py": {
                    "summary": {
                        "num_statements": 10,
                        "covered_lines": 10,
                        "num_branches": 0,
                        "covered_branches": 0,
                    }
                },
                "src/lumehaven/api/routes.py": {
                    "summary": {
                        "num_statements": 10,
                        "covered_lines": 10,
                        "num_branches": 0,
                        "covered_branches": 0,
                    }
                },
            }
        }
        modules = extract_module_coverage(data)
        names = [m.name for m in modules]
        assert names == sorted(names)


# =============================================================================
# check_thresholds
# =============================================================================


class TestCheckThresholds:
    """Tests for check_thresholds() — violation detection.

    Technique: Equivalence Partitioning — above threshold, below threshold, at boundary.
    """

    def test_no_violations_when_all_pass(self) -> None:
        """Modules meeting thresholds produce no violations."""
        line_t, branch_t = _get_threshold("api")
        modules = [
            _make_module(
                "api",
                total_lines=100,
                covered_lines=line_t,
                total_branches=100,
                covered_branches=branch_t,
            )
        ]
        violations = check_thresholds(modules)
        assert violations == []

    def test_line_violation(self) -> None:
        """Line rate below threshold produces a line violation."""
        line_t, branch_t = _get_threshold("api")
        modules = [
            _make_module(
                "api",
                total_lines=100,
                covered_lines=line_t - 1,
                total_branches=100,
                covered_branches=branch_t,
            )
        ]
        violations = check_thresholds(modules)
        line_violations = [v for v in violations if v.metric == "line"]
        assert len(line_violations) == 1
        assert line_violations[0].actual == line_t - 1
        assert line_violations[0].required == line_t

    def test_branch_violation(self) -> None:
        """Branch rate below threshold produces a branch violation."""
        line_t, branch_t = _get_threshold("api")
        modules = [
            _make_module(
                "api",
                total_lines=100,
                covered_lines=line_t,
                total_branches=100,
                covered_branches=branch_t - 1,
            )
        ]
        violations = check_thresholds(modules)
        branch_violations = [v for v in violations if v.metric == "branch"]
        assert len(branch_violations) == 1
        assert branch_violations[0].actual == branch_t - 1

    def test_both_violations_for_one_module(self) -> None:
        """Module can have both line AND branch violations."""
        # 0% is below any positive threshold
        modules = [
            _make_module(
                "api",
                total_lines=100,
                covered_lines=0,
                total_branches=100,
                covered_branches=0,
            )
        ]
        violations = check_thresholds(modules)
        assert len(violations) == 2

    def test_at_exact_threshold_passes(self) -> None:
        """Rate exactly at threshold is NOT a violation (>=)."""
        line_t, branch_t = _get_threshold("api")
        modules = [
            _make_module(
                "api",
                total_lines=100,
                covered_lines=line_t,
                total_branches=100,
                covered_branches=branch_t,
            )
        ]
        violations = check_thresholds(modules)
        assert violations == []


# =============================================================================
# format_report
# =============================================================================


class TestFormatReport:
    """Tests for format_report() — text output formatting.

    Technique: Branch Coverage — verbose vs non-verbose, violations vs passed.
    """

    def test_passed_non_verbose(self) -> None:
        """Non-verbose passed report contains PASSED message."""
        modules = [_make_module("api")]
        report = format_report(modules, [], verbose=False)
        assert "PASSED" in report
        assert "api" not in report  # Non-verbose doesn't list modules

    def test_passed_verbose(self) -> None:
        """Verbose passed report lists each module with check marks."""
        line_t, branch_t = _get_threshold("api")
        modules = [
            _make_module(
                "api",
                total_lines=100,
                covered_lines=line_t,
                total_branches=100,
                covered_branches=branch_t,
            )
        ]
        report = format_report(modules, [], verbose=True)
        assert "PASSED" in report
        assert "api" in report
        assert "✓" in report

    def test_failed_report_shows_violations(self) -> None:
        """Failed report shows violation details."""
        # ThresholdViolation is just display data — values are arbitrary
        violations = [
            ThresholdViolation(
                module="modX",
                metric="line",
                actual=50.0,
                required=80,
            ),
        ]
        report = format_report([], violations, verbose=False)
        assert "FAILED" in report
        assert "modX" in report
        assert "50.0%" in report

    def test_verbose_shows_failing_marks(self) -> None:
        """Verbose report shows ✗ for failing modules."""
        line_t, _branch_t = _get_threshold("api")
        mod = _make_module(
            "api",
            total_lines=100,
            covered_lines=0,
            total_branches=100,
            covered_branches=100,
        )
        violations = [
            ThresholdViolation(
                module="api",
                metric="line",
                actual=0.0,
                required=line_t,
            )
        ]
        report = format_report([mod], violations, verbose=True)
        assert "✗" in report


# =============================================================================
# main() CLI
# =============================================================================


class TestMain:
    """Tests for main() — CLI entry point and exit codes.

    Technique: Specification-based Testing — exit code 0, 1, 2 per docstring.
    """

    def test_exit_0_all_thresholds_met(self, tmp_path: Path) -> None:
        """Exit code 0 when all thresholds are met."""
        data = {
            "files": {
                "src/lumehaven/__init__.py": {
                    "summary": {
                        "num_statements": 10,
                        "covered_lines": 10,
                        "num_branches": 0,
                        "covered_branches": 0,
                    }
                }
            }
        }
        cov_file = tmp_path / "coverage.json"
        _write_coverage_json(cov_file, data)

        with patch("sys.argv", ["prog", "--coverage-file", str(cov_file)]):
            result = main()
        assert result == 0

    def test_exit_1_threshold_violated(self, tmp_path: Path) -> None:
        """Exit code 1 when a threshold is violated."""
        # 0% coverage guarantees violation for any positive threshold
        data = {
            "files": {
                "src/lumehaven/adapters/openhab/adapter.py": {
                    "summary": {
                        "num_statements": 100,
                        "covered_lines": 0,
                        "num_branches": 100,
                        "covered_branches": 0,
                    }
                }
            }
        }
        cov_file = tmp_path / "coverage.json"
        _write_coverage_json(cov_file, data)

        with patch("sys.argv", ["prog", "--coverage-file", str(cov_file)]):
            result = main()
        assert result == 1

    def test_exit_2_missing_file(self, tmp_path: Path) -> None:
        """Exit code 2 when coverage file doesn't exist."""
        missing = tmp_path / "nonexistent.json"
        with (
            patch("sys.argv", ["prog", "--coverage-file", str(missing)]),
            pytest.raises(SystemExit, match="2"),
        ):
            main()

    def test_exit_2_no_modules(self, tmp_path: Path) -> None:
        """Exit code 2 when coverage data has no modules."""
        cov_file = tmp_path / "coverage.json"
        _write_coverage_json(cov_file, {"files": {}})

        with patch("sys.argv", ["prog", "--coverage-file", str(cov_file)]):
            result = main()
        assert result == 2

    def test_verbose_flag(self, tmp_path: Path) -> None:
        """Verbose flag produces detailed output."""
        data = {
            "files": {
                "src/lumehaven/__init__.py": {
                    "summary": {
                        "num_statements": 10,
                        "covered_lines": 10,
                        "num_branches": 0,
                        "covered_branches": 0,
                    }
                }
            }
        }
        cov_file = tmp_path / "coverage.json"
        _write_coverage_json(cov_file, data)

        stdout = StringIO()
        with (
            patch("sys.argv", ["prog", "--coverage-file", str(cov_file), "-v"]),
            patch("sys.stdout", stdout),
        ):
            result = main()

        assert result == 0
        output = stdout.getvalue()
        assert "__root__" in output
        assert "✓" in output

    def test_quiet_flag_suppresses_passing_output(self, tmp_path: Path) -> None:
        """Quiet flag suppresses output when all thresholds pass."""
        data = {
            "files": {
                "src/lumehaven/__init__.py": {
                    "summary": {
                        "num_statements": 10,
                        "covered_lines": 10,
                        "num_branches": 0,
                        "covered_branches": 0,
                    }
                }
            }
        }
        cov_file = tmp_path / "coverage.json"
        _write_coverage_json(cov_file, data)

        stdout = StringIO()
        with (
            patch("sys.argv", ["prog", "--coverage-file", str(cov_file), "-q"]),
            patch("sys.stdout", stdout),
        ):
            result = main()

        assert result == 0
        assert stdout.getvalue() == ""


# =============================================================================
# Codecov Component Sync
# =============================================================================


class TestModuleKeyToComponent:
    """Tests for _module_key_to_component mapping logic.

    Technique: Equivalence Partitioning — four distinct key patterns:
    __root__, wildcard (*/), directory, and single-file module.
    """

    def test_root_key_produces_regex_for_root_files(self) -> None:
        """__root__ maps to a regex matching only top-level .py files."""
        comp = _module_key_to_component("__root__", 30, 0)
        assert comp["component_id"] == "be-root"
        assert any("[^/]+\\.py$" in p for p in comp["paths"])

    def test_wildcard_key_produces_subdir_regex(self) -> None:
        """adapters/* maps to regex matching adapter subdirectories."""
        comp = _module_key_to_component("adapters/*", 90, 85)
        assert comp["component_id"] == "be-adapters-impl"
        assert any("adapters/[^/]+/" in p for p in comp["paths"])

    def test_directory_module_produces_dir_and_file_paths(self) -> None:
        """Directory module (api) produces both dir/ and .py paths."""
        comp = _module_key_to_component("api", 80, 75)
        assert comp["component_id"] == "be-api"
        # Should have both a directory path and a .py path
        paths = comp["paths"]
        assert any(p.endswith("api/") for p in paths)
        assert any(p.endswith("api.py") for p in paths)

    def test_single_file_module_same_as_directory(self) -> None:
        """Single-file module (config) uses same pattern.

        Codecov ignores non-matching paths, so both dir/ and .py are safe.
        """
        comp = _module_key_to_component("config", 85, 80)
        assert comp["component_id"] == "be-config"
        assert any("config.py" in p for p in comp["paths"])

    def test_component_id_uses_be_prefix(self) -> None:
        """All backend components use 'be-' prefix for monorepo namespacing."""
        for key in ("core", "state", "api", "__root__", "adapters/*"):
            comp = _module_key_to_component(key, 80, 70)
            assert comp["component_id"].startswith("be-")

    def test_name_includes_backend_prefix(self) -> None:
        """Display names include 'Backend:' for clarity in Codecov UI."""
        comp = _module_key_to_component("core", 80, 70)
        assert comp["name"].startswith("Backend:")


class TestGenerateComponentsBlock:
    """Tests for _generate_components_block YAML generation.

    Technique: Specification-based — verify structural properties of the
    generated output that must hold regardless of MODULE_THRESHOLDS content.
    """

    def test_block_starts_with_begin_marker(self) -> None:
        """Generated block must start with the BEGIN marker."""
        block = _generate_components_block()
        assert block.startswith(_BEGIN_MARKER)

    def test_block_ends_with_end_marker(self) -> None:
        """Generated block must end with the END marker."""
        block = _generate_components_block()
        assert block.rstrip().endswith(_END_MARKER)

    def test_block_contains_component_management(self) -> None:
        """YAML must include the top-level component_management key."""
        block = _generate_components_block()
        assert "component_management:" in block

    def test_block_uses_target_auto(self) -> None:
        """Default status uses target: auto (no regression, not hardcoded)."""
        block = _generate_components_block()
        assert "target: auto" in block

    def test_block_contains_all_module_keys(self) -> None:
        """Every MODULE_THRESHOLDS key should appear as a component."""
        from tests.coverage_config import MODULE_THRESHOLDS

        block = _generate_components_block()
        for key in MODULE_THRESHOLDS:
            comp = _module_key_to_component(key, *MODULE_THRESHOLDS[key])
            assert comp["component_id"] in block, (
                f"Component for {key!r} missing from generated block"
            )


class TestSyncCodecovComponents:
    """Tests for sync_codecov_components file I/O and sync logic.

    Technique: Equivalence Partitioning — three scenarios:
    1. File already in sync (no-op)
    2. File out of sync (update or fail)
    3. File without markers (first-time append)

    Uses tmp_path to avoid touching the real codecov.yml.
    """

    def _write_codecov(self, path: Path, content: str) -> None:
        path.write_text(content)

    def test_in_sync_returns_0(self, tmp_path: Path) -> None:
        """Returns 0 and doesn't modify file when already in sync."""
        block = _generate_components_block()
        content = f"coverage:\n  status: {{}}\n\n{block}\n"
        codecov_path = tmp_path / "codecov.yml"
        self._write_codecov(codecov_path, content)

        with patch(
            "tests.scripts.check_coverage_thresholds._find_codecov_yml",
            return_value=codecov_path,
        ):
            result = sync_codecov_components(check_only=False)

        assert result == 0
        assert codecov_path.read_text() == content  # Unchanged

    def test_check_only_in_sync_returns_0(self, tmp_path: Path) -> None:
        """Check mode returns 0 when in sync."""
        block = _generate_components_block()
        content = f"coverage:\n  status: {{}}\n\n{block}\n"
        codecov_path = tmp_path / "codecov.yml"
        self._write_codecov(codecov_path, content)

        with patch(
            "tests.scripts.check_coverage_thresholds._find_codecov_yml",
            return_value=codecov_path,
        ):
            result = sync_codecov_components(check_only=True)

        assert result == 0

    def test_out_of_sync_updates_file(self, tmp_path: Path) -> None:
        """Sync mode rewrites the markers section when out of date."""
        old_block = f"{_BEGIN_MARKER}\nold content\n{_END_MARKER}"
        content = f"# header\ncoverage:\n  status: {{}}\n\n{old_block}\n"
        codecov_path = tmp_path / "codecov.yml"
        self._write_codecov(codecov_path, content)

        with patch(
            "tests.scripts.check_coverage_thresholds._find_codecov_yml",
            return_value=codecov_path,
        ):
            result = sync_codecov_components(check_only=False)

        assert result == 0
        updated = codecov_path.read_text()
        assert _BEGIN_MARKER in updated
        assert _END_MARKER in updated
        assert "old content" not in updated
        assert "component_management:" in updated
        # Header preserved
        assert updated.startswith("# header")

    def test_check_only_out_of_sync_returns_1(self, tmp_path: Path) -> None:
        """Check mode returns 1 when out of sync, does NOT modify file."""
        old_block = f"{_BEGIN_MARKER}\nold content\n{_END_MARKER}"
        content = f"coverage:\n  status: {{}}\n\n{old_block}\n"
        codecov_path = tmp_path / "codecov.yml"
        self._write_codecov(codecov_path, content)

        with patch(
            "tests.scripts.check_coverage_thresholds._find_codecov_yml",
            return_value=codecov_path,
        ):
            result = sync_codecov_components(check_only=True)

        assert result == 1
        assert codecov_path.read_text() == content  # Unchanged

    def test_no_markers_appends_block(self, tmp_path: Path) -> None:
        """First-time sync appends markers and block to existing file."""
        content = "coverage:\n  status: {}\n"
        codecov_path = tmp_path / "codecov.yml"
        self._write_codecov(codecov_path, content)

        with patch(
            "tests.scripts.check_coverage_thresholds._find_codecov_yml",
            return_value=codecov_path,
        ):
            result = sync_codecov_components(check_only=False)

        assert result == 0
        updated = codecov_path.read_text()
        assert _BEGIN_MARKER in updated
        assert _END_MARKER in updated
        # Original content preserved at the top
        assert updated.startswith("coverage:")

    def test_missing_file_returns_2(self, tmp_path: Path) -> None:
        """Returns 2 when codecov.yml doesn't exist."""
        codecov_path = tmp_path / "nonexistent.yml"

        with patch(
            "tests.scripts.check_coverage_thresholds._find_codecov_yml",
            return_value=codecov_path,
        ):
            result = sync_codecov_components(check_only=False)

        assert result == 2


class TestMainSyncCodecov:
    """Tests for main() with --sync-codecov flag integration.

    Technique: Integration — verify CLI arg parsing routes to sync_codecov_components.
    """

    def test_sync_codecov_flag_calls_sync(self, tmp_path: Path) -> None:
        """--sync-codecov routes to sync_codecov_components."""
        block = _generate_components_block()
        content = f"coverage:\n  status: {{}}\n\n{block}\n"
        codecov_path = tmp_path / "codecov.yml"
        codecov_path.write_text(content)

        with (
            patch("sys.argv", ["prog", "--sync-codecov"]),
            patch(
                "tests.scripts.check_coverage_thresholds._find_codecov_yml",
                return_value=codecov_path,
            ),
        ):
            result = main()

        assert result == 0

    def test_sync_codecov_check_flag_fails_on_drift(self, tmp_path: Path) -> None:
        """--sync-codecov --check returns 1 when out of sync."""
        old_block = f"{_BEGIN_MARKER}\nstale\n{_END_MARKER}"
        codecov_path = tmp_path / "codecov.yml"
        codecov_path.write_text(f"header\n{old_block}\n")

        with (
            patch("sys.argv", ["prog", "--sync-codecov", "--check"]),
            patch(
                "tests.scripts.check_coverage_thresholds._find_codecov_yml",
                return_value=codecov_path,
            ),
        ):
            result = main()

        assert result == 1

    def test_check_without_sync_codecov_is_error(self) -> None:
        """--check alone (without --sync-codecov) raises a parser error."""
        with (
            patch("sys.argv", ["prog", "--check"]),
            pytest.raises(SystemExit, match="2"),
        ):
            main()
