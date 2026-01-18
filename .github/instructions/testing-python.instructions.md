---
description: 'Python testing - pytest and Robot Framework patterns'
applyTo: 'packages/backend/tests/**/*.py, **/*.robot'
---

# Testing Instructions

## Test Strategy (ADR-006)

| Layer       | Tool                           | Location             |
| ----------- | ------------------------------ | -------------------- |
| Unit        | pytest + pytest-asyncio        | `tests/unit/`        |
| Integration | Robot Framework + RESTinstance | `tests/integration/` |

## Test Structure

### AAA Pattern

Follow the Arrange-Act-Assert pattern:

```python
def test_parse_value_extracts_unit():
    # Arrange
    raw_value = "21.5 °C"

    # Act
    result = parse_value(raw_value)

    # Assert
    assert result == ("21.5", "°C")
```

### Naming Convention

Name tests: `test_<method>_<scenario>_<expected>`

```python
def test_parse_value_with_percentage_returns_tuple(): ...
def test_get_signal_with_invalid_id_raises_not_found(): ...
def test_adapter_connect_when_offline_retries(): ...
```

### Assertions

Use specific assertions, not generic truthy checks:

```python
# ❌ Bad - vague assertion
assert result

# ✅ Good - specific assertion
assert result.value == "21.5"
assert result.unit == "°C"
```

### Edge Cases

Always test critical edge cases:

- Empty inputs and None values
- Invalid data types
- Boundary conditions
- Error conditions and exceptions

## pytest Patterns

```python
# Use pytest fixtures for shared setup
@pytest.fixture
def sample_signal():
    return Signal(id="temp_1", value="21.5", unit="°C")

# Async tests need the marker
@pytest.mark.asyncio
async def test_async_operation():
    result = await some_async_function()
    assert result is not None

# Use parametrize for multiple cases
@pytest.mark.parametrize("input,expected", [
    ("21.5 °C", ("21.5", "°C")),
    ("100 %", ("100", "%")),
])
def test_parse_value(input, expected):
    assert parse_value(input) == expected
```

## Robot Framework Patterns

```robot
*** Settings ***
Library    RESTinstance

*** Test Cases ***
Get All Signals Returns List
    GET    /api/signals
    Integer    response status    200
    Array    response body
```

## Test Organization

- One test file per module: `test_signal.py` tests `signal.py`
- Fixtures in `conftest.py`
- Integration tests focus on API contracts, not implementation
