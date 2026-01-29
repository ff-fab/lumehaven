# ADR-006: Testing Strategy

## Status

Accepted

## Context

Lumehaven needs a testing strategy that:

1. Ensures reliability of the backend (BFF) which handles smart home API integration
2. Validates the Signal abstraction and platform adapters (OpenHAB, later HomeAssistant)
3. Supports iterative development with increasing sophistication over time
4. Keeps frontend and E2E testing lightweight initially
5. Enables future expansion without major rework

The PoC had **zero tests** (noted in lessons learned), leading to fragile code and
difficult refactoring. The complex parsing logic in `openhab.py` (unit extraction, value
formatting, special states) is error-prone and needs thorough coverage.

Key constraints:

- **Backend-first focus:** Core business logic lives in adapters and signal
  normalization
- **Smart home mocking:** Need to simulate OpenHAB/HomeAssistant APIs without real
  instances
- **Learning goal:** Robot Framework is of interest for its human-readable syntax and
  BDD-style capabilities
- **Lightweight start:** Don't over-engineer; add sophistication as needed

## Considered Options

### Option 1: pytest-Only Strategy

Traditional Python testing with pytest for all backend tests.

**Stack:**

- Backend: pytest + pytest-asyncio + httpx (for FastAPI testing)
- Frontend: Vitest (if needed later)
- E2E: None initially, Playwright later

**Pros:**

- Familiar to most Python developers
- Excellent IDE integration
- Fast execution
- Rich assertion library and fixtures

**Cons:**

- Tests can become code-heavy and hard to read for non-developers
- No built-in support for BDD-style acceptance tests
- Separate tooling needed for integration/acceptance layer

### Option 2: Robot Framework for Integration + pytest for Units

Hybrid approach using Robot Framework for integration/acceptance tests and pytest for
unit tests.

**Stack:**

- Backend Unit Tests: pytest
- Backend Integration/Acceptance: Robot Framework + RESTinstance
- Frontend: Vitest (lightweight, later)
- E2E: Robot Framework + Browser Library (later)

**Pros:**

- Human-readable test cases for integration scenarios
- Robot Framework's keyword-driven approach suits API testing
- Same tool can grow into E2E testing
- Clear separation: pytest for units, RF for integration
- RESTinstance library excellent for REST API testing

**Cons:**

- Two testing frameworks to maintain
- Robot Framework has learning curve
- Slightly more setup complexity

### Option 3: Robot Framework for Everything

Use Robot Framework at all levels, including unit tests via Python libraries.

**Stack:**

- All testing: Robot Framework
- Custom Python keywords for unit-level testing
- RESTinstance for API testing
- Browser Library for E2E

**Pros:**

- Single testing framework
- Consistent syntax across all test levels
- Business stakeholders can read all tests

**Cons:**

- Unit tests in RF are awkward compared to pytest
- Slower test execution for unit tests
- Fighting the tool at the unit level
- Over-engineering for a personal project

### Option 4: Behavior-Driven with pytest-bdd

Use pytest-bdd for Gherkin-style tests while staying in pytest ecosystem.

**Stack:**

- Backend: pytest + pytest-bdd
- Frontend: Vitest
- E2E: Playwright with pytest

**Pros:**

- Gherkin syntax for scenarios
- Stays within pytest ecosystem
- Good for acceptance criteria

**Cons:**

- pytest-bdd adds complexity without RF's keyword reusability
- Less powerful than Robot Framework for complex scenarios
- Gherkin can be verbose

## Decision

Use **Option 2: Robot Framework for Integration + pytest for Units**

### Test Pyramid Structure

```
                    ┌─────────────┐
                    │    E2E      │  Robot Framework + Browser Library
                    │  (Later)    │  (deferred until UI is stable)
                    └─────────────┘
               ┌─────────────────────┐
               │    Integration      │  Robot Framework + RESTinstance
               │   (API/Adapter)     │  Human-readable scenarios
               └─────────────────────┘
          ┌───────────────────────────────┐
          │         Unit Tests            │  pytest + pytest-asyncio
          │  (Signal, Adapters, Parsing)  │  Fast, focused, thorough
          └───────────────────────────────┘
```

