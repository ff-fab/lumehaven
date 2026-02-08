# Add a New Adapter

!!! abstract "Goal"
    Implement a new smart home adapter (e.g., Home Assistant) by following the
    `SmartHomeAdapter` Protocol, registering it in the factory, and adding tests.

## Overview

lumehaven uses a Protocol-based adapter system (see
[Adapter System](../explanation/adapter-system.md)). Adding a new adapter requires four
steps:

1. Implement the `SmartHomeAdapter` Protocol
2. Register the adapter in the factory
3. Add a configuration model
4. Write tests

This guide uses a fictional **Home Assistant** adapter as the running example.

## Step 1: Implement the Protocol

Create the adapter package:

```
packages/backend/src/lumehaven/adapters/homeassistant/
├── __init__.py       # Factory registration
└── adapter.py        # Adapter implementation
```

Your adapter class must satisfy the
[`SmartHomeAdapter` Protocol](../reference/api/adapters.md). Here's the complete
skeleton with all required properties and methods:

```python title="adapters/homeassistant/adapter.py"
"""Home Assistant adapter — connects to the Home Assistant API."""

from collections.abc import AsyncIterator
from dataclasses import dataclass, field

import httpx

from lumehaven.core.signal import Signal


@dataclass
class HomeAssistantAdapter:
    """Adapter for Home Assistant smart home system.

    Connects to the Home Assistant REST API and WebSocket API
    for real-time state updates.
    """

    base_url: str
    token: str
    _name: str = "homeassistant"
    _prefix: str = "ha"
    _client: httpx.AsyncClient | None = field(default=None, repr=False)

    # --- Properties (required by Protocol) ---

    @property
    def name(self) -> str:
        """Unique identifier for this adapter instance."""
        return self._name

    @property
    def adapter_type(self) -> str:
        """Must match the 'type' discriminator in config."""
        return "homeassistant"

    @property
    def prefix(self) -> str:
        """Short prefix for signal ID namespacing (e.g., 'ha')."""
        return self._prefix

    # --- Data access ---

    async def get_signals(self) -> dict[str, Signal]:
        """Fetch all entity states from Home Assistant.

        Called on startup. Must return a dict mapping signal IDs
        to Signal objects.

        Raises:
            SmartHomeConnectionError: If the API is unreachable.
        """
        client = await self._get_client()
        response = await client.get("/api/states")
        response.raise_for_status()

        signals: dict[str, Signal] = {}
        for entity in response.json():
            signal = self._entity_to_signal(entity)
            signals[signal.id] = signal
        return signals

    async def get_signal(self, signal_id: str) -> Signal | None:
        """Fetch a single entity by signal ID.

        Returns None if the entity doesn't exist.
        """
        # Strip prefix to get entity_id
        entity_id = signal_id.removeprefix(f"{self._prefix}:")
        client = await self._get_client()
        response = await client.get(f"/api/states/{entity_id}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return self._entity_to_signal(response.json())

    # --- Real-time events ---

    async def subscribe_events(self) -> AsyncIterator[Signal]:
        """Subscribe to state change events via WebSocket.

        Yields Signal objects whenever an entity state changes.
        The AdapterManager iterates this and publishes to the store.
        """
        # 1. Connect to ws://<url>/api/websocket and authenticate
        # 2. Subscribe to state_changed events
        # 3. Yield signals as they arrive
        async for message in self._listen_websocket():
            yield self._entity_to_signal(message)

    # --- Lifecycle ---

    def is_connected(self) -> bool:
        """Check if the HTTP client exists (lightweight, no network call)."""
        return self._client is not None and not self._client.is_closed

    async def close(self) -> None:
        """Close the HTTP client. Must be idempotent."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # --- Private helpers ---

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazily create the HTTP client with auth headers."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"Authorization": f"Bearer {self.token}"},
            )
        return self._client

    def _entity_to_signal(self, entity: dict) -> Signal:
        """Convert a Home Assistant entity dict to a Signal.

        This is where normalization happens — adapt the raw API
        format to lumehaven's universal Signal model.
        """
        entity_id = entity["entity_id"]
        return Signal(
            id=f"{self._prefix}:{entity_id}",
            value=str(entity.get("state", "")),
            unit=entity.get("attributes", {}).get("unit_of_measurement", ""),
            label=entity.get("attributes", {}).get("friendly_name", entity_id),
        )
```

!!! tip "Key Protocol requirements"
    - **`name`**, **`adapter_type`**, **`prefix`** are *properties*, not plain
      attributes. Use `@property` or a dataclass field won't satisfy the Protocol.
    - **`get_signals()`** and **`get_signal()`** are `async`.
    - **`subscribe_events()`** returns an `AsyncIterator[Signal]` — typically
      implemented as an `async def` generator with `yield`.
    - **`is_connected()`** is *synchronous* — it checks internal state, never makes
      network calls.
    - **`close()`** must be idempotent (safe to call multiple times).

## Step 2: Register in the Factory

Each adapter module provides a `_register()` function that adds its factory to the
global `ADAPTER_FACTORIES` registry. This follows the
**Open/Closed Principle** — no existing code needs modification.

