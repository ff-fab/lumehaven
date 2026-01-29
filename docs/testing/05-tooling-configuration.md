# Tooling & Configuration

> **Scope:** Complete tooling setup for lumehaven testing—pytest, Robot Framework,
> coverage, complexity analysis, and CI integration.

## Tool Stack Overview

| Layer                 | Tool                                      | Purpose                       |
| --------------------- | ----------------------------------------- | ----------------------------- |
| **Unit Tests**        | pytest + pytest-asyncio                   | Fast, focused Python tests    |
| **Integration Tests** | Robot Framework + RESTinstance            | Human-readable API scenarios  |
| **E2E Tests**         | Robot Framework + Browser Library         | Browser automation (deferred) |
| **Coverage**          | pytest-cov (coverage.py)                  | Line and branch coverage      |
| **Complexity**        | radon, xenon, flake8-cognitive-complexity | Code complexity metrics       |
| **Quality Platform**  | SonarQube                                 | Unified dashboard (planned)   |

---

## pytest Configuration

### pyproject.toml

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
addopts = [
    "-v",
    "--tb=short",
    "--strict-markers",
    "--strict-config",
]
markers = [
    "unit: Unit tests (fast, no external dependencies)",
    "integration: Integration tests (require mock servers)",
    "slow: Tests that take > 1 second",
]
filterwarnings = [
    "error",
    "ignore::DeprecationWarning",
]
```

### Key Settings Explained

| Setting                    | Value                    | Why                                     |
| -------------------------- | ------------------------ | --------------------------------------- |
| `asyncio_mode = "auto"`    | Auto-detect async tests  | No manual `@pytest.mark.asyncio` needed |
| `--strict-markers`         | Error on unknown markers | Catches typos in marker names           |
| `--strict-config`          | Error on unknown config  | Catches typos in pyproject.toml         |
| `filterwarnings = "error"` | Warnings become errors   | Forces clean code                       |

---

## Coverage Configuration

### pyproject.toml

```toml
[tool.coverage.run]
source = ["src/lumehaven"]
branch = true
omit = [
    "*/__pycache__/*",
    "*/tests/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
    "@abstractmethod",
    "def __repr__",
    "if __name__ == .__main__.:",
]
fail_under = 80
show_missing = true
skip_covered = false

[tool.coverage.html]
directory = "htmlcov"

[tool.coverage.xml]
output = "coverage.xml"
```

### Running Coverage

```bash
# Basic coverage report
uv run pytest --cov=lumehaven --cov-report=term-missing

# With branch coverage (required)
uv run pytest --cov=lumehaven --cov-branch --cov-report=term-missing

# Generate HTML report for detailed analysis
uv run pytest --cov=lumehaven --cov-branch --cov-report=html

# Generate XML for CI upload
uv run pytest --cov=lumehaven --cov-branch --cov-report=xml

# Fail if below threshold
uv run pytest --cov=lumehaven --cov-branch --cov-fail-under=80
```

### Coverage Reports

| Format   | Command                     | Use Case                          |
| -------- | --------------------------- | --------------------------------- |
| Terminal | `--cov-report=term-missing` | Quick feedback during development |
| HTML     | `--cov-report=html`         | Detailed line-by-line analysis    |
| XML      | `--cov-report=xml`          | CI upload (Codecov, SonarQube)    |
| JSON     | `--cov-report=json`         | Programmatic analysis             |

---

## Complexity Tools

### Installation

```bash
uv add --dev radon xenon flake8-cognitive-complexity
```

### radon — Cyclomatic Complexity

```bash
# Show complexity for all modules
uv run radon cc src/lumehaven --average --show-complexity

# JSON output for CI
uv run radon cc src/lumehaven --json > complexity.json

# Show only complex functions (grade C or worse)
uv run radon cc src/lumehaven --min C
```

**Output example:**

```
src/lumehaven/adapters/openhab/adapter.py
    M 45:4 _parse_item - C (12)
    M 120:4 _process_event - B (8)
    M 200:4 subscribe_events - A (5)

