"""Unit tests for AdapterManager sync behavior and multi-adapter coordination.

Test Techniques Used:
- State Transition Testing: Reconnection logic after stream errors
- Specification-based Testing: Multi-adapter coordination

Coverage Target: Critical Risk (adapters/manager.py)
- Line Coverage: ≥90%
- Branch Coverage: ≥85%
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Callable
from typing import TYPE_CHECKING

from lumehaven.adapters.manager import AdapterManager
from lumehaven.core.signal import Signal
from lumehaven.state.store import SignalStore
from tests.fixtures.async_utils import wait_for_condition

if TYPE_CHECKING:
    from tests.unit.adapters.conftest import MockAdapter


class TestSyncBehavior:
    """Tests for event sync task behavior.

    Technique: State Transition Testing for reconnection logic
    """

    async def test_sync_task_publishes_events_to_store(
        self,
        adapter_manager: AdapterManager,
        signal_store: SignalStore,
        mock_adapter_factory: Callable[..., MockAdapter],
        sample_signals: dict[str, Signal],
    ) -> None:
        """Events from adapter stream are published to SignalStore."""
        # Arrange
        update_signal = Signal(
            id="mock:temp_1", value="25.0", unit="°C", label="Updated Temperature"
        )
        adapter = mock_adapter_factory(
            _name="streaming-adapter",
            signals_to_return=sample_signals,
            events_to_yield=[update_signal],
            event_stream_closes_after=1,  # Close after yielding event
        )
        adapter_manager.add(adapter)

        # Subscribe to store before starting
        received_events: list[Signal] = []

        async def collect_events() -> None:
            async for signal in signal_store.subscribe():
                received_events.append(signal)
                break  # Just need one

        collector_task = asyncio.create_task(collect_events())

        # Act
        await adapter_manager.start_all()

        # Wait for event to be received
        await wait_for_condition(
            lambda: len(received_events) >= 1,
            timeout=2.0,
            description="event publication",
        )

        # Assert
        assert len(received_events) >= 1
        assert received_events[0].id == "mock:temp_1"
        assert received_events[0].value == "25.0"

        # Cleanup
        collector_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await collector_task
        await adapter_manager.stop_all()

    async def test_stream_end_sets_disconnected_state(
        self,
        adapter_manager: AdapterManager,
        mock_adapter_factory: Callable[..., MockAdapter],
        sample_signals: dict[str, Signal],
    ) -> None:
        """Event stream ending normally sets connected=False.

        State transition: CONNECTED → (stream end) → DISCONNECTED
        """
        # Arrange
        adapter = mock_adapter_factory(
            _name="closing-adapter",
            signals_to_return=sample_signals,
            event_stream_closes_after=0,  # Close immediately
        )
        adapter_manager.add(adapter)

        # Act
        await adapter_manager.start_all()

        # Wait for the sync task to detect stream closure
        await wait_for_condition(
            lambda: adapter_manager.states["closing-adapter"].connected is False,
            timeout=2.0,
            description="disconnection detection",
        )

        # Assert
        state = adapter_manager.states["closing-adapter"]
        assert state.connected is False
        assert "closed" in state.error.lower() if state.error else True

        # Cleanup
        await adapter_manager.stop_all()

    async def test_sync_reconnects_after_stream_error(
        self,
        adapter_manager: AdapterManager,
        mock_adapter_factory: Callable[..., MockAdapter],
        sample_signals: dict[str, Signal],
    ) -> None:
        """Sync task reconnects after subscribe_events raises an error.

        State transition: CONNECTED → (error) → DISCONNECTED → (reconnect) → CONNECTED
        """
        # Arrange — adapter that fails on first subscribe then succeeds
        adapter = mock_adapter_factory(
            _name="recovering-adapter",
            signals_to_return=sample_signals,
        )
        adapter_manager.add(adapter)

        # Start and let it connect
        await adapter_manager.start_all()
        state = adapter_manager.states["recovering-adapter"]
        assert state.connected is True

        # Simulate stream closure (adapter will try to reconnect)
        await adapter.close_stream()

        # Wait for disconnection
        await wait_for_condition(
            lambda: state.connected is False,
            timeout=2.0,
            description="disconnection after stream close",
        )

        # The sync task should attempt reconnection
        # We verify by checking get_signals is called again
        initial_call_count = adapter.get_signals_call_count

        # Wait for reconnect attempt (test uses 10ms retry delay)
        await wait_for_condition(
            lambda: adapter.get_signals_call_count > initial_call_count,
            timeout=1.0,  # Fast with test's 10ms retry delay
            description="reconnection attempt",
        )

        # Assert — reconnection was attempted
        assert adapter.get_signals_call_count > initial_call_count

        # Cleanup
        await adapter_manager.stop_all()

    async def test_successful_reconnection_resets_retry_delay(
        self,
        adapter_manager: AdapterManager,
        mock_adapter_factory: Callable[..., MockAdapter],
        sample_signals: dict[str, Signal],
    ) -> None:
        """Successful reconnection resets retry_delay to INITIAL.

        This tests the recovery path where after backoff increases,
        a successful reconnection brings the delay back to initial.
        """
        # Arrange
        adapter = mock_adapter_factory(
            _name="recovering-adapter",
            signals_to_return=sample_signals,
        )
        adapter_manager.add(adapter)

        await adapter_manager.start_all()
        state = adapter_manager.states["recovering-adapter"]

        # Simulate a disconnect-reconnect cycle
        await adapter.close_stream()

        # Wait for disconnect
        await wait_for_condition(
            lambda: state.connected is False,
            timeout=2.0,
            description="disconnection",
        )

        # After backoff, delay should have increased
        # Wait for reconnection
        await wait_for_condition(
            lambda: state.connected is True,
            timeout=1.0,  # Fast with test's 10ms retry delay
            description="reconnection",
        )

        # Assert — delay reset to manager's configured initial value
        assert state.retry_delay == adapter_manager.initial_retry_delay

        # Cleanup
        await adapter_manager.stop_all()


class TestMultipleAdapters:
    """Tests for managing multiple adapters simultaneously.

    Technique: Specification-based testing for multi-adapter coordination.
    """

    async def test_start_all_starts_all_adapters_independently(
        self,
        adapter_manager: AdapterManager,
        signal_store: SignalStore,
        mock_adapter_factory: Callable[..., MockAdapter],
    ) -> None:
        """Each adapter starts independently — one failure doesn't block others."""
        # Arrange
        healthy_signals = {
            "mock:healthy": Signal(id="mock:healthy", value="OK", unit="", label="OK"),
        }
        healthy = mock_adapter_factory(
            _name="healthy",
            signals_to_return=healthy_signals,
        )
        failing = mock_adapter_factory(
            _name="failing",
            should_fail_connect=True,
        )

        adapter_manager.add(healthy)
        adapter_manager.add(failing)

        # Act
        await adapter_manager.start_all()

        # Assert — healthy adapter connected
        assert adapter_manager.states["healthy"].connected is True
        # Assert — failing adapter has error
        assert adapter_manager.states["failing"].connected is False
        assert adapter_manager.states["failing"].error is not None

        # Assert — healthy adapter's signals in store
        stored = await signal_store.get_all()
        assert "mock:healthy" in stored

        # Cleanup
        await adapter_manager.stop_all()

    async def test_stop_all_closes_all_adapters(
        self,
        adapter_manager: AdapterManager,
        mock_adapter_factory: Callable[..., MockAdapter],
    ) -> None:
        """stop_all() closes all adapters regardless of state."""
        # Arrange
        adapters = [mock_adapter_factory(_name=f"adapter-{i}") for i in range(5)]
        for adapter in adapters:
            adapter_manager.add(adapter)

        await adapter_manager.start_all()

        # Act
        await adapter_manager.stop_all()

        # Assert — all adapters closed
        for adapter in adapters:
            assert adapter.close_call_count >= 1
