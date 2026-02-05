# Test Implementation Plan

> **Phase 2 Task:** Comprehensive test coverage per ADR-006 **Approach:** Greenfield —
> delete existing tests and rebuild following the documented test strategy exactly

## Prerequisites Check

### ✅ Tools Installed

| Tool             | Status | Version |
| ---------------- | ------ | ------- |
| pytest           | ✅     | 9.0.2   |
| pytest-asyncio   | ✅     | 1.3.0   |
| pytest-cov       | ✅     | 7.0.0   |
| coverage         | ✅     | 7.13.2  |
| Robot Framework  | ✅     | 7.4.1   |
| RESTinstance     | ✅     | 1.6.2   |
| radon            | ✅     | 6.0.1   |
| xenon            | ✅     | 0.9.3   |
| flake8-cognitive | ✅     | 0.1.0   |

### ~~Missing Tools~~ ✅ All Installed

All required tools have been installed and verified.

### ~~Configuration Updates Needed~~ ✅ Complete

1. ✅ **pyproject.toml** — Coverage configuration added (branch coverage, exclusions)
2. ✅ **pyproject.toml** — Strict markers, filterwarnings configured
3. ⏳ **.pre-commit-config.yaml** — Complexity hooks (deferred to CI setup)

---

## Scope: Source Files to Test

Based on test strategy risk assessment:

| Component                     | Lines | Risk Level   | Coverage Target      | Priority |
| ----------------------------- | ----- | ------------ | -------------------- | -------- |
| `adapters/openhab/adapter.py` | 465   | **Critical** | 90% line, 85% branch | 1        |
| `adapters/manager.py`         | 215   | **Critical** | 90% line, 85% branch | 2        |
| `config.py`                   | 252   | **High**     | 85% line, 80% branch | 3        |
| `state/store.py`              | 233   | **High**     | 85% line, 80% branch | 4        |
| `adapters/openhab/units.py`   | 176   | **Medium**   | 80% line, 75% branch | 5        |
| `api/routes.py`               | 181   | **Medium**   | 80% line, 75% branch | 6        |
| `core/signal.py`              | 94    | **Low**      | 80% line, 70% branch | 7        |
| `api/sse.py`                  | 69    | **Medium**   | 80% line, 75% branch | 8        |
| `core/exceptions.py`          | 69    | **Low**      | 80% line, 70% branch | 9        |
| `adapters/protocol.py`        | 154   | **Low**      | 80% line, 70% branch | 10       |

**Excluded from unit tests** (tested at integration level):

- `main.py` — App startup, tested via integration
- `__init__.py` files — Re-exports only

---

## Implementation Phases

> **Process:** After completing each phase, stop and provide a summary for review before
> proceeding to the next phase. This ensures alignment and allows for feedback.

### ✅ Phase 0: Setup (Complete)

- [x] Install missing tools (radon, xenon, flake8-cognitive-complexity)
- [x] Update pyproject.toml with coverage configuration
- [x] Delete existing tests
- [x] Create test directory structure per test strategy
- [x] Create base fixtures (conftest.py)
- [x] Validate setup with empty test run
- [x] Add per-module coverage threshold validation (pytest hook + standalone script)

### ✅ Phase 1: Core Models (Complete)

**Goal:** Establish test patterns and validate infrastructure

| Step | File                 | Tests | Coverage | Techniques Used                                   |
| ---- | -------------------- | ----- | -------- | ------------------------------------------------- |
| 1.1  | `core/signal.py`     | 20    | 100%     | Specification, Round-trip, Decision Table, Branch |
| 1.2  | `core/exceptions.py` | 16    | 100%     | Structural Verification, Specification, Condition |

**Key outcome:** Test technique documentation pattern established — every test module
documents techniques in module docstring, individual tests document non-obvious choices.

### ✅ Phase 2: State Layer (Complete)

**Goal:** Test the data backbone with sociable unit approach

| Step | File             | Tests | Coverage | Techniques Used                                   |
| ---- | ---------------- | ----- | -------- | ------------------------------------------------- |
| 2.1  | `state/store.py` | 25    | 93%      | Specification, State Transition, Branch, Protocol |

**Key outcome:** Async testing patterns established — proper generator cleanup with
`aclose()`, use of `asyncio.Event()` for synchronization, `contextlib.suppress()` for
cancellation handling. Queue overflow and throttled logging paths fully tested.

