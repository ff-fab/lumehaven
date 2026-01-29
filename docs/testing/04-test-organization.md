# Test Organization

> **Scope:** File structure, naming conventions, fixtures, and markers for lumehaven
> tests. Follows pytest idioms and Python community standards.

## Directory Structure

### Mirrored Source Layout

Test files mirror the source structure for discoverability:

```
packages/backend/
├── src/
│   └── lumehaven/
│       ├── __init__.py
│       ├── config.py
│       ├── main.py
│       ├── adapters/
│       │   ├── __init__.py
│       │   ├── manager.py
│       │   ├── protocol.py
│       │   └── openhab/
│       │       ├── __init__.py
│       │       ├── adapter.py
│       │       └── units.py
│       ├── api/
│       │   ├── __init__.py
│       │   ├── routes.py
│       │   └── sse.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── exceptions.py
│       │   └── signal.py
│       └── state/
│           ├── __init__.py
│           └── store.py
│
└── tests/
    ├── conftest.py                    # Shared fixtures (signal_factory, etc.)
    ├── fixtures/
    │   ├── __init__.py
    │   ├── openhab_responses.py       # Mock API response data
    │   └── signals.py                 # Test signal factories
    │
    ├── unit/
    │   ├── conftest.py                # Unit-specific fixtures (mock_adapter)
    │   ├── test_config.py             # ← mirrors config.py
    │   ├── adapters/
    │   │   ├── conftest.py            # Adapter test fixtures
    │   │   ├── test_manager.py        # ← mirrors adapters/manager.py
    │   │   └── openhab/
    │   │       ├── test_adapter.py    # ← mirrors adapters/openhab/adapter.py
    │   │       └── test_units.py      # ← mirrors adapters/openhab/units.py
    │   ├── api/
    │   │   ├── test_routes.py
    │   │   └── test_sse.py
    │   ├── core/
    │   │   └── test_signal.py
    │   └── state/
    │       └── test_store.py
    │
    └── integration/
        ├── conftest.py                # Integration fixtures (server startup)
        ├── api_tests.robot
        └── mock_openhab/              # Mock OpenHAB server for integration
            ├── __init__.py
            └── server.py
```

### Rationale

