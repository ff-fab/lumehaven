"""Unit tests for tests/scripts/summarize_tests.py — unified test summary.

Test Techniques Used:
- Specification-based Testing: Verifying CLI, rendering, and exit code contracts
- Equivalence Partitioning: No coverage / coverage OK / coverage violations
- Boundary Value Analysis: Zero violations vs. one vs. many
- Branch Coverage: Result line logic (tests ok + cov ok, tests fail, cov fail, both)
"""

from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from tests.scripts.summarize_tests import (
    CoverageResult,
    SuiteResult,
    _render_summary,
    check_coverage,
    main,
)

# =============================================================================
# Helpers
# =============================================================================


def _make_suite(
    name: str = "Unit (pytest)",
    passed: int = 10,
    failed: int = 0,
    errors: int = 0,
    skipped: int = 0,
) -> SuiteResult:
    return SuiteResult(
        name=name, passed=passed, failed=failed, errors=errors, skipped=skipped
    )


@dataclass
class FakeViolation:
    """Minimal stand-in for ThresholdViolation used in CoverageResult."""

    module: str
    metric: str
    actual: float
    required: float


# =============================================================================
# CoverageResult
# =============================================================================


class TestCoverageResult:
    """Tests for the CoverageResult dataclass.

    Technique: Specification-based Testing — verifying the ok property contract.
    """

    def test_ok_when_no_violations(self) -> None:
        """ok is True when violations list is empty."""
        result = CoverageResult(module_count=7, violations=[])
        assert result.ok is True

    def test_not_ok_when_violations_exist(self) -> None:
        """ok is False when violations list is non-empty."""
        v = FakeViolation(module="api", metric="line", actual=70.0, required=80.0)
        result = CoverageResult(module_count=7, violations=[v])  # type: ignore[arg-type]
        assert result.ok is False


# =============================================================================
# check_coverage
# =============================================================================


class TestCheckCoverage:
    """Tests for the check_coverage() integration function.

    Technique: Specification-based Testing — file-not-found and valid-file paths.
    """

    def test_returns_none_when_file_missing(self, tmp_path: Path) -> None:
        """Returns None when coverage file doesn't exist."""
        result = check_coverage(tmp_path / "nonexistent.json")
        assert result is None

    def test_returns_coverage_result_for_valid_file(self, tmp_path: Path) -> None:
        """Returns a CoverageResult when coverage data is valid."""
        # Minimal coverage.json with one file in the "core" module
        coverage_json = tmp_path / "coverage.json"
        coverage_json.write_text(
            '{"files": {"src/lumehaven/core/signal.py": '
            '{"summary": {"num_statements": 20, "covered_lines": 20, '
            '"num_branches": 4, "covered_branches": 4}}}}'
        )
        result = check_coverage(coverage_json)
        assert result is not None
        assert result.module_count >= 1
        assert result.ok is True


# =============================================================================
# _render_summary — coverage integration
# =============================================================================


class TestRenderSummaryWithCoverage:
    """Tests for _render_summary coverage integration.

    Technique: Branch Coverage — all combinations of test/coverage pass/fail.
    """

    def _capture_render(
        self,
        results: list[SuiteResult],
        coverage: CoverageResult | None = None,
    ) -> str:
        """Capture stdout from _render_summary."""
        buf = StringIO()
        with patch("sys.stdout", buf):
            _render_summary(results, coverage=coverage)
        return buf.getvalue()

    def test_no_coverage_shows_tests_only(self) -> None:
        """Without coverage, behaves like the original (backward compatible)."""
        output = self._capture_render([_make_suite()])
        assert "Coverage:" not in output
        assert "ALL PASSED" in output

    def test_coverage_ok_shows_compact_line(self) -> None:
        """With passing coverage, shows one-line summary."""
        cov = CoverageResult(module_count=7, violations=[])
        output = self._capture_render([_make_suite()], coverage=cov)
        assert "7 modules, all thresholds met ✓" in output
        assert "ALL PASSED" in output

    def test_coverage_violation_shows_details(self) -> None:
        """With coverage violation, expands to show failing modules."""
        v = FakeViolation(module="api", metric="line", actual=70.5, required=80.0)
        cov = CoverageResult(module_count=7, violations=[v])  # type: ignore[arg-type]
        output = self._capture_render([_make_suite()], coverage=cov)
        assert "7 modules, 1 violation(s) ✗" in output
        assert "api: line 70.5% < 80.0%" in output
        assert "FAILED" in output
        assert "1 coverage violation(s)" in output

    def test_both_failures_shows_combined_result(self) -> None:
        """Both test failures and coverage violations are reported together."""
        v = FakeViolation(module="state", metric="branch", actual=60.0, required=80.0)
        cov = CoverageResult(module_count=7, violations=[v])  # type: ignore[arg-type]
        suite = _make_suite(failed=2)
        output = self._capture_render([suite], coverage=cov)
        assert "2 test failure(s)" in output
        assert "1 coverage violation(s)" in output

    def test_test_failure_only_no_coverage_mention(self) -> None:
        """Test failures without coverage don't mention coverage."""
        suite = _make_suite(failed=3)
        output = self._capture_render([suite])
        assert "3 test failure(s)" in output
        assert "coverage" not in output.lower().replace("coverage:", "")