### ✅ Phase 3: Configuration (Complete)

**Goal:** Test startup-critical config parsing

| Step | File        | Tests | Coverage | Techniques Used                                       |
| ---- | ----------- | ----- | -------- | ----------------------------------------------------- |
| 3.1  | `config.py` | 36    | 100%     | Specification, Decision Table, Branch, Error Guessing |

**Key outcome:** Discriminated union routing verified via Decision Table technique
(parametrized). Environment variable expansion tested with Branch Coverage for all type
dispatch paths. YAML loading error cases exhaustively tested with Error Guessing. Path
search fallback (../../) explicitly verified. Shared fixtures (`reset_settings_cache`,
`tmp_config_file`) added to `tests/fixtures/config.py`.

### ✅ Phase 4: Adapter Protocol (Complete)

**Goal:** Test abstract interface with Protocol structural subtyping verification

| Step | File                   | Tests | Coverage | Techniques Used                                     |
| ---- | ---------------------- | ----- | -------- | --------------------------------------------------- |
| 4.1  | `adapters/protocol.py` | 16    | 100%     | Structural Subtyping, Specification, Decision Table |

**Key outcome:** Protocol `@runtime_checkable` behavior verified via mock
implementations (CompliantAdapter, MissingMethodAdapter, MissingPropertyAdapter). Added
coverage exclusion for Protocol ellipsis stubs (`...`) in pyproject.toml since these are
type-only placeholders.

### ✅ Phase 5: OpenHAB Units (Complete)

**Goal:** Test parsing logic (high complexity, many edge cases)

| Step | File                        | Tests | Coverage | Techniques Used                                            |
| ---- | --------------------------- | ----- | -------- | ---------------------------------------------------------- |
| 5.1  | `adapters/openhab/units.py` | 85    | 100%     | Equivalence Partitioning, BVA, Decision Table, Error Guess |

**Key outcome:** Comprehensive pattern parsing via Equivalence Partitioning (float/int/
string/percent formats). Banker's rounding edge cases documented with BVA. Decision
Table for `format_value()` condition combinations. Encoding edge cases tested
(double-encoded UTF-8, CJK symbols, Unicode normalization scenarios). Test inputs
derived from shared OpenHAB fixtures (`tests/fixtures/openhab_responses.py`).

### ✅ Phase 6: OpenHAB Adapter (Complete)

**Goal:** Most complex component, state transitions, external I/O mocking

| Step | File                          | Tests | Coverage | Techniques Used                                              |
| ---- | ----------------------------- | ----- | -------- | ------------------------------------------------------------ |
| 6.1  | `adapters/openhab/adapter.py` | 40    | 91%      | State Transition, Specification, Branch, Error Guessing, BVA |

**Key outcome:** Adapter tests split into 5 focused modules (init, api, extract,
process, sse) for maintainability. External I/O mocked via `respx` for HTTP and
AsyncIterator mocks for SSE. Connection state transitions verified. Error recovery
tested via Error Guessing. Shared fixtures in `tests/unit/adapters/openhab/conftest.py`
and `tests/fixtures/openhab_sse.py`.

### ✅ Phase 7: Adapter Manager (Complete)

**Goal:** Lifecycle state machine testing

| Step | File                  | Tests | Coverage | Techniques Used                                      |
| ---- | --------------------- | ----- | -------- | ---------------------------------------------------- |
| 7.1  | `adapters/manager.py` | 22    | 91%      | State Transition, BVA, Specification, Error Guessing |

**Key outcome:** State transitions verified (disconnected→connected, connection failure,
stop_all cleanup). Retry delay exponential backoff tested with BVA at boundary points
(INITIAL=5s, mid-range, MAX=300s). MockAdapter class implements SmartHomeAdapter
protocol with configurable failure modes. Sociable unit tests use real SignalStore with
injected mock adapters. Test classes organized by functionality: Registration,
Lifecycle, RetryLogic, SyncBehavior, MultipleAdapters.

### ✅ Phase 8: API Layer (Complete)

**Goal:** Route handlers with mocked store

| Step | File            | Tests | Coverage | Techniques Used                                          |
| ---- | --------------- | ----- | -------- | -------------------------------------------------------- |
| 8.1  | `api/routes.py` | 24    | 100%     | State Transition, Specification, Round-trip, Error Guess |
| 8.2  | `api/sse.py`    | 7     | 100%     | Specification, State Transition, Error Guessing          |

