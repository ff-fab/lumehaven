# Coverage Strategy

> **ISTQB Alignment:** This chapter defines coverage metrics, risk-based targets, and
> enforcement strategy. Based on risk-based testing principles from ISTQB Foundation.

## Metrics Overview

We track three categories of metrics:

| Category             | Metrics                       | Purpose                      | Enforcement                 |
| -------------------- | ----------------------------- | ---------------------------- | --------------------------- |
| **Test Coverage**    | Line, Branch                  | "Did we test this code?"     | Enforced from start         |
| **Code Complexity**  | Cyclomatic (radon), Cognitive | "How testable is this code?" | Enforced in pre-commit + CI |
| **Quality Platform** | SonarQube (future)            | Unified quality dashboard    | Planned for later           |

---

## Test Coverage Metrics

### Line Coverage (Primary)

**What it measures:** Percentage of executable statements exercised by tests.

**Why primary:** Industry standard. CPython, FastAPI, requests all track line coverage.
Simple to understand: "80% of lines were executed during tests."

**Tool:** `pytest-cov` (coverage.py wrapper)

```bash
uv run pytest --cov=lumehaven --cov-report=term-missing
```

### Branch Coverage (Secondary)

**What it measures:** Percentage of decision branches (both true/false paths) exercised.

**Why important:** Line coverage can miss untested branches:

```python
def process(value: str | None) -> str:
    if value:           # Branch: True path
        return value    # ← Line covered if value is truthy
    return "default"    # ← Line covered if value is falsy
```

With only `process("hello")`, line coverage is 66% (2/3 lines), but branch coverage
reveals we never tested the falsy path.

**Tool:** `pytest-cov` with `--cov-branch`

```bash
uv run pytest --cov=lumehaven --cov-branch --cov-report=term-missing
```

---

## Complexity Metrics

### Cyclomatic Complexity (radon)

**What it measures:** Number of independent paths through code. Higher = more test cases
needed for full coverage.

| Grade | CC Range | Interpretation                        |
| ----- | -------- | ------------------------------------- |
| A     | 1-5      | Simple, low risk                      |
| B     | 6-10     | Moderate complexity                   |
| C     | 11-15    | Complex, consider refactoring         |
| D     | 16-20    | High complexity, refactor recommended |
| E/F   | 21+      | Very high risk, refactor required     |

**Tool:** radon + xenon

```bash
# Report complexity
uv run radon cc src/lumehaven --average --show-complexity

# Enforce thresholds (xenon)
uv run xenon --max-absolute C --max-modules B --max-average B src/lumehaven
```

### Cognitive Complexity

**What it measures:** How hard code is for humans to understand. Weights nested
structures and control flow breaks higher than cyclomatic complexity.

**Why both?** Cyclomatic is mathematical (paths), cognitive matches human perception. A
deeply nested `if` scores higher cognitively even with same cyclomatic score.

**Tool:** flake8-cognitive-complexity

```bash
# Via flake8
uv run flake8 --max-cognitive-complexity=15 src/lumehaven
```

### Complexity → Testing Relationship

High complexity indicates where to focus testing effort:

```
┌─────────────────────────────────────────────────────────────────┐
│                    COMPLEXITY GUIDES TESTING                    │
│                                                                 │
│   High CC (>10)              │   Low CC (<5)                    │
│   ─────────────              │   ──────────                     │
│   • More test cases needed   │   • Fewer test cases sufficient  │
│   • Higher branch coverage   │   • Line coverage adequate       │
│   • Consider refactoring     │   • Low risk                     │
│   • Priority for review      │   • Standard review              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Risk-Based Coverage Targets

### Risk Classification

Components are classified by combining:

1. **Business criticality** — Impact on users if broken
2. **Defect likelihood** — Complexity, change frequency, external dependencies

| Risk Level   | Business Impact          | Defect Likelihood              | Examples                           |
| ------------ | ------------------------ | ------------------------------ | ---------------------------------- |
| **Critical** | Core functionality fails | High complexity, external APIs | `OpenHABAdapter`, `AdapterManager` |
| **High**     | Major feature degraded   | Medium complexity              | `config.py`, `SignalStore`         |
| **Medium**   | Minor inconvenience      | Low-medium complexity          | API routes, SSE streaming          |
| **Low**      | Cosmetic/dev-only        | Simple code                    | Models, utilities                  |

### Coverage Targets by Risk Level

| Risk Level   | Line Coverage | Branch Coverage | Complexity Gate   |
| ------------ | ------------- | --------------- | ----------------- |
| **Critical** | ≥ 90%         | ≥ 85%           | CC ≤ 10 (grade B) |
| **High**     | ≥ 85%         | ≥ 80%           | CC ≤ 15 (grade C) |
| **Medium**   | ≥ 80%         | ≥ 75%           | CC ≤ 15 (grade C) |
| **Low**      | ≥ 80%         | ≥ 70%           | CC ≤ 20 (grade D) |

**Minimum floor:** 80% line coverage for all components regardless of risk level.

### Component Risk Assignment

| Component                     | Risk Level   | Line Target | Branch Target | Rationale                         |
| ----------------------------- | ------------ | ----------- | ------------- | --------------------------------- |
| `adapters/openhab/adapter.py` | **Critical** | 90%         | 85%           | Core data source, complex parsing |
| `adapters/manager.py`         | **Critical** | 90%         | 85%           | Lifecycle state machine           |
| `config.py`                   | **High**     | 85%         | 80%           | Startup failure = app unusable    |
| `state/store.py`              | **High**     | 85%         | 80%           | All data flows through here       |
| `core/signal.py`              | **Low**      | 80%         | 70%           | Simple dataclass                  |
| `api/routes.py`               | **Medium**   | 80%         | 75%           | Thin layer, delegates to store    |
| `api/sse.py`                  | **Medium**   | 80%         | 75%           | Streaming complexity              |

---

## Enforcement Strategy

### Enforcement from Day One

Coverage gates are **enforced immediately**, not advisory. Rationale:

> Writing tests with coverage requirements from the start produces better tests than
> retrofitting coverage onto existing code. The cost of "test debt" compounds.

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml (complexity only - coverage in CI)
repos:
  - repo: local
    hooks:
      - id: radon-complexity
        name: Check cyclomatic complexity
        entry: uv run radon cc src/lumehaven --average -nc
        language: system
        pass_filenames: false

      - id: xenon-threshold
        name: Enforce complexity thresholds
        entry:
          uv run xenon --max-absolute C --max-modules B --max-average B src/lumehaven
        language: system
        pass_filenames: false
```

