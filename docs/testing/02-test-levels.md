# Test Levels

> **ISTQB Alignment:** This chapter defines test levels (unit, integration, system/E2E)
> and their boundaries for lumehaven. Based on
> [ADR-006](../adr/ADR-006-testing-strategy.md).

## Test Pyramid

```
                         ┌───────────────┐
                         │     E2E       │  Browser + real backend + mock smart home
                         │   (deferred)  │  Robot Framework + Browser Library
                         └───────────────┘
                    ┌─────────────────────────┐
                    │      Integration        │  Full vertical slice with mock adapters
                    │    (API + behavior)     │  Robot Framework + RESTinstance
                    └─────────────────────────┘
               ┌───────────────────────────────────┐
               │           Unit Tests              │  Sociable units, mock external I/O
               │      (fast, focused, many)        │  pytest + pytest-asyncio
               └───────────────────────────────────┘
```

### Ratio Guidance

| Level       | Approximate % | Execution Time   | Feedback Loop           |
| ----------- | ------------- | ---------------- | ----------------------- |
| Unit        | 70-80%        | < 1 second total | Every save (watch mode) |
| Integration | 15-25%        | < 30 seconds     | Pre-commit, CI          |
| E2E         | 5-10%         | < 2 minutes      | CI only                 |

---

## Unit Tests

**Tool:** pytest + pytest-asyncio

**Philosophy:** Sociable units—test components with their real lightweight dependencies,
mock only external I/O.

### What We Mock

| Always Mock                        | Why                        |
| ---------------------------------- | -------------------------- |
| HTTP clients (`httpx.AsyncClient`) | Slow, unreliable, external |
| SSE streams                        | Require real server        |
| Filesystem (config file reads)     | Environment-dependent      |
| Time (`asyncio.sleep`)             | Tests must be fast         |

### What We Don't Mock

| Use Real           | Why                                          |
| ------------------ | -------------------------------------------- |
| `SignalStore`      | Fast, in-memory, tests real pub/sub behavior |
| `Signal` dataclass | No reason to mock a data structure           |
| Pydantic models    | Validation logic is part of the unit         |
| Pure functions     | No dependencies to mock                      |

### Isolation Boundary Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         UNIT TEST BOUNDARY                          │
│                                                                     │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐             │
│  │   Signal    │    │ SignalStore │    │   Config    │             │
│  │  (real)     │◄───│   (real)    │    │  (real)     │             │
│  └─────────────┘    └──────┬──────┘    └──────┬──────┘             │
│                            │                   │                    │
│                            │                   │                    │
│  ┌─────────────────────────┴───────────────────┴──────────────┐    │
│  │                    AdapterManager                          │    │
│  │                       (real)                               │    │
│  └─────────────────────────┬──────────────────────────────────┘    │
│                            │                                        │
├────────────────────────────┼────────────────────────────────────────┤
│                            │           MOCK BOUNDARY                │
│                            ▼                                        │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                   SmartHomeAdapter                          │   │
│  │                      (MOCKED)                               │   │
│  │                                                             │   │
│  │   get_signals() → returns predefined Signal list            │   │
│  │   subscribe_events() → yields predefined events             │   │
│  │   close() → no-op                                           │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### Unit Test Examples

```python
# Good: Uses real SignalStore, mocks adapter protocol
async def test_adapter_manager_loads_signals_on_start(
    mock_adapter: MockAdapter,
    signal_store: SignalStore,  # Real, in-memory
) -> None:
    manager = AdapterManager()
    manager.add(mock_adapter)

    await manager.start_all()

    signals = await signal_store.get_all()
    assert len(signals) == len(mock_adapter.signals)


# Good: Tests OpenHAB parsing with real input, no mocks needed
@pytest.mark.parametrize("raw_state,expected", [
    ("21.5 °C", ("21.5", "°C")),
    ("ON", ("ON", None)),
    ("UNDEF", (None, None)),
])
def test_parse_openhab_state(raw_state: str, expected: tuple) -> None:
    result = parse_state(raw_state)
    assert result == expected


# Bad: Over-mocked, doesn't test real behavior
async def test_store_set_signal_overmocked(
    mock_store: Mock,  # Don't do this
) -> None:
    mock_store.set.return_value = None
    await mock_store.set(some_signal)
    mock_store.set.assert_called_once()  # Tests nothing useful
```