**Key outcome:** FastAPI dependency override pattern used to inject isolated SignalStore
for testing. Mock AdapterManager provides configurable adapter states for /health
endpoint testing. SSE generator tested directly for event format and subscription
lifecycle. Full endpoint integration tested via httpx AsyncClient with ASGI transport.
Tests organized: routes_health.py, routes_signals.py, sse.py.

### ✅ Phase 9: Integration Tests (Robot Framework) (Complete)

**Goal:** Full vertical slice with mock OpenHAB server

| Step | Scope          | What to Test              | Status |
| ---- | -------------- | ------------------------- | ------ |
| 9.1  | API smoke      | Health, signals endpoints | ✅     |
| 9.2  | SSE flow       | Real-time updates         | ✅     |
| 9.3  | Error handling | Mock failures             | ✅     |

**Key outcome:** Robot Framework integration tests implemented with custom Python
keyword libraries. Mock OpenHAB server provides fixture-based responses with mutable
state. Per-suite server lifecycle via `ROBOT_LIBRARY_SCOPE = "SUITE"`. SSE testing uses
background thread reader with event queue. Run with `task test:be:integration`.

**Test files created:**

- `tests/integration/api_tests.robot` — Health, signals, metrics endpoint verification
- `tests/integration/sse_tests.robot` — Real-time signal update propagation
- `tests/integration/error_handling.robot` — Failure modes, degraded health states
- `tests/integration/mock_openhab/server.py` — FastAPI mock with test control endpoints
- `tests/integration/libraries/ServerKeywords.py` — Server lifecycle management
- `tests/integration/libraries/SSEKeywords.py` — SSE stream testing
- `tests/integration/resources/keywords.resource` — Shared Robot Framework keywords

---

## ✅ Test Implementation Complete

All phases completed. Coverage thresholds achieved across all modules.

## Test Design Approach Per Component

### For Each Component We Will:

1. **Review the source** together to understand functions/classes
2. **Identify test cases** using techniques from test strategy:
   - Equivalence partitioning (via parametrization)
   - Boundary value analysis
   - State transition (for stateful components)
   - Decision tables (for complex conditionals)
3. **Design fixtures** needed
4. **Implement tests** with your approval
5. **Verify coverage** meets targets

### Granularity

For your involvement, I'll present:

- **Per-function** test plans for complex components (adapter, manager, config)
- **Per-class** test plans for simpler components (signal, store, exceptions)

---

## Directory Structure (Final)

```
tests/
├── conftest.py                    # Global fixtures + coverage thresholds
├── fixtures/
│   ├── __init__.py
│   ├── config.py                  # Config test fixtures
│   ├── openhab_responses.py       # Mock API data
│   ├── openhab_sse.py             # SSE event fixtures
│   └── signals.py                 # Signal factories
├── unit/
│   ├── conftest.py                # Unit-specific fixtures
│   ├── test_config.py
│   ├── adapters/
│   │   ├── conftest.py
│   │   ├── test_manager.py
│   │   ├── test_protocol.py
│   │   └── openhab/
│   │       ├── conftest.py
│   │       ├── test_adapter_api.py
│   │       ├── test_adapter_extract.py
│   │       ├── test_adapter_init.py
│   │       ├── test_adapter_process.py
│   │       ├── test_adapter_sse.py
│   │       └── test_units.py
│   ├── api/
│   │   ├── conftest.py
│   │   ├── test_routes_health.py
│   │   ├── test_routes_signals.py
│   │   └── test_sse.py
│   ├── core/
│   │   ├── test_signal.py
│   │   └── test_exceptions.py
│   └── state/
│       └── test_store.py
└── integration/
    ├── api_tests.robot
    ├── sse_tests.robot
    ├── error_handling.robot
    ├── mock_openhab/
    │   ├── __init__.py
    │   └── server.py
    ├── libraries/
    │   ├── __init__.py
    │   ├── ServerKeywords.py
    │   └── SSEKeywords.py
    └── resources/
        └── keywords.resource
```

---

## Next Step

**Ready to proceed?**

1. I'll first install missing tools and update configuration
2. Then delete existing tests
3. Create the directory structure and base conftest.py
4. Start with Phase 1: `core/signal.py` test design

Confirm to proceed with Phase 0 setup.
