"""FastAPI application entry point.

This is the main module that creates and configures the FastAPI application.
Run with: uvicorn lumehaven.main:app --reload
"""

import asyncio
import contextlib
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from lumehaven import __version__
from lumehaven import adapters as _adapters  # noqa: F401 - registers factories
from lumehaven.adapters.protocol import SmartHomeAdapter
from lumehaven.api.routes import router as api_router
from lumehaven.api.sse import router as sse_router
from lumehaven.config import (
    ADAPTER_FACTORIES,
    AdapterConfig,
    get_settings,
    load_adapter_configs,
)
from lumehaven.state.store import SignalStore, get_signal_store

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Adapter Factory
# -----------------------------------------------------------------------------


def create_adapter(config: AdapterConfig) -> SmartHomeAdapter:
    """Create an adapter instance from configuration.

    Uses the ADAPTER_FACTORIES registry to find the appropriate factory
    function based on the config's type field. Adapters register themselves
    via the @register_adapter_factory decorator when their module is imported.

    Args:
        config: Adapter configuration (discriminated by type field).

    Returns:
        Configured adapter instance.

    Raises:
        NotImplementedError: If no factory is registered for the adapter type.
    """
    adapter_type = config.type
    factory = ADAPTER_FACTORIES.get(adapter_type)

    if factory is None:
        raise NotImplementedError(
            f"No factory registered for adapter type '{adapter_type}'. "
            f"Available types: {list(ADAPTER_FACTORIES.keys())}"
        )

    adapter: SmartHomeAdapter = factory(config)
    return adapter


# -----------------------------------------------------------------------------
# Adapter State Management
# -----------------------------------------------------------------------------

# Retry settings for failed adapters
INITIAL_RETRY_DELAY = 5.0  # seconds
MAX_RETRY_DELAY = 300.0  # 5 minutes
RETRY_BACKOFF_FACTOR = 2.0


@dataclass
class AdapterState:
    """Runtime state for a single adapter.

    Tracks the adapter instance, its sync task, and connection status.
    """

    adapter: SmartHomeAdapter
    sync_task: asyncio.Task[None] | None = None
    connected: bool = False
    error: str | None = None
    retry_delay: float = INITIAL_RETRY_DELAY


@dataclass
class AdapterManager:
    """Manages multiple adapters with independent lifecycle.

    Handles startup, sync tasks, retry logic, and graceful shutdown.
    """

    states: dict[str, AdapterState] = field(default_factory=dict)
    _retry_tasks: dict[str, asyncio.Task[None]] = field(default_factory=dict)

    def add(self, adapter: SmartHomeAdapter) -> None:
        """Register an adapter for management."""
        self.states[adapter.name] = AdapterState(adapter=adapter)

    @property
    def adapters(self) -> list[SmartHomeAdapter]:
        """Get all managed adapters."""
        return [state.adapter for state in self.states.values()]

    @property
    def connected_adapters(self) -> list[SmartHomeAdapter]:
        """Get adapters that are currently connected."""
        return [state.adapter for state in self.states.values() if state.connected]

    async def start_all(self) -> None:
        """Start all adapters, load initial signals, begin sync tasks.

        Adapters that fail to connect will be scheduled for retry.
        """
        store = get_signal_store()

        for name, state in self.states.items():
            await self._start_adapter(name, state, store)

    async def _start_adapter(
        self,
        name: str,
        state: AdapterState,
        store: SignalStore,
    ) -> None:
        """Start a single adapter with error handling."""
        adapter = state.adapter
        try:
            logger.info(f"Connecting to {adapter.adapter_type} adapter '{name}'...")
            signals = await adapter.get_signals()
            await store.set_many(signals)
            logger.info(f"Adapter '{name}': loaded {len(signals)} signals")

            # Start sync task
            state.sync_task = asyncio.create_task(
                self._sync_with_retry(name),
                name=f"sync-{name}",
            )
            state.connected = True
            state.error = None
            state.retry_delay = INITIAL_RETRY_DELAY

        except Exception as e:
            logger.error(f"Adapter '{name}' failed to connect: {e}")
            state.connected = False
            state.error = str(e)
            self._schedule_retry(name)

    async def _sync_with_retry(self, name: str) -> None:
        """Sync task wrapper with automatic reconnection on failure."""
        store = get_signal_store()
        state = self.states[name]
        adapter = state.adapter

        while True:
            try:
                async for signal in adapter.subscribe_events():
                    await store.publish(signal)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Adapter '{name}' sync failed: {e}")
                state.connected = False
                state.error = str(e)

                # Wait before reconnecting
                await asyncio.sleep(state.retry_delay)
                state.retry_delay = min(
                    state.retry_delay * RETRY_BACKOFF_FACTOR,
                    MAX_RETRY_DELAY,
                )

                # Try to reconnect
                try:
                    signals = await adapter.get_signals()
                    await store.set_many(signals)
                    state.connected = True
                    state.error = None
                    state.retry_delay = INITIAL_RETRY_DELAY
                    logger.info(f"Adapter '{name}' reconnected")
                except Exception as reconnect_error:
                    logger.error(
                        f"Adapter '{name}' reconnect failed: {reconnect_error}"
                    )
                    # Loop will continue and try again

    def _schedule_retry(self, name: str) -> None:
        """Schedule a retry for a failed adapter."""
        if name in self._retry_tasks:
            return  # Already scheduled

        async def retry() -> None:
            state = self.states[name]
            await asyncio.sleep(state.retry_delay)
            state.retry_delay = min(
                state.retry_delay * RETRY_BACKOFF_FACTOR,
                MAX_RETRY_DELAY,
            )
            del self._retry_tasks[name]
            await self._start_adapter(name, state, get_signal_store())

        self._retry_tasks[name] = asyncio.create_task(retry(), name=f"retry-{name}")

    async def stop_all(self) -> None:
        """Stop all adapters and cleanup resources."""
        # Cancel retry tasks
        for task in self._retry_tasks.values():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        self._retry_tasks.clear()

        # Cancel sync tasks and close adapters
        for name, state in self.states.items():
            if state.sync_task is not None:
                state.sync_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await state.sync_task

            await state.adapter.close()
            logger.info(f"Adapter '{name}' closed")


# -----------------------------------------------------------------------------
# Application Lifespan
# -----------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Application lifespan manager.

    Handles startup and shutdown tasks:
    - Startup: Create adapters, load signals, start sync tasks
    - Shutdown: Cancel tasks, close connections
    """
    # Load adapter configurations
    adapter_configs = load_adapter_configs()
    logger.info(f"Loaded {len(adapter_configs)} adapter configuration(s)")

    # Create adapter manager
    manager = AdapterManager()
    for config in adapter_configs:
        adapter = create_adapter(config)
        manager.add(adapter)

    # Store manager for access in routes
    app.state.adapter_manager = manager

    try:
        # Start all adapters (failures are handled gracefully)
        await manager.start_all()

        if not manager.connected_adapters:
            logger.warning("No adapters connected - starting in degraded mode")
        else:
            logger.info(
                f"Started with {len(manager.connected_adapters)}/"
                f"{len(manager.adapters)} adapter(s) connected"
            )

        yield

    finally:
        logger.info("Shutting down...")
        await manager.stop_all()
        logger.info("Shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI instance.
    """
    settings = get_settings()

    app = FastAPI(
        title="lumehaven",
        description="Smart home dashboard backend",
        version=__version__,
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(api_router)
    app.include_router(sse_router)

    return app


# Application instance for uvicorn
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "lumehaven.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
