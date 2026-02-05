"""Unit tests for AdapterManager retry logic.

Test Techniques Used:
- Specification-based Testing: Retry task creation and cancellation

Coverage Target: Critical Risk (adapters/manager.py)
- Line Coverage: ≥90%
- Branch Coverage: ≥85%
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from lumehaven.adapters.manager import (
    INITIAL_RETRY_DELAY,
    AdapterManager,
    AdapterState,
)

if TYPE_CHECKING:
    from tests.unit.adapters.conftest import MockAdapter


class TestRetryLogic:
    """Tests for retry task creation and cancellation.

    Technique: Specification-based testing for retry scheduling behavior.
    """

    def test_adapter_state_initializes_with_initial_retry_delay(
        self,
        mock_adapter: MockAdapter,
    ) -> None:
        """New AdapterState starts with INITIAL_RETRY_DELAY by default.

        Note: When created via AdapterManager.add(), the manager injects
        its configured initial_retry_delay instead.
        """
        state = AdapterState(adapter=mock_adapter)
        assert state.retry_delay == INITIAL_RETRY_DELAY

    async def test_schedule_retry_creates_retry_task(
        self,
        adapter_manager: AdapterManager,
        mock_adapter_factory: Callable[..., MockAdapter],
    ) -> None:
        """_schedule_retry creates a named retry task.

        Technique: Indirect testing of private method through public API.
        """
        # Arrange
        adapter = mock_adapter_factory(
            _name="failing-adapter",
            should_fail_connect=True,
        )
        adapter_manager.add(adapter)

        # Act — start_all will fail and schedule retry
        await adapter_manager.start_all()

        # Assert — retry task was created
        assert "failing-adapter" in adapter_manager._retry_tasks
        retry_task = adapter_manager._retry_tasks["failing-adapter"]
        assert retry_task.get_name() == "retry-failing-adapter"

        # Cleanup
        await adapter_manager.stop_all()

    async def test_schedule_retry_does_not_duplicate(
        self,
        adapter_manager: AdapterManager,
        mock_adapter_factory: Callable[..., MockAdapter],
    ) -> None:
        """Multiple failures don't create duplicate retry tasks."""
        # Arrange
        adapter = mock_adapter_factory(
            _name="failing-adapter",
            should_fail_connect=True,
        )
        adapter_manager.add(adapter)

        # Act — call start multiple times
        await adapter_manager.start_all()
        first_task = adapter_manager._retry_tasks.get("failing-adapter")

        # Manually call _schedule_retry again (simulating another failure)
        adapter_manager._schedule_retry("failing-adapter")

        # Assert — same task, not replaced
        assert adapter_manager._retry_tasks.get("failing-adapter") is first_task

        # Cleanup
        await adapter_manager.stop_all()

    async def test_stop_all_cancels_retry_tasks(
        self,
        adapter_manager: AdapterManager,
        mock_adapter_factory: Callable[..., MockAdapter],
    ) -> None:
        """stop_all() cancels pending retry tasks."""
        # Arrange
        adapter = mock_adapter_factory(
            _name="failing-adapter",
            should_fail_connect=True,
        )
        adapter_manager.add(adapter)
        await adapter_manager.start_all()

        retry_task = adapter_manager._retry_tasks.get("failing-adapter")
        assert retry_task is not None

        # Act
        await adapter_manager.stop_all()

        # Assert
        assert retry_task.cancelled() or retry_task.done()
        assert len(adapter_manager._retry_tasks) == 0
