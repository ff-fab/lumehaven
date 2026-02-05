"""Unit tests for /health endpoint.

Test Techniques Used:
- State Transition Testing: Health status (healthy/degraded) based on
  signal count, adapter connection state, and adapter presence
- Specification-based Testing: Response structure and field values

Coverage Target: Medium Risk (api/routes.py)
- Line Coverage: ≥80%
- Branch Coverage: ≥75%
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from httpx import AsyncClient

from lumehaven.state.store import SignalStore
from tests.fixtures.signals import create_signal
from tests.unit.api.conftest import MockAdapter, MockAdapterManager, MockAdapterState

if TYPE_CHECKING:
    pass


class TestHealthStatus:
    """Tests for health status determination logic.

    Technique: State Transition Testing
    States: healthy ↔ degraded based on conditions
    Conditions: signal_count > 0, has_adapters, all_connected
    """

    async def test_healthy_with_signals_and_connected_adapters(
        self,
        async_client: AsyncClient,
        signal_store: SignalStore,
        mock_adapter_manager: MockAdapterManager,
        mock_adapter_factory: Callable[..., MockAdapter],
    ) -> None:
        """Returns 'healthy' when signals loaded and all adapters connected.

        Condition: signal_count > 0 AND has_adapters AND all_connected → healthy
        """
        # Arrange — add signals to store
        await signal_store.set(create_signal(id="test:temp"))

        # Arrange — add connected adapter
        adapter = mock_adapter_factory(_name="openhab", _adapter_type="openhab")
        mock_adapter_manager.states["openhab"] = MockAdapterState(
            adapter=adapter, connected=True
        )

        # Act
        response = await async_client.get("/health")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    async def test_degraded_with_no_signals(
        self,
        async_client: AsyncClient,
        mock_adapter_manager: MockAdapterManager,
        mock_adapter_factory: Callable[..., MockAdapter],
    ) -> None:
        """Returns 'degraded' when signal_count is 0.

        Condition: signal_count == 0 → degraded (regardless of adapters)
        """
        # Arrange — no signals in store, but adapter connected
        adapter = mock_adapter_factory(_name="openhab", _adapter_type="openhab")
        mock_adapter_manager.states["openhab"] = MockAdapterState(
            adapter=adapter, connected=True
        )

        # Act
        response = await async_client.get("/health")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["signal_count"] == 0

    async def test_degraded_with_no_adapters(
        self,
        async_client: AsyncClient,
        signal_store: SignalStore,
    ) -> None:
        """Returns 'degraded' when no adapters are registered.

        Condition: has_adapters == False → degraded
        """
        # Arrange — signals exist but no adapters
        await signal_store.set(create_signal(id="test:temp"))
        # mock_adapter_manager.states is empty by default

        # Act
        response = await async_client.get("/health")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["adapters"] == []

    async def test_degraded_with_disconnected_adapter(
        self,
        async_client: AsyncClient,
        signal_store: SignalStore,
        mock_adapter_manager: MockAdapterManager,
        mock_adapter_factory: Callable[..., MockAdapter],
    ) -> None:
        """Returns 'degraded' when any adapter is disconnected.

        Condition: all_connected == False → degraded
        """
        # Arrange — signals and adapter, but adapter disconnected
        await signal_store.set(create_signal(id="test:temp"))

        adapter = mock_adapter_factory(_name="openhab", _adapter_type="openhab")
        mock_adapter_manager.states["openhab"] = MockAdapterState(
            adapter=adapter,
            connected=False,  # Disconnected!
        )

        # Act
        response = await async_client.get("/health")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"

    async def test_degraded_when_one_of_multiple_adapters_disconnected(
        self,
        async_client: AsyncClient,
        signal_store: SignalStore,
        mock_adapter_manager: MockAdapterManager,
        mock_adapter_factory: Callable[..., MockAdapter],
    ) -> None:
        """Returns 'degraded' if any adapter in multi-adapter setup is disconnected.

        Condition: Multiple adapters, one disconnected → degraded
        """
        # Arrange
        await signal_store.set(create_signal(id="test:temp"))

        connected_adapter = mock_adapter_factory(
            _name="openhab", _adapter_type="openhab"
        )
        disconnected_adapter = mock_adapter_factory(
            _name="homeassistant", _adapter_type="hass"
        )

        mock_adapter_manager.states["openhab"] = MockAdapterState(
            adapter=connected_adapter, connected=True
        )
        mock_adapter_manager.states["homeassistant"] = MockAdapterState(
            adapter=disconnected_adapter, connected=False
        )

        # Act
        response = await async_client.get("/health")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"


class TestHealthResponse:
    """Tests for health response structure and fields.

    Technique: Specification-based Testing — verifying response contract.
    """

    async def test_returns_signal_count(
        self,
        async_client: AsyncClient,
        signal_store: SignalStore,
    ) -> None:
        """Health response includes correct signal_count."""
        # Arrange — add 3 signals
        for i in range(3):
            await signal_store.set(create_signal(id=f"test:sig_{i}"))

        # Act
        response = await async_client.get("/health")

        # Assert
        data = response.json()
        assert data["signal_count"] == 3

    async def test_returns_subscriber_count(
        self,
        async_client: AsyncClient,
        signal_store: SignalStore,
    ) -> None:
        """Health response includes subscriber_count from store."""
        # Arrange — no subscribers initially
        # Act
        response = await async_client.get("/health")

        # Assert
        data = response.json()
        assert data["subscriber_count"] == 0

    async def test_returns_adapter_list_with_status(
        self,
        async_client: AsyncClient,
        mock_adapter_manager: MockAdapterManager,
        mock_adapter_factory: Callable[..., MockAdapter],
    ) -> None:
        """Health response includes adapter list with name, type, connected."""
        # Arrange
        adapter = mock_adapter_factory(_name="openhab-main", _adapter_type="openhab")
        mock_adapter_manager.states["openhab-main"] = MockAdapterState(
            adapter=adapter, connected=True
        )

        # Act
        response = await async_client.get("/health")

        # Assert
        data = response.json()
        assert len(data["adapters"]) == 1
        adapter_status = data["adapters"][0]
        assert adapter_status["name"] == "openhab-main"
        assert adapter_status["type"] == "openhab"
        assert adapter_status["connected"] is True

    async def test_returns_multiple_adapters(
        self,
        async_client: AsyncClient,
        mock_adapter_manager: MockAdapterManager,
        mock_adapter_factory: Callable[..., MockAdapter],
    ) -> None:
        """Health response lists all registered adapters."""
        # Arrange — two adapters
        adapter1 = mock_adapter_factory(_name="openhab", _adapter_type="openhab")
        adapter2 = mock_adapter_factory(_name="hass", _adapter_type="homeassistant")

        mock_adapter_manager.states["openhab"] = MockAdapterState(
            adapter=adapter1, connected=True
        )
        mock_adapter_manager.states["hass"] = MockAdapterState(
            adapter=adapter2, connected=False
        )

        # Act
        response = await async_client.get("/health")

        # Assert
        data = response.json()
        assert len(data["adapters"]) == 2
        adapter_names = {a["name"] for a in data["adapters"]}
        assert adapter_names == {"openhab", "hass"}


class TestHealthGracefulDegradation:
    """Tests for graceful handling when adapter_manager is missing.

    Technique: Error Guessing — anticipating edge case during startup.
    """

    async def test_handles_missing_adapter_manager(
        self,
        signal_store: SignalStore,
    ) -> None:
        """Returns degraded status when adapter_manager not set on app.state.

        This can happen during early startup before adapters are initialized.
        """
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        from lumehaven.api.routes import router as routes_router

        # Arrange — app WITHOUT adapter_manager on state
        app = FastAPI()
        app.include_router(routes_router)
        app.dependency_overrides[get_signal_store] = lambda: signal_store
        # Note: NOT setting app.state.adapter_manager

        # Act
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/health")

        # Assert — should not crash, returns degraded
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["adapters"] == []


# Import needed for test above
from lumehaven.state.store import get_signal_store  # noqa: E402
