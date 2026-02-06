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
import time
from collections.abc import AsyncGenerator
from typing import Protocol, runtime_checkable

from lumehaven.config import get_settings
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

    async def subscribe(self) -> AsyncGenerator[Signal]:
        """Subscribe to signal updates."""
        ...

    async def publish(self, signal: Signal) -> None:
        """Publish a signal update to subscribers."""
        ...


class SignalStore:
    """In-memory implementation of signal storage.

    Thread-safe via asyncio locks. Suitable for single-instance
    deployments.

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
        # Track drops per subscriber: queue -> (drop_count, last_log_time)
        self._drop_stats: dict[asyncio.Queue[Signal], tuple[int, float]] = {}

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

    async def subscribe(self) -> AsyncGenerator[Signal]:
        """Subscribe to signal updates.

        Yields:
            Signal objects as they are published.

        Note:
            Caller must handle cleanup if breaking out of the generator.
            Queue is bounded to prevent memory exhaustion from slow consumers.
            When full, new updates are dropped (see publish()).
        """
        queue = self.register_subscriber()
        try:
            while True:
                signal = await queue.get()
                yield signal
        finally:
            self.unregister_subscriber(queue)

    def register_subscriber(self) -> asyncio.Queue[Signal]:
        """Register a new subscriber and return its queue.

        This method allows eager registration of subscribers before
        the async generator starts iterating, which is important for
        accurate subscriber counts in testing and monitoring.

        Returns:
            A bounded asyncio.Queue that will receive Signal objects.
        """
        settings = get_settings()
        queue: asyncio.Queue[Signal] = asyncio.Queue(
            maxsize=settings.subscriber_queue_size
        )
        self._subscribers.add(queue)
        logger.debug(f"Registered subscriber, total: {len(self._subscribers)}")
        return queue

    def unregister_subscriber(self, queue: asyncio.Queue[Signal]) -> None:
        """Unregister a subscriber and clean up its resources.

        Args:
            queue: The subscriber queue to remove.
        """
        self._subscribers.discard(queue)
        # Clean up drop stats to prevent memory leak
        self._drop_stats.pop(queue, None)
        logger.debug(f"Unregistered subscriber, total: {len(self._subscribers)}")

    async def publish(self, signal: Signal) -> None:
        """Publish a signal update to all subscribers.

        Also updates the stored value.

        Args:
            signal: The updated signal.
        """
        # Update stored value
        await self.set(signal)

        # Notify subscribers (iterate over snapshot to prevent race conditions)
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(signal)
                # Reset drop stats on successful delivery
                if queue in self._drop_stats:
                    del self._drop_stats[queue]
            except asyncio.QueueFull:
                self._log_drop_throttled(queue, signal.id)

    def _log_drop_throttled(self, queue: asyncio.Queue[Signal], signal_id: str) -> None:
        """Log dropped messages with rate limiting to prevent log flooding.

        Logs immediately on first drop, then at most every drop_log_interval
        seconds per subscriber, summarizing how many were dropped.
        """
        settings = get_settings()
        drop_log_interval = settings.drop_log_interval
        now = time.monotonic()

        if queue not in self._drop_stats:
            # First drop for this subscriber
            logger.warning(f"Subscriber queue full, dropping update for {signal_id}")
            # Start tracking with zero pending drops and current time as last log
            self._drop_stats[queue] = (0, now)
            return

        drop_count, last_log_time = self._drop_stats[queue]
        drop_count += 1

        if now - last_log_time >= drop_log_interval:
            # Time to log a summary
            logger.warning(
                f"Subscriber queue full, dropped {drop_count} updates "
                f"in last {drop_log_interval:.0f}s (latest: {signal_id})"
            )
            # Reset count after logging
            self._drop_stats[queue] = (0, now)
        else:
            # Suppress log, just increment counter
            self._drop_stats[queue] = (drop_count, last_log_time)

    def subscriber_count(self) -> int:
        """Get the number of active subscribers.

        Returns:
            Number of subscribers.
        """
        return len(self._subscribers)

    def get_metrics(self) -> dict[str, dict[str, int]]:
        """Get store metrics for monitoring and debugging.

        Returns a structured dictionary with current store state,
        useful for dashboards, health checks, and testing.

        Returns:
            Dictionary with metrics grouped by category:
            - subscribers: total count and slow (backpressured) count
            - signals: count of stored signals
        """
        return {
            "subscribers": {
                "total": len(self._subscribers),
                "slow": len(self._drop_stats),
            },
            "signals": {
                "stored": len(self._signals),
            },
        }


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