### Async Testing Pattern

All adapter and store tests are async. We use `pytest-asyncio` with
`asyncio_mode = "auto"`:

```python
# No decorator needed with auto mode
async def test_store_publishes_to_subscribers() -> None:
    store = SignalStore()
    received: list[Signal] = []

    async def collector() -> None:
        async for signal in store.subscribe():
            received.append(signal)
            if len(received) >= 2:
                break

    task = asyncio.create_task(collector())
    await store.publish(signal_1)
    await store.publish(signal_2)
    await task

    assert received == [signal_1, signal_2]
```

---

## Integration Tests

**Tool:** Robot Framework + RESTinstance

**Philosophy:** Full vertical slice—test complete data flow from mock smart home through
our API, with human-readable scenarios.

### Scope

Integration tests verify:

1. **API contracts** — Correct status codes, response shapes, headers
2. **Behavior** — State changes propagate correctly through the system
3. **Data flow** — Mock smart home data appears correctly in API responses

### Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                    INTEGRATION TEST BOUNDARY                         │
│                                                                      │
│  ┌────────────────┐         ┌─────────────────────────────────────┐ │
│  │  Robot Tests   │         │         Lumehaven Backend           │ │
│  │                │  HTTP   │  ┌─────────┐  ┌─────────────────┐   │ │
│  │  Given/When/   │────────►│  │   API   │──│  AdapterManager │   │ │
│  │  Then steps    │◄────────│  │ Routes  │  │                 │   │ │
│  │                │         │  └─────────┘  └────────┬────────┘   │ │
│  └────────────────┘         │                        │            │ │
│                             │                        │            │ │
│                             │                ┌───────▼────────┐   │ │
│                             │                │ OpenHABAdapter │   │ │
│                             │                └───────┬────────┘   │ │
│                             └────────────────────────┼────────────┘ │
│                                                      │              │
│                                              HTTP    │              │
│                                                      ▼              │
│                             ┌─────────────────────────────────────┐ │
│                             │         Mock OpenHAB Server         │ │
│                             │                                     │ │
│                             │  - /rest/items → fixture data       │ │
│                             │  - /rest/events → SSE stream        │ │
│                             │  - Controllable via test keywords   │ │
│                             └─────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

### Mock Smart Home Server

The mock OpenHAB server (`tests/integration/mock_openhab/server.py`) provides:

- `/rest/items` — Configurable fixture data from `tests/fixtures/openhab_responses.py`
- `/rest/events/states` — SSE stream for batch state subscriptions
- `/_test/set_item_state` — Trigger state changes and SSE events
- `/_test/configure_failure` — Simulate errors for error handling tests
- `/_test/reset` — Reset to default state between tests

**Implementation:** FastAPI stub—same stack as main app, easy to understand.

### SSE Testing in Integration Tests

SSE testing requires special handling since the REST library doesn't support SSE
streams. We use a custom `SSEKeywords.py` library (`tests/integration/libraries/`) with:

- Synchronous `httpx.Client` with threading for background event reading
- Polling-based synchronization via `/metrics` subscriber count
- `Wait For SSE Event Matching` for reliable event capture with timeout

**Critical synchronization pattern:**

```robot
Connect And Wait For SSE Subscription
    [Documentation]    Connect SSE and wait for subscriber registration.
    Connect SSE Stream    ${LUMEHAVEN_URL}/api/events/signals
    Wait For Lumehaven SSE Subscribers    min_count=1
    # Now safe to trigger events — subscriber is registered
```

This prevents race conditions where events fire before the client is subscribed, which
is essential for CI reliability.

### Example Integration Tests

