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

### Phase 1: Core Models (Low Risk, Foundation)

**Goal:** Establish test patterns and validate infrastructure

| Step | File                 | What to Test                              |
| ---- | -------------------- | ----------------------------------------- |
| 1.1  | `core/signal.py`     | Signal dataclass validation, immutability |
| 1.2  | `core/exceptions.py` | Custom exception hierarchy                |

### Phase 2: State Layer (High Risk)

**Goal:** Test the data backbone with sociable unit approach

| Step | File             | What to Test                            |
| ---- | ---------------- | --------------------------------------- |
| 2.1  | `state/store.py` | SignalStore CRUD, subscription, publish |

### Phase 3: Configuration (High Risk)

**Goal:** Test startup-critical config parsing

| Step | File        | What to Test                                            |
| ---- | ----------- | ------------------------------------------------------- |
| 3.1  | `config.py` | Environment loading, YAML parsing, discriminated unions |

### Phase 4: Adapter Protocol (Low Risk)

**Goal:** Test abstract interfaces before implementations

| Step | File                   | What to Test                       |
| ---- | ---------------------- | ---------------------------------- |
| 4.1  | `adapters/protocol.py` | Protocol compliance helpers if any |

### Phase 5: OpenHAB Units (Medium Risk)

**Goal:** Test parsing logic (high complexity, many edge cases)

| Step | File                        | What to Test                           |
| ---- | --------------------------- | -------------------------------------- |
| 5.1  | `adapters/openhab/units.py` | Unit extraction, value formatting, BVA |

### Phase 6: OpenHAB Adapter (Critical Risk)

**Goal:** Most complex component, state transitions, external I/O mocking

| Step | File                          | What to Test                          |
| ---- | ----------------------------- | ------------------------------------- |
| 6.1  | `adapters/openhab/adapter.py` | Parsing, SSE handling, error recovery |

### Phase 7: Adapter Manager (Critical Risk)

**Goal:** Lifecycle state machine testing

| Step | File                  | What to Test                                  |
| ---- | --------------------- | --------------------------------------------- |
| 7.1  | `adapters/manager.py` | State transitions, retry logic, BVA on delays |

### Phase 8: API Layer (Medium Risk)

**Goal:** Route handlers with mocked store

| Step | File            | What to Test                     |
| ---- | --------------- | -------------------------------- |
| 8.1  | `api/routes.py` | REST endpoints, error responses  |
| 8.2  | `api/sse.py`    | SSE streaming, client disconnect |

### Phase 9: Integration Tests (Robot Framework)

**Goal:** Full vertical slice with mock OpenHAB server

| Step | Scope          | What to Test              |
| ---- | -------------- | ------------------------- |
| 9.1  | API smoke      | Health, signals endpoints |
| 9.2  | SSE flow       | Real-time updates         |
| 9.3  | Error handling | Mock failures             |

---

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

## Directory Structure (Target)

```
tests/
├── conftest.py                    # Global fixtures
├── fixtures/
│   ├── __init__.py
│   ├── openhab_responses.py       # Mock API data
│   └── signals.py                 # Signal factories
├── unit/
│   ├── conftest.py                # Unit-specific fixtures
│   ├── test_config.py
│   ├── adapters/
│   │   ├── conftest.py
│   │   ├── test_manager.py
│   │   ├── test_protocol.py
│   │   └── openhab/
│   │       ├── test_adapter.py
│   │       └── test_units.py
│   ├── api/
│   │   ├── test_routes.py
│   │   └── test_sse.py
│   ├── core/
│   │   ├── test_signal.py
│   │   └── test_exceptions.py
│   └── state/
│       └── test_store.py
└── integration/
    ├── conftest.py
    ├── api_tests.robot
    └── mock_openhab/
        ├── __init__.py
        └── server.py
```

---

## Next Step

**Ready to proceed?**

1. I'll first install missing tools and update configuration
2. Then delete existing tests
3. Create the directory structure and base conftest.py
4. Start with Phase 1: `core/signal.py` test design

Confirm to proceed with Phase 0 setup.
