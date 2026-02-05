"""Unit tests for AdapterManager lifecycle transitions.

Test Techniques Used:
- State Transition Testing: Adapter lifecycle states
  (disconnected → connected, connection failure, stop_all cleanup)
- Specification-based Testing: Public API contracts for start_all(), stop_all()

Coverage Target: Critical Risk (adapters/manager.py)
- Line Coverage: ≥90%
- Branch Coverage: ≥85%
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from lumehaven.adapters.manager import AdapterManager
from lumehaven.core.signal import Signal
from lumehaven.state.store import SignalStore

if TYPE_CHECKING:
    from tests.unit.adapters.conftest import MockAdapter


class TestLifecycleTransitions:
    """Tests for adapter lifecycle state transitions.

    Technique: State Transition Testing
    States: DISCONNECTED → CONNECTED → (error) → DISCONNECTED → (retry) → CONNECTED
    """

    async def test_start_all_connects_adapter_and_loads_signals(
        self,
        adapter_manager: AdapterManager,
        signal_store: SignalStore,
        mock_adapter_factory: Callable[..., MockAdapter],
        sample_signals: dict[str, Signal],
    ) -> None:
        """start_all() transitions adapter to connected and loads signals.

        State transition: DISCONNECTED → CONNECTED
        """
        # Arrange
        adapter = mock_adapter_factory(
            _name="test-adapter",
            signals_to_return=sample_signals,
        )
        adapter_manager.add(adapter)

        # Act
        await adapter_manager.start_all()

        # Assert — adapter state
        state = adapter_manager.states["test-adapter"]
        assert state.connected is True
        assert state.error is None
        assert adapter.get_signals_call_count == 1

        # Assert — signals loaded to store
        stored_signals = await signal_store.get_all()
        assert len(stored_signals) == len(sample_signals)

        # Cleanup
        await adapter_manager.stop_all()

    async def test_start_all_with_connection_failure_sets_error_state(
        self,
        adapter_manager: AdapterManager,
        mock_adapter_factory: Callable[..., MockAdapter],
    ) -> None:
        """Connection failure transitions to error state with message.

        State transition: DISCONNECTED → (failure) → DISCONNECTED with error
        """
        # Arrange
        error_message = "Cannot reach OpenHAB server"
        adapter = mock_adapter_factory(
            _name="failing-adapter",
            should_fail_connect=True,
            connect_error_message=error_message,
        )
        adapter_manager.add(adapter)

        # Act
        await adapter_manager.start_all()

        # Assert
        state = adapter_manager.states["failing-adapter"]
        assert state.connected is False
        assert state.error == error_message

        # Cleanup — cancel any scheduled retry tasks
        await adapter_manager.stop_all()

    async def test_start_all_creates_sync_task_for_connected_adapter(
        self,
        adapter_manager: AdapterManager,
        mock_adapter_factory: Callable[..., MockAdapter],
        sample_signals: dict[str, Signal],
    ) -> None:
        """Connected adapter gets a sync task for event streaming."""
        # Arrange
        adapter = mock_adapter_factory(
            _name="test-adapter",
            signals_to_return=sample_signals,
        )
        adapter_manager.add(adapter)

        # Act
        await adapter_manager.start_all()

        # Assert
        state = adapter_manager.states["test-adapter"]
        assert state.sync_task is not None
        assert not state.sync_task.done()
        assert state.sync_task.get_name() == "sync-test-adapter"

        # Cleanup
        await adapter_manager.stop_all()

    async def test_stop_all_cancels_sync_tasks(
        self,
        adapter_manager: AdapterManager,
        mock_adapter_factory: Callable[..., MockAdapter],
        sample_signals: dict[str, Signal],
    ) -> None:
        """stop_all() cancels all sync tasks gracefully."""
        # Arrange
        adapter = mock_adapter_factory(
            _name="test-adapter",
            signals_to_return=sample_signals,
        )
        adapter_manager.add(adapter)
        await adapter_manager.start_all()

        state = adapter_manager.states["test-adapter"]
        sync_task = state.sync_task
        assert sync_task is not None

        # Act
        await adapter_manager.stop_all()

        # Assert — task is cancelled
        assert sync_task.cancelled() or sync_task.done()

    async def test_stop_all_calls_close_on_all_adapters(
        self,
        adapter_manager: AdapterManager,
        mock_adapter_factory: Callable[..., MockAdapter],
    ) -> None:
        """stop_all() calls close() on every registered adapter."""
        # Arrange
        adapters = [mock_adapter_factory(_name=f"adapter-{i}") for i in range(3)]
        for adapter in adapters:
            adapter_manager.add(adapter)

        # Note: Don't call start_all() — test close even without start
        # Act
        await adapter_manager.stop_all()

        # Assert
        for adapter in adapters:
            assert adapter.close_call_count == 1
