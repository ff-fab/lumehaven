"""In-memory signal state storage.

Implements ADR-001: Start with in-memory storage, interface allows
future swap to Redis or other backends without changing consumers.

Key design decisions:
- Protocol-based interface for testability and future flexibility
- Async methods to allow non-blocking implementations
- Thread-safe via asyncio locks (not threading locks)
- Singleton access via get_signal_store() for DI in FastAPI
"""

import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import Protocol, runtime_checkable

from lumehaven.core.signal import Signal

logger = logging.getLogger(__name__)


@runtime_checkable
class SignalStoreProtocol(Protocol):
    """Protocol for signal storage backends.

    This abstraction allows swapping the storage implementation
    (e.g., Redis) without changing the API layer.
    """

    async def get_all(self) -> dict[str, Signal]:
        """Get all stored signals."""
        ...

    async def get(self, signal_id: str) -> Signal | None:
        """Get a specific signal by ID."""
        ...

    async def set(self, signal: Signal) -> None:
        """Store or update a signal."""
        ...

    async def set_many(self, signals: dict[str, Signal]) -> None:
        """Store or update multiple signals."""
        ...

    async def subscribe(self) -> AsyncGenerator[Signal, None]:
        """Subscribe to signal updates."""
        ...

    async def publish(self, signal: Signal) -> None:
        """Publish a signal update to subscribers."""
        ...


class SignalStore:
    """In-memory implementation of signal storage.

    Thread-safe via asyncio locks. Suitable for single-instance
    deployments (typical for Raspberry Pi dashboard).

    For multi-instance deployments, swap this for a Redis-backed
    implementation using the same SignalStoreProtocol.

    Attributes:
        _signals: Dictionary of signal ID to Signal.
        _lock: Asyncio lock for thread-safe access.
        _subscribers: Set of queues for pub/sub.
    """

    def __init__(self) -> None:
        """Initialize empty signal store."""
        self._signals: dict[str, Signal] = {}
        self._lock = asyncio.Lock()
        self._subscribers: set[asyncio.Queue[Signal]] = set()

    async def get_all(self) -> dict[str, Signal]:
        """Get all stored signals.

        Returns:
            Copy of the signals dictionary.
        """
        async with self._lock:
            return self._signals.copy()

    async def get(self, signal_id: str) -> Signal | None:
        """Get a specific signal by ID.

        Args:
            signal_id: The signal's unique identifier.

        Returns:
            Signal if found, None otherwise.
        """
        async with self._lock:
            return self._signals.get(signal_id)

    async def set(self, signal: Signal) -> None:
        """Store or update a signal.

        Args:
            signal: The signal to store.
        """
        async with self._lock:
            self._signals[signal.id] = signal

    async def set_many(self, signals: dict[str, Signal]) -> None:
        """Store or update multiple signals atomically.

        Args:
            signals: Dictionary of signal ID to Signal.
        """
        async with self._lock:
            self._signals.update(signals)
        logger.debug(f"Stored {len(signals)} signals")

    async def subscribe(self) -> AsyncGenerator[Signal, None]:
        """Subscribe to signal updates.

        Yields:
            Signal objects as they are published.

        Note:
            Caller must handle cleanup if breaking out of the generator.
        """
        queue: asyncio.Queue[Signal] = asyncio.Queue()
        self._subscribers.add(queue)
        try:
            while True:
                signal = await queue.get()
                yield signal
        finally:
            self._subscribers.discard(queue)

    async def publish(self, signal: Signal) -> None:
        """Publish a signal update to all subscribers.

        Also updates the stored value.

        Args:
            signal: The updated signal.
        """
        # Update stored value
        await self.set(signal)

        # Notify subscribers
        for queue in self._subscribers:
            try:
                queue.put_nowait(signal)
            except asyncio.QueueFull:
                logger.warning(f"Subscriber queue full, dropping update for {signal.id}")

    def subscriber_count(self) -> int:
        """Get the number of active subscribers.

        Returns:
            Number of subscribers.
        """
        return len(self._subscribers)


# Singleton instance
_signal_store: SignalStore | None = None


def get_signal_store() -> SignalStore:
    """Get the singleton SignalStore instance.

    This function is designed for FastAPI dependency injection.

    Returns:
        The global SignalStore instance.
    """
    global _signal_store
    if _signal_store is None:
        _signal_store = SignalStore()
    return _signal_store


def reset_signal_store() -> None:
    """Reset the singleton for testing.

    WARNING: Only use in tests!
    """
    global _signal_store
    _signal_store = None