Average complexity: B (7.5)
```

### xenon — Complexity Thresholds

```bash
# Enforce thresholds (fails if exceeded)
uv run xenon --max-absolute C --max-modules B --max-average B src/lumehaven
```

| Threshold        | Our Setting | Meaning                           |
| ---------------- | ----------- | --------------------------------- |
| `--max-absolute` | C (≤15)     | No single function exceeds CC 15  |
| `--max-modules`  | B (≤10)     | No module average exceeds CC 10   |
| `--max-average`  | B (≤10)     | Project average stays below CC 10 |

### flake8 — Cognitive Complexity

```toml
# pyproject.toml or .flake8
[tool.flake8]
max-cognitive-complexity = 15
extend-select = ["CCR"]  # Enable cognitive complexity rules
```

```bash
uv run flake8 --max-cognitive-complexity=15 src/lumehaven
```

---

## Pre-commit Hooks

### .pre-commit-config.yaml

```yaml
repos:
  # Existing hooks (ruff, mypy, etc.)
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.10.0
    hooks:
      - id: mypy
        additional_dependencies: [pydantic, fastapi]

  # Complexity checks
  - repo: local
    hooks:
      - id: radon-complexity
        name: Check cyclomatic complexity
        entry: uv run radon cc src/lumehaven --average -nc
        language: system
        pass_filenames: false
        always_run: true

      - id: xenon-threshold
        name: Enforce complexity thresholds
        entry:
          uv run xenon --max-absolute C --max-modules B --max-average B src/lumehaven
        language: system
        pass_filenames: false
        always_run: true

      - id: cognitive-complexity
        name: Check cognitive complexity
        entry: uv run flake8 --max-cognitive-complexity=15 src/lumehaven
        language: system
        pass_filenames: false
        always_run: true
```

### Running Pre-commit

```bash
# Run on staged files
pre-commit run

# Run on all files
pre-commit run --all-files

# Install hooks
pre-commit install
```

---

## Robot Framework Configuration

### Directory Structure

```
tests/integration/
├── __init__.robot           # Suite initialization
├── api_tests.robot          # API endpoint tests
├── signal_flow.robot        # Data flow scenarios
└── resources/
    ├── keywords.resource    # Custom keywords
    └── variables.resource   # Shared variables
```

### robot.toml (Robot Framework 7+)

```toml
[tool.robot]
outputdir = "results"
loglevel = "INFO"
include = ["integration"]
exclude = ["slow"]
```

### Running Robot Tests

```bash
# Run all integration tests
uv run robot tests/integration/

# Run with specific tag
uv run robot --include smoke tests/integration/

# Generate detailed report
uv run robot --outputdir results --log log.html tests/integration/
```

### RESTinstance Setup

```robot
*** Settings ***
Library    REST    http://localhost:8000    # Base URL
Library    Collections

*** Keywords ***
API Should Return Success
    [Arguments]    ${endpoint}
    GET    ${endpoint}
    Integer    response status    200
```

---

## CI/CD Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/test.yml
name: Test

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v3

      - name: Install dependencies
        run: uv sync --dev

      - name: Run unit tests with coverage
        run: |
          uv run pytest tests/unit \
            --cov=lumehaven \
            --cov-branch \
            --cov-report=xml \
            --cov-report=term-missing \
            --cov-fail-under=80

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          files: coverage.xml
          fail_ci_if_error: true

  complexity:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v3

      - name: Install dependencies
        run: uv sync --dev

      - name: Check cyclomatic complexity
        run: |
          uv run radon cc src/lumehaven --json > complexity.json
          uv run radon cc src/lumehaven --average --show-complexity

      - name: Enforce complexity thresholds
        run: |
          uv run xenon --max-absolute C --max-modules B --max-average B src/lumehaven

      - name: Check cognitive complexity
        run: |
          uv run flake8 --max-cognitive-complexity=15 src/lumehaven

      - name: Upload complexity report
        uses: actions/upload-artifact@v4
        with:
          name: complexity-report
          path: complexity.json

  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests # Only run if unit tests pass
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v3

      - name: Install dependencies
        run: uv sync --dev

      - name: Run integration tests
        run: |
          uv run robot \
            --outputdir results \
            --xunit xunit.xml \
            tests/integration/

      - name: Upload Robot results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: robot-results
          path: results/
```

