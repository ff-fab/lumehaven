"""Fixtures for adapter unit tests.

Provides mock adapters and pre-configured manager instances for testing
adapter lifecycle, registration, and coordination.

Key Fixtures:
- MockAdapter: Configurable test adapter implementing SmartHomeAdapter protocol
- adapter_manager: Fresh AdapterManager with injected SignalStore
- signal_store: Isolated SignalStore instance for sociable unit tests
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pytest

from lumehaven.adapters.manager import AdapterManager
from lumehaven.core.exceptions import SignalNotFoundError
from lumehaven.core.signal import Signal, SignalType
from lumehaven.state.store import SignalStore

if TYPE_CHECKING:
    from collections.abc import Callable


# =============================================================================
# Mock Adapter — Configurable SmartHomeAdapter implementation
# =============================================================================


@dataclass(eq=False)
class MockAdapter:
    """Configurable mock adapter for testing AdapterManager.

    Implements SmartHomeAdapter protocol with configurable behavior:
    - Control connection success/failure
    - Provide custom signals for get_signals()
    - Queue events for subscribe_events()
    - Track method calls for verification

    Note: eq=False makes instances hashable by identity (id-based),
    allowing use in sets for test assertions.

    Example:
        >>> adapter = MockAdapter(name="test")
        >>> adapter.should_fail_connect = True
        >>> await adapter.get_signals()  # Raises ConnectionError
    """

    _name: str = "mock-adapter"
    _adapter_type: str = "mock"
    _prefix: str = "mock"

    # Behavior configuration
    should_fail_connect: bool = False
    connect_error_message: str = "Connection refused"
    signals_to_return: dict[str, Signal] = field(default_factory=dict)

    # Event stream configuration
    events_to_yield: list[Signal] = field(default_factory=list)
    should_fail_subscribe: bool = False
    subscribe_error_message: str = "Stream error"
    event_stream_closes_after: int | None = None  # Close after N events

    # Call tracking for verification
    get_signals_call_count: int = 0
    subscribe_events_call_count: int = 0
    close_call_count: int = 0
    send_command_call_count: int = 0
    last_command: tuple[str, str] | None = None
    should_fail_command: bool = False
    command_error_message: str = "Command delivery failed"

    # Internal state
    _connected: bool = False
    _event_queue: asyncio.Queue[Signal | None] = field(default_factory=asyncio.Queue)
    _closed: bool = False

    @property
    def name(self) -> str:
        """Unique identifier for this adapter instance."""
        return self._name

    @property
    def adapter_type(self) -> str:
        """The type of smart home system this adapter connects to."""
        return self._adapter_type

    @property
    def prefix(self) -> str:
        """Short prefix for signal ID namespacing."""
        return self._prefix

    async def get_signals(self) -> dict[str, Signal]:
        """Get all signals from the smart home system.

        Raises:
            ConnectionError: If should_fail_connect is True.
        """
        self.get_signals_call_count += 1

        if self.should_fail_connect:
            raise ConnectionError(self.connect_error_message)

        self._connected = True
        return self.signals_to_return.copy()

    async def get_signal(self, signal_id: str) -> Signal | None:
        """Get a specific signal by ID."""
        return self.signals_to_return.get(signal_id)

    async def subscribe_events(self) -> AsyncIterator[Signal]:
        """Subscribe to real-time signal updates.

        Yields events from events_to_yield list, then from _event_queue.

        Raises:
            ConnectionError: If should_fail_subscribe is True.
        """
        self.subscribe_events_call_count += 1

        if self.should_fail_subscribe:
            raise ConnectionError(self.subscribe_error_message)

        # Yield pre-configured events first
        events_yielded = 0
        for signal in self.events_to_yield:
            if (
                self.event_stream_closes_after is not None
                and events_yielded >= self.event_stream_closes_after
            ):
                return  # Simulate stream close
            yield signal
            events_yielded += 1

        # Then yield from queue (for dynamic event injection during tests)
        while True:
            if (
                self.event_stream_closes_after is not None
                and events_yielded >= self.event_stream_closes_after
            ):
                return  # Simulate stream close

            try:
                event = await asyncio.wait_for(self._event_queue.get(), timeout=0.1)
                if event is None:
                    return  # Graceful shutdown signal
                yield event
                events_yielded += 1
            except TimeoutError:
                # No event available, keep polling
                continue

    def is_connected(self) -> bool:
        """Check if adapter is currently connected."""
        return self._connected

    async def close(self) -> None:
        """Close the adapter and release resources."""
        self.close_call_count += 1
        self._connected = False
        self._closed = True
        # Signal event stream to close
        await self._event_queue.put(None)

    async def send_command(self, signal_id: str, command: str) -> None:
        """Send a command to a signal/device (ADR-011).

        Raises:
            SignalNotFoundError: If signal_id not in signals_to_return.
            ConnectionError: If should_fail_command is True.
        """
        self.send_command_call_count += 1
        self.last_command = (signal_id, command)

        if self.should_fail_command:
            raise ConnectionError(self.command_error_message)

        if signal_id not in self.signals_to_return:
            raise SignalNotFoundError(signal_id)

    # ==========================================================================
    # Test helper methods
    # ==========================================================================

    async def inject_event(self, signal: Signal) -> None:
        """Inject an event into the stream during a test."""
        await self._event_queue.put(signal)

    async def close_stream(self) -> None:
        """Signal the event stream to close gracefully."""
        await self._event_queue.put(None)

    def reset_call_counts(self) -> None:
        """Reset all call tracking counters."""
        self.get_signals_call_count = 0
        self.subscribe_events_call_count = 0
        self.close_call_count = 0
        self.send_command_call_count = 0
        self.last_command = None


# =============================================================================
# Fixtures
# =============================================================================
# Note: signal_store fixture is provided by root conftest.py


@pytest.fixture
def adapter_manager(signal_store: SignalStore) -> AdapterManager:
    """Create an AdapterManager with injected SignalStore and fast retry delays.

    Uses a store getter that returns the test fixture store,
    bypassing the production singleton.

    Retry delays are set to 0.01s (instead of 5s) for fast test execution.
    """
    manager = AdapterManager(
        initial_retry_delay=0.01,  # 10ms instead of 5s
        max_retry_delay=0.05,  # 50ms instead of 300s
        retry_backoff_factor=2.0,
    )
    # Inject the test store via the store getter
    object.__setattr__(manager, "_store_getter", lambda: signal_store)
    return manager


@pytest.fixture
def mock_adapter() -> MockAdapter:
    """Create a basic mock adapter with default settings."""
    return MockAdapter()


@pytest.fixture
def mock_adapter_factory() -> Callable[..., MockAdapter]:
    """Factory for creating mock adapters with custom settings.

    Example:
        >>> adapter = mock_adapter_factory(name="custom", should_fail_connect=True)
    """

    def _create(**kwargs: object) -> MockAdapter:
        return MockAdapter(**kwargs)  # type: ignore[arg-type]

    return _create


@pytest.fixture
def sample_signals() -> dict[str, Signal]:
    """Sample signals for adapter tests (ADR-010 enriched)."""
    return {
        "mock:temp_1": Signal(
            id="mock:temp_1",
            value=21.5,
            display_value="21.5",
            unit="°C",
            label="Temperature",
            signal_type=SignalType.NUMBER,
        ),
        "mock:switch_1": Signal(
            id="mock:switch_1",
            value=True,
            display_value="ON",
            unit="",
            label="Light Switch",
            signal_type=SignalType.BOOLEAN,
        ),
    }
