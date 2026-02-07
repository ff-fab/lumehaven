# Run Tests & Check Coverage

!!! abstract "Goal" Run the test suite, understand coverage thresholds, and add new
tests.

## Quick Reference

| Command                    | What it does                                         |
| -------------------------- | ---------------------------------------------------- |
| `task test:be`             | Full backend test run (unit + integration + summary) |
| `task test:be:unit`        | Unit tests only — fast feedback loop                 |
| `task test:be:integration` | Robot Framework integration tests                    |
| `task test:be:cov`         | Tests with coverage report (terminal + XML)          |
| `task test:be:cov:html`    | Tests with HTML coverage report                      |
| `task test:be:thresholds`  | Validate per-module coverage thresholds              |

## Running Unit Tests

```bash
cd packages/backend
task test:be:unit
```

Unit tests use **sociable units** — real collaborators where possible, mock only
external I/O (HTTP, filesystem). See [Test Levels](../testing/02-test-levels.md) for
details.

## Running Integration Tests

Integration tests use Robot Framework for full vertical-slice testing with a mock
OpenHAB server:

```bash
task test:be:integration
```

## Coverage Thresholds

Coverage is enforced per-module with risk-based thresholds. The single source of truth
is `packages/backend/tests/coverage_config.py`.

| Risk Level | Line | Branch | Modules                                   |
| ---------- | ---- | ------ | ----------------------------------------- |
| Critical   | 90%  | 85%    | `adapters/*` (adapter implementations)    |
| High       | 85%  | 80%    | `adapters` (framework), `config`, `state` |
| Medium     | 80%  | 75%    | `api`                                     |
| Low        | 80%  | 70%    | `core`                                    |

New adapter implementations automatically inherit the Critical threshold.

To check thresholds locally:

```bash
task test:be:thresholds
```

## Adding New Tests

1. Create test files following the naming convention: `test_<module>_<aspect>.py`
2. Use shared fixtures from `tests/fixtures/`
3. Follow the [test file template](../testing/06-test-file-template-python.md)

For full testing strategy details, see the [Testing Strategy](../testing/00-index.md)
explanation section.
