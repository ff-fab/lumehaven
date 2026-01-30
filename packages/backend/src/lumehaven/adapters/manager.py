"""Adapter lifecycle management.

This module handles the lifecycle of smart home adapters:
- Startup with initial signal loading
- Background sync tasks for live updates
- Automatic reconnection with exponential backoff
- Graceful shutdown

The AdapterManager is used by the FastAPI lifespan handler to coordinate
adapter instances across their full lifecycle.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lumehaven.adapters.protocol import SmartHomeAdapter
    from lumehaven.state.store import SignalStore

logger = logging.getLogger(__name__)

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
    _store_getter: Callable[[], SignalStore] = field(
        default=lambda: None,  # type: ignore[assignment]
        repr=False,
    )

    def __post_init__(self) -> None:
        """Initialize store getter after dataclass init."""
        # Deferred import to avoid circular dependency
        from lumehaven.state.store import get_signal_store

        object.__setattr__(self, "_store_getter", get_signal_store)

    def _get_store(self) -> SignalStore:
        """Get the signal store instance."""
        return self._store_getter()

    def add(self, adapter: SmartHomeAdapter) -> None:
        """Register an adapter for management.

        Raises:
            ValueError: If an adapter with the same name is already registered.
        """
        name = adapter.name
        if name in self.states:
            raise ValueError(
                f"Duplicate adapter name '{name}' detected. "
                "Adapter names must be unique. Check your adapter configuration."
            )
        self.states[name] = AdapterState(adapter=adapter)

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
        store = self._get_store()

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
        store = self._get_store()
        state = self.states[name]
        adapter = state.adapter

        while True:
            try:
                async for signal in adapter.subscribe_events():
                    await store.publish(signal)

                # Iterator completed normally (server closed stream)
                # Treat as transient failure and reconnect with backoff
                logger.debug(
                    f"Adapter '{name}' event stream ended normally, reconnecting..."
                )
                state.connected = False
                state.error = "Event stream closed by server"

            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Adapter '{name}' sync failed: {e}")
                state.connected = False
                state.error = str(e)

            # Wait before reconnecting (applies to both normal end and errors)
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
                logger.error(f"Adapter '{name}' reconnect failed: {reconnect_error}")
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
            await self._start_adapter(name, state, self._get_store())

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