### Backend Testing (Primary Focus)

#### Unit Tests with pytest

**Location:** `packages/backend/tests/unit/`

**What to test:**

- Signal dataclass creation and validation
- Unit extraction from OpenHAB patterns (`get_unit_from_pattern`)
- Value formatting logic (`get_value_from_state`)
- Special state handling (`UNDEF`, `NULL`, `unavailable`)
- Measurement system (SI/US) selection
- Edge cases from real OpenHAB API responses

**Example test structure:**

```python
# tests/unit/test_signal.py
import pytest
from lumehaven.models import Signal

class TestSignal:
    def test_signal_creation_with_unit(self):
        signal = Signal(id="temp_living", value="21.5", unit="°C")
        assert signal.value == "21.5"
        assert signal.unit == "°C"

    def test_signal_creation_without_unit(self):
        signal = Signal(id="switch_light", value="ON", unit="")
        assert signal.unit == ""

# tests/unit/adapters/test_openhab_parsing.py
class TestOpenHABPatternParsing:
    @pytest.mark.parametrize("pattern,expected_unit,expected_format", [
        ("%d Wh", "Wh", "%d"),
        ("%.1f °C", "°C", "%.1f"),
        ("%d %%", "%", "%d"),
        ("€/Monat", "€/Monat", "%s"),
    ])
    def test_get_unit_from_pattern(self, pattern, expected_unit, expected_format):
        unit, fmt = get_unit_from_pattern(pattern)
        assert unit == expected_unit
        assert fmt == expected_format

    @pytest.mark.parametrize("state,expected_value", [
        ("UNDEF", "UNDEF"),
        ("NULL", "NULL"),
        ("19.6 °C", "19.6"),
    ])
    def test_special_states_pass_through(self, state, expected_value):
        # ...
```

**Fixtures for OpenHAB responses:**

```python
# tests/conftest.py
import pytest
import json
from pathlib import Path

@pytest.fixture
def openhab_items_response():
    """Real response from OpenHAB API (anonymized)"""
    return json.loads((Path(__file__).parent / "fixtures/openhab_items.json").read_text())

@pytest.fixture
def openhab_sse_events():
    """Sample SSE events from OpenHAB"""
    return [
        {"topic": "TemperatureLiving", "state": "21.5 °C"},
        {"topic": "SwitchLight", "state": "ON"},
        # ...
    ]
```

#### Integration Tests with Robot Framework

**Location:** `packages/backend/tests/integration/`

**What to test:**

- Full adapter → Signal flow
- FastAPI endpoints (REST API)
- SSE event streaming
- Mock smart home API interactions

**Example Robot Framework test:**

```robot
*** Settings ***
Documentation    OpenHAB Adapter Integration Tests
Library          RESTinstance
Library          Collections
Suite Setup      Initialize Test Environment

*** Variables ***
${BACKEND_URL}    http://localhost:8000
${MOCK_OPENHAB}   http://localhost:8081

*** Test Cases ***
Get All Signals Returns Normalized Data
    [Documentation]    Verify that signals are properly normalized from OpenHAB
    [Tags]    integration    openhab

    Given OpenHAB Has Temperature Item "TemperatureLiving" With State "21.5 °C"
    When I Request All Signals From Backend
    Then Response Status Should Be 200
    And Signal "TemperatureLiving" Should Have Value "21.5"
    And Signal "TemperatureLiving" Should Have Unit "°C"

Handle OpenHAB Special States
    [Documentation]    UNDEF and NULL states should pass through unchanged
    [Tags]    integration    openhab    edge-case

    Given OpenHAB Has Item "SensorOffline" With State "UNDEF"
    When I Request Signal "SensorOffline"
    Then Signal Value Should Be "UNDEF"
    And Signal Unit Should Be Empty

*** Keywords ***
Initialize Test Environment
    Set Backend URL    ${BACKEND_URL}
    Start Mock OpenHAB Server

Given OpenHAB Has Temperature Item "${name}" With State "${state}"
    Configure Mock Response    /rest/items/${name}
    ...    {"name": "${name}", "state": "${state}", "type": "Number:Temperature"}

When I Request All Signals From Backend
    GET    ${BACKEND_URL}/api/signals
    Integer    response status    200

Then Signal "${name}" Should Have Value "${expected}"
    ${signals}=    Output    response body
    ${signal}=    Get From Dictionary    ${signals}    ${name}
    Should Be Equal    ${signal}[value]    ${expected}
```