### Codecov Configuration

```yaml
# codecov.yml
coverage:
  precision: 2
  round: down
  status:
    project:
      default:
        target: 80%
        threshold: 1%
    patch:
      default:
        target: 80%

comment:
  layout: 'reach,diff,flags,files'
  behavior: default
```

---

## Local Development Commands

### Quick Reference

```bash
# Run all tests
uv run pytest

# Run only unit tests
uv run pytest tests/unit -m unit

# Run with coverage
uv run pytest --cov=lumehaven --cov-branch --cov-report=html

# Run specific test file
uv run pytest tests/unit/adapters/test_manager.py

# Run tests matching pattern
uv run pytest -k "retry"

# Run integration tests
uv run robot tests/integration/

# Check complexity
uv run radon cc src/lumehaven --average --show-complexity

# Full pre-commit check
pre-commit run --all-files
```

### Watch Mode (Development)

```bash
# Install pytest-watch
uv add --dev pytest-watch

# Run tests on file change
uv run ptw tests/unit -- --cov=lumehaven
```

---

## Known Issues & Remediation

### Failing Unit Test

**Status:** Documented, to be fixed after strategy completion.

**Action items:**

1. Identify the failing test
2. Determine root cause (test bug vs code bug)
3. Fix and verify coverage is maintained
4. Update this section when resolved

### Missing Test Fixtures

**Status:** `tests/fixtures/` directory exists but is empty.

**Action items:**

1. Create `openhab_responses.py` with mock API data
2. Create `signals.py` with test Signal instances
3. Migrate existing inline test data to fixtures

### Unconfigured Coverage

**Status:** pytest-cov installed but not configured.

**Action items:**

1. Add `[tool.coverage.*]` sections to pyproject.toml ✅ (defined above)
2. Add CI workflow with coverage upload ✅ (defined above)
3. Set up Codecov integration

---

## SonarQube Integration (Planned)

### Future Setup

SonarQube will provide unified quality dashboard once the project matures.

**Prerequisites:**

- Coverage XML reports (already configured)
- Complexity JSON reports (already configured)
- SonarCloud account (free for open source)

**Configuration (for later):**

```properties
# sonar-project.properties
sonar.projectKey=ff-fab_lumehaven
sonar.organization=ff-fab
sonar.sources=src/lumehaven
sonar.tests=tests
sonar.python.coverage.reportPaths=coverage.xml
sonar.python.version=3.12
```

**CI step (for later):**

```yaml
- name: SonarCloud Scan
  uses: SonarSource/sonarcloud-github-action@master
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
```

---

## Dependencies Summary

### Required Dev Dependencies

```toml
# pyproject.toml [project.optional-dependencies]
dev = [
    # Testing
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "pytest-watch>=4.2.0",

    # Robot Framework
    "robotframework>=7.0",
    "robotframework-requests>=0.9.0",
    "RESTinstance>=1.4.0",

    # Complexity
    "radon>=6.0.0",
    "xenon>=0.9.0",
    "flake8>=7.0.0",
    "flake8-cognitive-complexity>=0.1.0",

    # Type checking
    "mypy>=1.8.0",

    # Linting
    "ruff>=0.4.0",

    # Pre-commit
    "pre-commit>=4.0.0",
]
```

---

## References

- [pytest documentation](https://docs.pytest.org/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
- [coverage.py](https://coverage.readthedocs.io/)
- [radon](https://radon.readthedocs.io/)
- [Robot Framework](https://robotframework.org/)
- [RESTinstance](https://github.com/asyrjasalo/RESTinstance)
- [Codecov](https://docs.codecov.com/)
- [SonarQube Python](https://docs.sonarqube.org/latest/analysis/languages/python/)
