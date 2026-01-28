"""SmartHomeAdapter protocol - the contract for smart home integrations.

This module defines the Protocol that all smart home adapters must implement.
Using Protocol (structural subtyping) rather than ABC allows for more flexible
implementations and better testability.

From ADR-005:
- Adapters are responsible for converting smart home data to Signal objects
- All normalization (units, formatting) happens in the adapter
- The protocol is async-first for non-blocking I/O
"""

from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from lumehaven.core.signal import Signal


@runtime_checkable
class SmartHomeAdapter(Protocol):
    """Protocol defining the interface for smart home system adapters.

    All adapters must implement these methods and properties to provide:
    1. Adapter identity (name, type)
    2. Initial load of all signals
    3. Lookup of individual signals
    4. Real-time event streaming
    5. Connection status and lifecycle management

    The @runtime_checkable decorator allows isinstance() checks,
    useful for validation and testing.

    Example:
        >>> class MyAdapter:
        ...     @property
        ...     def name(self) -> str: return "my-adapter"
        ...     @property
        ...     def adapter_type(self) -> str: return "custom"
        ...     async def get_signals(self) -> dict[str, Signal]: ...
        ...     async def get_signal(self, signal_id: str) -> Signal: ...
        ...     async def subscribe_events(self) -> AsyncIterator[Signal]: ...
        ...     def is_connected(self) -> bool: return True
        ...     async def close(self) -> None: ...
        >>> isinstance(MyAdapter(), SmartHomeAdapter)
        True
    """

    @property
    def name(self) -> str:
        """Unique identifier for this adapter instance.

        Used for logging, health checks, and signal ID prefixing.
        Should be user-friendly and distinguishable when multiple
        adapters of the same type exist.

        Examples: "openhab-main", "homeassistant-garage", "openhab"
        """
        ...

    @property
    def adapter_type(self) -> str:
        """The type of smart home system this adapter connects to.

        Used for UI grouping, icons, and type-specific behavior.
        Should be lowercase and match SmartHomeType enum values.

        Examples: "openhab", "homeassistant"
        """
        ...

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

    def subscribe_events(self) -> AsyncIterator[Signal]:
        """Subscribe to real-time signal updates.

        This method returns an async iterator (typically implemented as an
        async generator function). Call it and iterate with `async for`.

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

    async def close(self) -> None:
        """Clean up adapter resources.

        Called during application shutdown to close HTTP clients,
        WebSocket connections, or other resources.

        Implementations should be idempotent (safe to call multiple times).
        """
        ...