### Frontend Testing (Lightweight)

**Location:** `packages/frontend/tests/` **Framework:** Vitest (comes with Vite)

**Initial scope (minimal):**

- Component smoke tests (renders without crashing)
- Critical utility functions

**Deferred:**

- Complex component interaction tests
- Visual regression testing
- Accessibility testing

```typescript
// tests/components/SignalDisplay.test.tsx
import { render, screen } from '@testing-library/react';
import { SignalDisplay } from '../src/components/SignalDisplay';

describe('SignalDisplay', () => {
  it('renders value and unit', () => {
    render(<SignalDisplay value="21.5" unit="°C" />);
    expect(screen.getByText('21.5')).toBeInTheDocument();
    expect(screen.getByText('°C')).toBeInTheDocument();
  });
});
```

### E2E Testing (Deferred)

**Framework:** Robot Framework + Browser Library (Playwright-based) **When:** After
frontend is stable (Phase 3+)

**Initial scope:**

- Critical user journeys only
- Dashboard loads and displays data
- Real-time updates work

```robot
*** Settings ***
Documentation    End-to-End Dashboard Tests
Library          Browser

*** Test Cases ***
Dashboard Shows Live Temperature
    [Tags]    e2e    smoke
    New Browser    chromium    headless=true
    New Page    ${DASHBOARD_URL}
    Wait For Elements State    css=.signal-temperature    visible
    Get Text    css=.signal-temperature .value    should contain    °C
```

### Mocking Strategy

#### Smart Home API Mocking

**Approach:** WireMock or custom FastAPI mock server

```python
# tests/mocks/openhab_mock.py
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

mock_openhab = FastAPI()

MOCK_ITEMS = {
    "TemperatureLiving": {
        "name": "TemperatureLiving",
        "state": "21.5 °C",
        "type": "Number:Temperature",
        "stateDescription": {"pattern": "%.1f °C"}
    }
}

@mock_openhab.get("/rest/items")
def get_items():
    return list(MOCK_ITEMS.values())

@mock_openhab.get("/rest/items/{item_name}")
def get_item(item_name: str):
    return MOCK_ITEMS.get(item_name, {"error": "not found"})
```

**Fixture data:** Store real (anonymized) API responses in `tests/fixtures/` for
realistic testing.

### Test Data from PoC

Leverage examples from
[openhab-example-api-calls.md](../ll/openhab-example-api-calls.md):

- 200+ real item types with various patterns
- SSE event formats
- Edge cases (transformed states, special values)

## Decision Drivers

1. **Backend complexity:** Parsing and normalization logic is the riskiest code
2. **Human readability:** Robot Framework tests serve as living documentation
3. **Extensibility:** RF scales from API tests to full E2E
4. **pytest strength:** Best tool for Python unit tests
5. **Lightweight start:** Don't test frontend heavily until it stabilizes
6. **Learning opportunity:** Robot Framework is a stated interest

## Decision Matrix

| Criterion                 | Option 1 (pytest only) | Option 2 (RF + pytest) | Option 3 (RF only) | Option 4 (pytest-bdd) |
| ------------------------- | ---------------------- | ---------------------- | ------------------ | --------------------- |
| Backend unit testing      | 5                      | 5                      | 2                  | 4                     |
| Integration testing       | 3                      | 5                      | 5                  | 3                     |
| Readability for scenarios | 2                      | 5                      | 5                  | 4                     |
| Learning curve            | 5                      | 3                      | 3                  | 4                     |
| E2E extensibility         | 3                      | 5                      | 5                  | 4                     |
| Maintenance burden        | 5                      | 3                      | 4                  | 3                     |
| **Total**                 | **23**                 | **26**                 | **24**             | **22**                |