- **Mirrored structure** makes it obvious which tests cover which code
- **Hierarchical conftest.py** scopes fixtures appropriately
- **fixtures/ directory** for reusable test data (imported, not auto-discovered)
- **Separate integration/** keeps slow tests isolated

---

## Naming Conventions

### Test Files

| Pattern             | Example               | When to Use                        |
| ------------------- | --------------------- | ---------------------------------- |
| `test_<module>.py`  | `test_manager.py`     | Standard—mirrors source module     |
| `test_<feature>.py` | `test_retry_logic.py` | When testing cross-cutting feature |

### Test Functions

**Pattern:** `test_<unit>_<behavior>_<condition>` (descriptive)

```python
# Good: Descriptive, self-documenting in output
def test_adapter_manager_schedules_retry_when_connection_fails() -> None: ...
def test_signal_store_publishes_to_all_subscribers() -> None: ...
def test_parse_state_extracts_unit_from_quantity_type() -> None: ...

# Bad: Too short, need to read code to understand
def test_retry() -> None: ...
def test_publish() -> None: ...

# Bad: BDD-style, verbose without adding clarity
def test_given_failed_connection_when_start_then_retry() -> None: ...
```

### Test Classes

**Pattern:** `Test<Unit>` groups related tests

```python
class TestAdapterManagerLifecycle:
    """Tests for adapter startup, shutdown, and reconnection."""

    async def test_start_all_loads_signals_from_each_adapter(self) -> None: ...
    async def test_start_all_creates_sync_task_for_each_adapter(self) -> None: ...
    async def test_stop_all_cancels_sync_tasks(self) -> None: ...


class TestAdapterManagerRetry:
    """Tests for retry logic with exponential backoff."""

    async def test_schedules_retry_when_initial_connection_fails(self) -> None: ...
    async def test_retry_delay_increases_exponentially(self) -> None: ...
    async def test_retry_delay_caps_at_maximum(self) -> None: ...
```

### When to Use Classes vs Functions

| Use Classes When                    | Use Functions When        |
| ----------------------------------- | ------------------------- |
| Tests share setup/fixtures          | Tests are independent     |
| Testing one method/behavior deeply  | Testing utility functions |
| Logical grouping aids readability   | Few tests for a module    |
| Multiple related parametrized tests | One-off edge case tests   |

---

## Fixtures

### Fixture Hierarchy

```
tests/conftest.py              # Shared across ALL tests
    │
    ├── tests/unit/conftest.py          # Unit test specific
    │   │
    │   └── tests/unit/adapters/conftest.py   # Adapter unit tests
    │
    └── tests/integration/conftest.py   # Integration specific
```

### Fixture Scopes

| Scope                | Lifetime        | Use Case                            |
| -------------------- | --------------- | ----------------------------------- |
| `function` (default) | Per test        | Most fixtures—fresh state each test |
| `class`              | Per test class  | Shared setup within a class         |
| `module`             | Per test file   | Expensive setup shared across file  |
| `session`            | Entire test run | Very expensive (e.g., database)     |

```python
@pytest.fixture
def signal() -> Signal:
    """Fresh signal for each test (function scope)."""
    return Signal(id="test:signal", value="42", unit="°C", label="Test")


@pytest.fixture(scope="module")
def mock_openhab_responses() -> dict[str, Any]:
    """Loaded once per test file (expensive I/O)."""
    return json.loads(FIXTURES_PATH.read_text())
```

### Fixture Location Guidelines

| Fixture               | Location                        | Rationale                     |
| --------------------- | ------------------------------- | ----------------------------- |
| `signal_factory`      | `tests/conftest.py`             | Used by unit and integration  |
| `mock_adapter`        | `tests/unit/conftest.py`        | Only unit tests mock adapters |
| `signal_store`        | `tests/unit/conftest.py`        | Unit tests use real store     |
| `running_backend`     | `tests/integration/conftest.py` | Only integration needs server |
| `mock_openhab_server` | `tests/integration/conftest.py` | Only integration needs mock   |

### Example Fixtures

```python
# tests/conftest.py — Shared fixtures
import pytest
from lumehaven.core.signal import Signal


@pytest.fixture
def signal_factory() -> Callable[..., Signal]:
    """Factory for creating test signals with defaults."""
    def _create(
        id: str = "test:signal",
        value: str = "0",
        unit: str | None = None,
        label: str = "Test Signal",
    ) -> Signal:
        return Signal(id=id, value=value, unit=unit, label=label)
    return _create


@pytest.fixture
def sample_signals(signal_factory) -> list[Signal]:
    """Standard set of signals for tests."""
    return [
        signal_factory(id="oh:temp", value="21.5", unit="°C", label="Temperature"),
        signal_factory(id="oh:light", value="ON", label="Kitchen Light"),
        signal_factory(id="oh:humidity", value="45", unit="%", label="Humidity"),
    ]
```

```python
# tests/unit/conftest.py — Unit test fixtures
import pytest
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

from lumehaven.adapters.protocol import SmartHomeAdapter
from lumehaven.core.signal import Signal
from lumehaven.state.store import SignalStore


@pytest.fixture
def signal_store() -> SignalStore:
    """Real in-memory signal store for unit tests."""
    return SignalStore()


@pytest.fixture
def mock_adapter(sample_signals: list[Signal]) -> SmartHomeAdapter:
    """Mock adapter implementing the protocol."""
    adapter = AsyncMock(spec=SmartHomeAdapter)
    adapter.name = "mock"
    adapter.adapter_type = "mock"
    adapter.get_signals = AsyncMock(return_value=sample_signals)
    adapter.subscribe_events = AsyncMock(return_value=async_signal_generator([]))
    adapter.close = AsyncMock()
    return adapter


async def async_signal_generator(
    signals: list[Signal],
) -> AsyncIterator[Signal]:
    """Helper to create async generator from list."""
    for signal in signals:
        yield signal
```

```python
# tests/integration/conftest.py — Integration fixtures
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def mock_openhab_server():
    """Start mock OpenHAB server for integration tests."""
    from tests.integration.mock_openhab.server import create_mock_server

    server = create_mock_server()
    server.start()
    yield server
    server.stop()


@pytest.fixture(scope="module")
def test_client(mock_openhab_server) -> TestClient:
    """FastAPI test client with mock adapter configured."""
    from lumehaven.main import create_app

    app = create_app(openhab_url=mock_openhab_server.url)
    return TestClient(app)
```

---

## Markers

### Standard Markers

```python
# pyproject.toml
[tool.pytest.ini_options]
markers = [
    "unit: Unit tests (fast, no external dependencies)",
    "integration: Integration tests (require mock servers)",
    "slow: Tests that take > 1 second",
    "asyncio: Async tests (auto-applied by pytest-asyncio)",
]
```

### Applying Markers

```python
# File-level marker (all tests in file)
pytestmark = pytest.mark.unit


# Class-level marker
@pytest.mark.unit
class TestSignalStore:
    ...


# Function-level marker
@pytest.mark.slow
async def test_adapter_reconnection_with_backoff() -> None:
    ...


# Multiple markers
@pytest.mark.unit
@pytest.mark.slow
async def test_large_signal_batch_processing() -> None:
    ...
```

### Running by Marker

```bash
# Run only unit tests
uv run pytest -m unit

# Run everything except slow tests
uv run pytest -m "not slow"

# Run integration tests only
uv run pytest -m integration
```

---

## Parametrization

### Basic Parametrization

```python
@pytest.mark.parametrize("raw_state,expected_value,expected_unit", [
    ("21.5 °C", "21.5", "°C"),
    ("ON", "ON", None),
    ("UNDEF", None, None),
    ("NULL", None, None),
    ("100 %", "100", "%"),
])
def test_parse_state(
    raw_state: str,
    expected_value: str | None,
    expected_unit: str | None,
) -> None:
    value, unit = parse_state(raw_state)
    assert value == expected_value
    assert unit == expected_unit
```

### Parametrization with IDs

```python
@pytest.mark.parametrize("item_type,expected", [
    pytest.param("Switch", None, id="switch-no-unit"),
    pytest.param("Dimmer", "%", id="dimmer-percent"),
    pytest.param("Number:Temperature", "°C", id="temperature-celsius"),
    pytest.param("Number:Power", "W", id="power-watts"),
], ids=str)
def test_default_unit_for_item_type(item_type: str, expected: str | None) -> None:
    ...
```

### Fixture Parametrization

```python
@pytest.fixture(params=["openhab", "homeassistant"])
def adapter_type(request) -> str:
    """Run test once for each adapter type."""
    return request.param


def test_adapter_implements_protocol(adapter_type: str) -> None:
    """Verify all adapter types implement SmartHomeAdapter protocol."""
    ...
```

---

## Async Testing

### Configuration

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

With `asyncio_mode = "auto"`, async test functions are automatically detected—no
decorator needed:

```python
# No @pytest.mark.asyncio needed with auto mode
async def test_store_publishes_signal() -> None:
    store = SignalStore()
    received = []

    async def collector():
        async for signal in store.subscribe():
            received.append(signal)
            break

    task = asyncio.create_task(collector())
    await asyncio.sleep(0.01)  # Let subscriber start
    await store.publish(Signal(id="test", value="1", label="Test"))
    await task

    assert len(received) == 1
```

### Async Fixtures

```python
@pytest.fixture
async def connected_adapter(mock_adapter: SmartHomeAdapter) -> SmartHomeAdapter:
    """Adapter that has completed initial connection."""
    await mock_adapter.connect()
    yield mock_adapter
    await mock_adapter.close()
```

---

## Test Data Management

### fixtures/ Directory

Store test data in importable modules, not conftest.py:

```python
# tests/fixtures/openhab_responses.py
"""Mock OpenHAB API response data."""

ITEMS_RESPONSE = [
    {
        "name": "Temperature_Living",
        "type": "Number:Temperature",
        "state": "21.5 °C",
        "label": "Living Room Temperature",
    },
    {
        "name": "Light_Kitchen",
        "type": "Switch",
        "state": "ON",
        "label": "Kitchen Light",
    },
]

SSE_EVENTS = [
    {
        "type": "ItemStateChangedEvent",
        "payload": '{"value": "22.0 °C"}',
    },
]
```

```python
# tests/fixtures/signals.py
"""Pre-built Signal instances for tests."""

from lumehaven.core.signal import Signal

TEMPERATURE_SIGNAL = Signal(
    id="oh:Temperature_Living",
    value="21.5",
    unit="°C",
    label="Living Room Temperature",
)

SWITCH_SIGNAL = Signal(
    id="oh:Light_Kitchen",
    value="ON",
    unit=None,
    label="Kitchen Light",
)
```

### Usage in Tests

```python
from tests.fixtures.openhab_responses import ITEMS_RESPONSE
from tests.fixtures.signals import TEMPERATURE_SIGNAL


def test_parse_items_response() -> None:
    signals = parse_items(ITEMS_RESPONSE)
    assert signals[0] == TEMPERATURE_SIGNAL
```

---

## Anti-Patterns to Avoid

### ❌ Over-Mocking

```python
# Bad: Mocks everything, tests nothing real
def test_store_set(mock_store):
    mock_store.set.return_value = None
    mock_store.set(signal)
    mock_store.set.assert_called_once()  # Proves nothing
```

### ❌ Test Interdependence

```python
# Bad: Tests depend on execution order
class TestStore:
    def test_set(self, store):
        store.set(signal)  # Side effect

    def test_get(self, store):
        result = store.get("id")  # Depends on test_set running first!
```

### ❌ Assertions in Fixtures

```python
# Bad: Fixture does testing
@pytest.fixture
def validated_signal():
    signal = Signal(...)
    assert signal.id  # Don't assert in fixtures
    return signal
```

### ❌ Magic Numbers

```python
# Bad: Magic values without context
def test_backoff():
    assert delay == 5.0  # Why 5.0?

# Good: Named constants or documented
def test_backoff():
    assert delay == INITIAL_RETRY_DELAY  # Clear reference
```

---

## References

- [pytest Good Practices](https://docs.pytest.org/en/stable/explanation/goodpractices.html)
- [pytest Fixtures](https://docs.pytest.org/en/stable/how-to/fixtures.html)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [CPython Test Guide](https://devguide.python.org/testing/)