### CI Pipeline

```yaml
# .github/workflows/test.yml
jobs:
  test:
    steps:
      - name: Run tests with coverage
        run: |
          uv run pytest \
            --cov=lumehaven \
            --cov-branch \
            --cov-report=xml \
            --cov-report=term-missing \
            --cov-fail-under=80

      - name: Check complexity
        run: |
          uv run radon cc src/lumehaven --json > complexity.json
          uv run xenon --max-absolute C --max-modules B --max-average B src/lumehaven

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          files: coverage.xml
```

### Coverage Configuration

```toml
# pyproject.toml
[tool.coverage.run]
source = ["src/lumehaven"]
branch = true
omit = [
    "*/tests/*",
    "*/__pycache__/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
    "@abstractmethod",
]
fail_under = 80
show_missing = true

[tool.coverage.html]
directory = "htmlcov"
```

---

## Complexity Thresholds

### Radon/Xenon Configuration

| Threshold        | Value | Meaning                           |
| ---------------- | ----- | --------------------------------- |
| `--max-absolute` | C     | No single function exceeds CC 15  |
| `--max-modules`  | B     | No module average exceeds CC 10   |
| `--max-average`  | B     | Project average stays below CC 10 |

### Cognitive Complexity

```toml
# pyproject.toml (flake8 section or .flake8 file)
[tool.flake8]
max-cognitive-complexity = 15
```

### When Complexity Is Too High

If a function exceeds thresholds:

1. **Refactor first** — Extract helper functions, use early returns
2. **Document if unavoidable** — Add comment explaining why complexity is necessary
3. **Increase test coverage** — High CC needs more test cases

```python
# Example: Unavoidable complexity with documentation
def _parse_item(self, item: dict[str, Any]) -> Signal:
    """Parse OpenHAB item to Signal.

    Note: High complexity (CC ~12) due to OpenHAB's many item types.
    Each type requires different parsing. Refactoring would obscure
    the item-type mapping. Covered by parametrized tests for each type.
    """
    ...
```

---

## Quality Platform: SonarQube (Future)

### Planned Integration

SonarQube provides a unified dashboard for:

- Coverage trends over time
- Complexity hotspots visualization
- Technical debt tracking
- Code smell detection
- Security vulnerability scanning

### Implementation Timeline

| Phase | Milestone                          | Status      |
| ----- | ---------------------------------- | ----------- |
| 1     | Local metrics (radon, coverage.py) | **Current** |
| 2     | CI integration (Codecov/Coveralls) | Next        |
| 3     | SonarQube setup                    | Planned     |

### SonarQube Setup Notes (For Later)

```yaml
# Future: sonar-project.properties
sonar.projectKey=lumehaven sonar.sources=src/lumehaven sonar.tests=tests
sonar.python.coverage.reportPaths=coverage.xml
sonar.python.xunit.reportPath=pytest-report.xml
```

**Hosting options:**

- SonarCloud (free for open source)
- Self-hosted SonarQube (if private)

---

## Current Coverage Gaps

### Baseline Assessment

| Component                     | Lines | Current Coverage | Target | Gap          |
| ----------------------------- | ----- | ---------------- | ------ | ------------ |
| `adapters/openhab/adapter.py` | 466   | 0%               | 90%    | ❌ Critical  |
| `adapters/manager.py`         | 216   | 0%               | 90%    | ❌ Critical  |
| `config.py`                   | 280   | 0%               | 85%    | ❌ High      |
| `state/store.py`              | ~150  | ~80%             | 85%    | 🟡 Small gap |
| `core/signal.py`              | ~80   | ~90%             | 80%    | ✅ Met       |
| `adapters/openhab/units.py`   | ~100  | ~70%             | 80%    | 🟡 Small gap |

### Priority Order

1. **OpenHAB Adapter** — Highest risk, zero coverage
2. **Adapter Manager** — Complex state machine, zero coverage
3. **Config** — Startup critical, zero coverage
4. **Store** — Close to target, quick win
5. **Units** — Close to target, quick win

---

## Known Issues

### Failing Unit Test

**Status:** Documented, fix deferred until after strategy completion.

**Location:** To be identified and documented here.

**Remediation:** Will be addressed as part of coverage gap closure.

---

## References

- [coverage.py documentation](https://coverage.readthedocs.io/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
- [radon](https://radon.readthedocs.io/)
- [xenon](https://xenon.readthedocs.io/)
- [SonarQube Python](https://docs.sonarqube.org/latest/analysis/languages/python/)
- [ISTQB Foundation Syllabus](https://www.istqb.org/) — Risk-based testing