# =============================================================================
# main() exit codes
# =============================================================================


class TestMainExitCodes:
    """Tests for main() exit code integration with coverage.

    Technique: Equivalence Partitioning — exit code classes.
    """

    def test_exit_0_when_tests_pass_without_coverage(self, tmp_path: Path) -> None:
        """Exit 0 when tests pass and no coverage file is specified."""
        junit = tmp_path / "results-unit.xml"
        junit.write_text('<testsuite tests="5" failures="0" errors="0" skipped="0"/>')
        with patch(
            "sys.argv",
            ["prog", "--unit-results", str(junit), "--robot-output", "nonexistent"],
        ):
            # Only unit results found; robot missing → exit 1
            # So test with robot too
            pass

        # Simpler: just unit, no robot → warns but has results → exit 1 (missing suite)
        # Instead, provide both
        robot_xml = tmp_path / "output.xml"
        robot_xml.write_text(
            "<robot><statistics><total>"
            '<stat pass="3" fail="0" skip="0">All Tests</stat>'
            "</total></statistics></robot>"
        )
        with patch(
            "sys.argv",
            [
                "prog",
                "--unit-results",
                str(junit),
                "--robot-output",
                str(robot_xml),
            ],
        ):
            assert main() == 0

    def test_exit_1_when_coverage_violations(self, tmp_path: Path) -> None:
        """Exit 1 when tests pass but coverage thresholds violated."""
        junit = tmp_path / "results-unit.xml"
        junit.write_text('<testsuite tests="5" failures="0" errors="0" skipped="0"/>')
        robot_xml = tmp_path / "output.xml"
        robot_xml.write_text(
            "<robot><statistics><total>"
            '<stat pass="3" fail="0" skip="0">All Tests</stat>'
            "</total></statistics></robot>"
        )
        # Coverage file with 0% coverage → guaranteed violations
        cov_file = tmp_path / "coverage.json"
        cov_file.write_text(
            '{"files": {"src/lumehaven/api/routes.py": '
            '{"summary": {"num_statements": 100, "covered_lines": 0, '
            '"num_branches": 20, "covered_branches": 0}}}}'
        )
        with patch(
            "sys.argv",
            [
                "prog",
                "--unit-results",
                str(junit),
                "--robot-output",
                str(robot_xml),
                "--coverage-file",
                str(cov_file),
            ],
        ):
            assert main() == 1

    def test_exit_0_when_coverage_passes(self, tmp_path: Path) -> None:
        """Exit 0 when tests and coverage both pass."""
        junit = tmp_path / "results-unit.xml"
        junit.write_text('<testsuite tests="5" failures="0" errors="0" skipped="0"/>')
        robot_xml = tmp_path / "output.xml"
        robot_xml.write_text(
            "<robot><statistics><total>"
            '<stat pass="3" fail="0" skip="0">All Tests</stat>'
            "</total></statistics></robot>"
        )
        # Coverage file with 100% coverage → all thresholds met
        cov_file = tmp_path / "coverage.json"
        cov_file.write_text(
            '{"files": {"src/lumehaven/core/signal.py": '
            '{"summary": {"num_statements": 20, "covered_lines": 20, '
            '"num_branches": 4, "covered_branches": 4}}}}'
        )
        with patch(
            "sys.argv",
            [
                "prog",
                "--unit-results",
                str(junit),
                "--robot-output",
                str(robot_xml),
                "--coverage-file",
                str(cov_file),
            ],
        ):
            assert main() == 0