_Scale: 1 (poor) to 5 (excellent)_

## Implementation Plan

### Phase 1: Foundation (Current Sprint)

- [ ] Set up pytest with pytest-asyncio
- [ ] Create test fixtures from PoC/OpenHAB examples
- [ ] Unit tests for Signal model
- [ ] Unit tests for pattern parsing logic

### Phase 2: Integration Layer

- [ ] Install Robot Framework + RESTinstance
- [ ] Create mock OpenHAB server
- [ ] Integration tests for adapter → Signal flow
- [ ] Integration tests for FastAPI endpoints

### Phase 3: Frontend Basics

- [ ] Set up Vitest
- [ ] Smoke tests for main components
- [ ] Basic utility function tests

### Phase 4: E2E (Future)

- [ ] Install Browser Library
- [ ] Critical path E2E tests
- [ ] CI integration for E2E suite

## Directory Structure

```
packages/
├── backend/
│   ├── src/
│   │   └── lumehaven/
│   ├── tests/
│   │   ├── conftest.py           # pytest fixtures
│   │   ├── unit/
│   │   │   ├── test_signal.py
│   │   │   └── adapters/
│   │   │       └── test_openhab.py
│   │   ├── integration/
│   │   │   ├── api_tests.robot
│   │   │   └── adapter_tests.robot
│   │   ├── fixtures/
│   │   │   ├── openhab_items.json
│   │   │   └── openhab_events.json
│   │   └── mocks/
│   │       └── openhab_mock.py
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   ├── tests/
│   │   └── components/
│   └── vitest.config.ts
└── e2e/                          # (Phase 4)
    ├── tests/
    │   └── dashboard.robot
    └── resources/
        └── keywords.resource
```

## Tooling Configuration

### pytest (pyproject.toml)

```toml
[tool.pytest.ini_options]
testpaths = ["tests/unit"]
asyncio_mode = "auto"
markers = [
    "slow: marks tests as slow",
    "integration: marks tests requiring external services",
]
```

### Robot Framework (robot.yaml or CLI)

```yaml
# robot.yaml
paths:
  - tests/integration
output_dir: reports/robot
variables:
  BACKEND_URL: http://localhost:8000
```

### CI Integration

```yaml
# .github/workflows/test.yml (excerpt)
jobs:
  backend-tests:
    steps:
      - name: Run unit tests
        run: uv run pytest tests/unit -v --cov

      - name: Run integration tests
        run: |
          uv run python -m tests.mocks.openhab_mock &
          uv run robot tests/integration
```

## Consequences

### Positive

- Thorough backend coverage where complexity lives
- Human-readable integration tests serve as documentation
- Clear path from unit tests to full E2E
- Robot Framework skills transferable to other projects
- Lightweight frontend testing reduces early maintenance

### Negative

- Two testing frameworks to learn and maintain
- Robot Framework adds dependencies
- Initial setup takes longer than pytest-only

### Risks & Mitigations

| Risk                      | Mitigation                                                |
| ------------------------- | --------------------------------------------------------- |
| RF learning curve         | Start with simple API tests, grow complexity gradually    |
| Two frameworks diverge    | Clear separation: pytest=units, RF=integration+           |
| Mock drift from real APIs | Use fixtures from real API responses, update periodically |

## Related Documents

- **[Test Strategy](../testing/00-index.md)** — Detailed implementation guide for this
  ADR, covering test design techniques, coverage targets, and tooling configuration.

## References

- Robot Framework: https://robotframework.org/
- RESTinstance: https://github.com/asyrjasalo/RESTinstance
- Browser Library: https://robotframework-browser.org/
- pytest-asyncio: https://pytest-asyncio.readthedocs.io/
- Vitest: https://vitest.dev/
- PoC lessons: [docs/ll/00-lessons-from-poc.md](../ll/00-lessons-from-poc.md)
- OpenHAB examples:
  [docs/ll/openhab-example-api-calls.md](../ll/openhab-example-api-calls.md)

_January 5, 2026_