```robot
*** Settings ***
Library     REST
Library     Collections
Library     libraries/ServerKeywords.py
Library     libraries/SSEKeywords.py
Resource    resources/keywords.resource

Suite Setup       Start Full Backend Stack
Suite Teardown    Stop Integration Test Environment
Test Setup        Reset Test State

*** Test Cases ***
Signal Has Correct Unit From OpenHAB
    [Documentation]    Verify OpenHAB temperature items are normalized.
    [Tags]    signals    smoke
    GET Lumehaven    /api/signals/oh:LivingRoom_Temperature
    Response Status Should Be    200
    Response Key Should Equal    unit    °C

Signal Update Propagates Through SSE
    [Documentation]    Verify signal state changes propagate through SSE stream.
    [Tags]    sse    data-flow
    Connect And Wait For SSE Subscription
    ${event}=    Trigger And Wait For Signal Update    LivingRoom_Temperature    28.5
    SSE Event Should Contain    event    signal
    SSE Event Data Should Contain Key    value    28.5

Backend Returns 503 When OpenHAB Unavailable
    [Documentation]    Verify graceful error handling when adapter fails.
    [Tags]    error-handling
    Configure Mock OpenHAB Failure    status_code=500
    # Health endpoint should report degraded status
    GET Lumehaven    /health
    Response Key Should Equal    status    degraded
```

### Integration Test Markers

```robot
*** Settings ***
Force Tags    integration

# Use tags for filtering:
# robot --include smoke tests/integration/
# robot --exclude slow tests/integration/
```

---

## E2E Tests (Deferred)

**Tool:** Robot Framework + Browser Library

**Status:** Deferred until frontend is stable (per ADR-006).

**Philosophy:** Browser tests against running full stack with mock smart home. Never
test against real smart home systems—they're unreliable and slow.

### Architecture (Future)

```
┌──────────────────────────────────────────────────────────────────────┐
│                       E2E TEST BOUNDARY                              │
│                                                                      │
│  ┌────────────────┐                                                  │
│  │  Browser Tests │                                                  │
│  │  (Playwright)  │                                                  │
│  └───────┬────────┘                                                  │
│          │                                                           │
│          │ Browser automation                                        │
│          ▼                                                           │
│  ┌────────────────┐         ┌─────────────────────────────────────┐ │
│  │    Frontend    │  HTTP   │         Lumehaven Backend           │ │
│  │   (React SPA)  │────────►│                                     │ │
│  │                │◄────────│                                     │ │
│  └────────────────┘   SSE   └──────────────────┬──────────────────┘ │
│                                                │                     │
│                                                │                     │
│                                                ▼                     │
│                             ┌─────────────────────────────────────┐ │
│                             │         Mock OpenHAB Server         │ │
│                             └─────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

### E2E Test Principles (Defined Now)

1. **Mock at external boundary** — Real frontend, real backend, mock smart home
2. **Test user journeys** — Not individual components
3. **Minimal coverage** — Only critical paths (5-10% of tests)
4. **CI-friendly** — Must run without hardware, in containers

### Example E2E Test (Future)

```robot
*** Test Cases ***
User Sees Live Temperature Update
    [Documentation]    Temperature changes in smart home appear in dashboard
    [Tags]    e2e    critical

    # Given
    Mock OpenHAB Has Item    Temp_Living    Number:Temperature    20.0 °C
    Open Browser To Dashboard

    # When
    Mock OpenHAB Updates Item    Temp_Living    22.5 °C

    # Then
    Wait Until Element Contains    css=[data-signal="oh:Temp_Living"]    22.5
```

---

## Level Boundaries Summary

| Aspect              | Unit                          | Integration                        | E2E                              |
| ------------------- | ----------------------------- | ---------------------------------- | -------------------------------- |
| **What's real**     | Store, models, pure functions | Full backend + mock adapter source | Full stack + mock adapter source |
| **What's mocked**   | HTTP, SSE, filesystem, time   | Smart home API only                | Smart home API only              |
| **Execution**       | pytest                        | Robot Framework                    | Robot Framework + Browser        |
| **Speed target**    | < 1s total                    | < 30s                              | < 2min                           |
| **When to run**     | Every change                  | Pre-commit, CI                     | CI only                          |
| **Failure meaning** | Logic bug in component        | Contract/integration bug           | User-visible regression          |

---

## References

- [ADR-006: Testing Strategy](../adr/ADR-006-testing-strategy.md) — Original decision
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Robot Framework REST Library](https://github.com/asyrjasalo/RESTinstance) — HTTP
  testing
- [sse-starlette](https://github.com/sysid/sse-starlette) — SSE support for FastAPI
- [Robot Framework Browser Library](https://robotframework-browser.org/) — E2E (future)
