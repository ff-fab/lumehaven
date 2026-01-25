"""SmartHomeAdapter protocol - the contract for smart home integrations.

This module defines the Protocol that all smart home adapters must implement.
Using Protocol (structural subtyping) rather than ABC allows for more flexible
implementations and better testability.

From ADR-005:
- Adapters are responsible for converting smart home data to Signal objects
- All normalization (units, formatting) happens in the adapter
- The protocol is async-first for non-blocking I/O
"""

from collections.abc import AsyncGenerator
from typing import Protocol, runtime_checkable

from lumehaven.core.signal import Signal


@runtime_checkable
class SmartHomeAdapter(Protocol):
    """Protocol defining the interface for smart home system adapters.

    All adapters must implement these methods to provide:
    1. Initial load of all signals
    2. Lookup of individual signals
    3. Real-time event streaming

    The @runtime_checkable decorator allows isinstance() checks,
    useful for validation and testing.

    Example:
        >>> class MyAdapter:
        ...     async def get_signals(self) -> dict[str, Signal]: ...
        ...     async def get_signal(self, signal_id: str) -> Signal: ...
        ...     async def subscribe_events(self) -> AsyncGenerator[Signal, None]: ...
        >>> isinstance(MyAdapter(), SmartHomeAdapter)
        True
    """

    async def get_signals(self) -> dict[str, Signal]:
        """Retrieve all signals from the smart home system.

        This is called on startup to populate the initial state.
        Implementations should handle connection errors gracefully.

        Returns:
            Dictionary mapping signal IDs to Signal objects.

        Raises:
            SmartHomeConnectionError: If connection to the system fails.
        """
        ...

    async def get_signal(self, signal_id: str) -> Signal:
        """Retrieve a specific signal by ID.

        Args:
            signal_id: The unique identifier of the signal.

        Returns:
            The Signal object for the given ID.

        Raises:
            SignalNotFoundError: If the signal doesn't exist.
            SmartHomeConnectionError: If connection to the system fails.
        """
        ...

    async def subscribe_events(self) -> AsyncGenerator[Signal]:
        """Subscribe to real-time signal updates.

        Returns an async generator that yields Signal objects whenever
        a value changes in the smart home system.

        Yields:
            Signal objects with updated values.

        Raises:
            SmartHomeConnectionError: If the event stream disconnects.

        Example:
            >>> async for signal in adapter.subscribe_events():
            ...     print(f"{signal.id}: {signal.value} {signal.unit}")
        """
        ...

    def is_connected(self) -> bool:
        """Check if the adapter has an active connection.

        This is a lightweight, synchronous check used for health monitoring.
        It does NOT make a network request - it only checks internal state.

        Returns:
            True if the adapter's client exists and is ready for requests.
        """
        ...