```python title="adapters/homeassistant/__init__.py"
"""Home Assistant adapter — connects to Home Assistant."""

from lumehaven.adapters.homeassistant.adapter import HomeAssistantAdapter
from lumehaven.adapters.protocol import SmartHomeAdapter
from lumehaven.config import HomeAssistantAdapterConfig

__all__ = ["HomeAssistantAdapter"]


def _register() -> None:
    """Register the Home Assistant adapter factory."""
    from lumehaven.adapters import ADAPTER_FACTORIES

    def create_ha_adapter(config: HomeAssistantAdapterConfig) -> SmartHomeAdapter:
        return HomeAssistantAdapter(
            base_url=config.url,
            token=config.token,
            _name=config.name,
            _prefix=config.prefix,
        )

    ADAPTER_FACTORIES["homeassistant"] = create_ha_adapter
```

Then trigger registration in the adapters package init:

```python title="adapters/__init__.py (add these lines)"
from lumehaven.adapters import homeassistant as _homeassistant
_homeassistant._register()
```

!!! info "Why deferred registration?"
    The `_register()` function imports `ADAPTER_FACTORIES` inside its body, not at
    module level. This avoids circular imports — the adapter module can be imported
    before the registry dict exists, and registration happens explicitly after everything
    is defined.

## Step 3: Add Configuration

A config model already exists for Home Assistant in
[config.py](../reference/api/config.md) — `HomeAssistantAdapterConfig` with fields
`type`, `name`, `prefix`, `url`, and `token`. If your adapter needs different fields,
add a new Pydantic `BaseModel`:

```python title="config.py (pattern for a new adapter type)"
class MyAdapterConfig(BaseModel):
    """Configuration for MySystem adapter."""

    type: Literal["mysystem"] = "mysystem"   # Discriminator value
    name: str = "mysystem"
    prefix: str = "ms"
    url: str = "http://localhost:9000"
    # Add adapter-specific fields here
```

Then add your config to the discriminated union:

```python title="config.py"
AdapterConfig = Annotated[
    OpenHABAdapterConfig | HomeAssistantAdapterConfig | MyAdapterConfig,
    Field(discriminator="type"),
]
```

The `type` field acts as a discriminator — Pydantic uses it to determine which model
validates the YAML entry. Users just set `type: mysystem` in their config file.

For all configuration options, see the
[Configuration Reference](../reference/configuration.md).

## Step 4: Write Tests

New adapters inherit the **Critical** coverage threshold (90% line, 85% branch) — no
configuration changes needed. The threshold applies automatically to any subdirectory
under `adapters/`.

### Unit Tests

Create the test structure mirroring the source:

```
packages/backend/tests/unit/adapters/homeassistant/
├── conftest.py                  # Fixtures (mock responses, test signals)
├── test_adapter.py              # Adapter method tests
└── test_adapter_protocol.py     # Protocol compliance
```

#### Protocol Compliance Test

Verify your adapter satisfies the Protocol at runtime:

```python title="test_adapter_protocol.py"
"""Verify HomeAssistantAdapter satisfies SmartHomeAdapter Protocol."""

from lumehaven.adapters.homeassistant.adapter import HomeAssistantAdapter
from lumehaven.adapters.protocol import SmartHomeAdapter


class TestProtocolCompliance:
    """Protocol conformance checks."""

    def test_isinstance_check(self) -> None:
        """Adapter passes runtime_checkable isinstance check."""
        adapter = HomeAssistantAdapter(
            base_url="http://test:8123",
            token="test-token",
        )
        assert isinstance(adapter, SmartHomeAdapter)
```

#### Adapter Method Tests

Mock HTTP responses and verify signal conversion:

```python title="test_adapter.py"
"""Unit tests for HomeAssistantAdapter."""

import httpx
import pytest

from lumehaven.adapters.homeassistant.adapter import HomeAssistantAdapter
from lumehaven.core.signal import Signal


@pytest.fixture
def adapter() -> HomeAssistantAdapter:
    return HomeAssistantAdapter(
        base_url="http://test:8123",
        token="test-token",
    )


class TestGetSignals:
    """Tests for get_signals() — initial state load."""

    async def test_returns_signals_from_api(
        self, adapter: HomeAssistantAdapter, httpx_mock
    ) -> None:
        """Signals are correctly built from HA entity list."""
        httpx_mock.add_response(
            url="http://test:8123/api/states",
            json=[
                {
                    "entity_id": "sensor.temperature",
                    "state": "21.5",
                    "attributes": {
                        "unit_of_measurement": "°C",
                        "friendly_name": "Living Room",
                    },
                },
            ],
        )

        signals = await adapter.get_signals()

        assert "ha:sensor.temperature" in signals
        signal = signals["ha:sensor.temperature"]
        assert signal == Signal(
            id="ha:sensor.temperature",
            value="21.5",
            unit="°C",
            label="Living Room",
        )
```

### Integration Tests

Integration tests use Robot Framework with a mock Home Assistant server. Follow the
patterns in the existing OpenHAB integration tests.

For testing conventions and coverage thresholds, see [Testing](../testing/00-index.md).

## Reference

- [SmartHomeAdapter Protocol API](../reference/api/adapters.md) — full interface docs
- [Adapter System explanation](../explanation/adapter-system.md) — architecture and
  design patterns
- [Configuration Reference](../reference/configuration.md) — all config options
- [Testing strategy](../testing/00-index.md) — coverage thresholds and organization
- [OpenHAB adapter](../reference/api/adapters.md) — reference implementation
- [Testing guide](testing.md)
