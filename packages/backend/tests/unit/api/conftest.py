"""Fixtures for API unit tests.

Provides test client setup, isolated SignalStore instances, and mock
AdapterManager for testing route handlers without production dependencies.

Key Fixtures:
- signal_store: Isolated SignalStore (not the singleton)
- app: FastAPI app with dependency overrides
- async_client: httpx AsyncClient for async endpoint testing
- mock_adapter_manager: Configurable mock for /health endpoint
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from lumehaven.api.routes import router as routes_router
from lumehaven.api.sse import router as sse_router
from lumehaven.state.store import SignalStore, get_signal_store

if TYPE_CHECKING:
    from collections.abc import Callable


# =============================================================================
# Mock AdapterManager — Minimal mock for /health endpoint
# =============================================================================


@dataclass
class MockAdapterState:
    """Mock adapter state for testing /health endpoint."""

    adapter: MockAdapter
    connected: bool = True


@dataclass
class MockAdapter:
    """Minimal mock adapter with just the properties /health needs."""

    _name: str = "mock-adapter"
    _adapter_type: str = "mock"

    @property
    def name(self) -> str:
        """Adapter name."""
        return self._name

    @property
    def adapter_type(self) -> str:
        """Adapter type identifier."""
        return self._adapter_type


@dataclass
class MockAdapterManager:
    """Mock AdapterManager with configurable states for /health testing.

    Only implements the `states` dict that /health endpoint accesses.
    """

    states: dict[str, MockAdapterState] = field(default_factory=dict)


# =============================================================================
# Fixtures
# =============================================================================
# Note: signal_store fixture is provided by root conftest.py


@pytest.fixture
def mock_adapter_manager() -> MockAdapterManager:
    """Create a mock AdapterManager with no adapters registered."""
    return MockAdapterManager()


@pytest.fixture
def mock_adapter_factory() -> Callable[..., MockAdapter]:
    """Factory for creating mock adapters with custom settings."""

    def _create(**kwargs: Any) -> MockAdapter:
        return MockAdapter(**kwargs)

    return _create


@pytest.fixture
def app(signal_store: SignalStore, mock_adapter_manager: MockAdapterManager) -> FastAPI:
    """Create FastAPI app with injected test dependencies.

    Overrides get_signal_store dependency to return the test fixture store.
    Sets mock adapter_manager on app.state for /health endpoint.
    """
    test_app = FastAPI()
    test_app.include_router(routes_router)
    test_app.include_router(sse_router)

    # Override dependency to use test store
    test_app.dependency_overrides[get_signal_store] = lambda: signal_store

    # Set adapter manager on app state (accessed by /health)
    test_app.state.adapter_manager = mock_adapter_manager

    return test_app


@pytest.fixture
async def async_client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Async HTTP client for testing endpoints.

    Uses httpx AsyncClient with ASGI transport to call FastAPI directly
    without starting a real server.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client
