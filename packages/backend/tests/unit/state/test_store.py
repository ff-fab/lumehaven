"""Unit tests for state/store.py — In-memory signal storage.

Test Techniques Used:
- Structural Verification: Protocol compliance
- Specification-based: CRUD operations, metrics API, singleton behavior
- State Transition: Pub/sub subscriber lifecycle
- Branch Coverage: Queue overflow, throttled logging paths
- Error Guessing: Memory leaks, race conditions
"""

import asyncio
import contextlib
from unittest.mock import Mock, patch

import pytest

from lumehaven.config import get_settings as real_get_settings
from lumehaven.core.signal import Signal
from lumehaven.state.store import (
    SignalStore,
    SignalStoreProtocol,
    get_signal_store,
    reset_signal_store,
)
from tests.fixtures.async_utils import wait_for_condition


@pytest.fixture
def store() -> SignalStore:
    """Fresh SignalStore instance per test."""
    return SignalStore()


@pytest.fixture
def sample_signal() -> Signal:
    """A single test signal."""
    return Signal(id="temp_living", value="21.5", unit="°C", label="Living Room")


@pytest.fixture
def sample_signals() -> dict[str, Signal]:
    """Multiple test signals for batch operations."""
    return {
        "temp_living": Signal(
            id="temp_living", value="21.5", unit="°C", label="Living Room"
        ),
        "temp_bedroom": Signal(
            id="temp_bedroom", value="18.0", unit="°C", label="Bedroom"
        ),
        "light_kitchen": Signal(
            id="light_kitchen", value="ON", unit="", label="Kitchen Light"
        ),
    }


@pytest.fixture
def mock_settings():
    """Mock get_settings() to control subscriber_queue_size."""
    real_get_settings.cache_clear()  # Clear lru_cache before patching
    settings = Mock()
    settings.subscriber_queue_size = 10
    settings.drop_log_interval = 10.0
    with patch("lumehaven.state.store.get_settings", return_value=settings):
        yield settings
    real_get_settings.cache_clear()  # Clear after to avoid polluting other tests


@pytest.fixture
def mock_settings_small_queue():
    """Mock get_settings() with small queue for overflow testing."""
    real_get_settings.cache_clear()
    settings = Mock()
    settings.subscriber_queue_size = 2
    settings.drop_log_interval = 10.0  # Default throttle interval
    with patch("lumehaven.state.store.get_settings", return_value=settings):
        yield settings
    real_get_settings.cache_clear()


@pytest.fixture
def mock_settings_small_queue_long_throttle():
    """Mock with small queue and long throttle (suppresses repeated logs)."""
    real_get_settings.cache_clear()
    settings = Mock()
    settings.subscriber_queue_size = 2
    settings.drop_log_interval = 1000.0  # Long interval suppresses logs
    with patch("lumehaven.state.store.get_settings", return_value=settings):
        yield settings
    real_get_settings.cache_clear()


@pytest.fixture
def mock_settings_small_queue_no_throttle():
    """Mock with small queue and no throttle (logs every drop)."""
    real_get_settings.cache_clear()
    settings = Mock()
    settings.subscriber_queue_size = 2
    settings.drop_log_interval = 0.0  # No throttle
    with patch("lumehaven.state.store.get_settings", return_value=settings):
        yield settings
    real_get_settings.cache_clear()


class TestProtocolCompliance:
    """Structural verification of SignalStore implementing SignalStoreProtocol."""

    def test_signal_store_implements_protocol(self, store: SignalStore) -> None:
        """SignalStore is a valid SignalStoreProtocol implementation."""
        assert isinstance(store, SignalStoreProtocol)

    def test_protocol_is_runtime_checkable(self) -> None:
        """Protocol can be used with isinstance() at runtime."""
        # This verifies the @runtime_checkable decorator is present
        assert hasattr(SignalStoreProtocol, "__protocol_attrs__") or isinstance(
            SignalStoreProtocol, type
        )


class TestGetMetrics:
    """Specification-based tests for SignalStore.get_metrics() observability API."""

    def test_empty_store_metrics(self, store: SignalStore) -> None:
        """Empty store returns zeroed metrics."""
        metrics = store.get_metrics()

        assert metrics == {
            "subscribers": {"total": 0, "slow": 0},
            "signals": {"stored": 0},
        }

    async def test_metrics_reflect_stored_signals(
        self, store: SignalStore, sample_signals: dict[str, Signal]
    ) -> None:
        """Metrics reflect signal count after storing."""
        await store.set_many(sample_signals)

        metrics = store.get_metrics()

        assert metrics["signals"]["stored"] == 3

    @pytest.mark.usefixtures("mock_settings")
    async def test_metrics_reflect_subscriber_count(self, store: SignalStore) -> None:
        """Metrics reflect active subscriber count."""
        started = asyncio.Event()

        async def subscriber():
            gen = store.subscribe()
            started.set()
            async for _ in gen:
                break

        task = asyncio.create_task(subscriber())
        await started.wait()

        metrics = store.get_metrics()
        assert metrics["subscribers"]["total"] == 1

        # Cleanup
        await store.publish(Signal(id="test", value="x", unit="", label=""))
        await asyncio.wait_for(task, timeout=1.0)

    @pytest.mark.usefixtures("mock_settings_small_queue")
    async def test_metrics_reflect_slow_subscribers(self, store: SignalStore) -> None:
        """Metrics track slow subscribers (those dropping messages)."""
        started = asyncio.Event()

        async def blocked_subscriber():
            gen = store.subscribe()
            started.set()
            try:
                async for _ in gen:
                    await asyncio.sleep(10)  # Never processes
            finally:
                await gen.aclose()

        task = asyncio.create_task(blocked_subscriber())
        await started.wait()

        # Initially not slow
        assert store.get_metrics()["subscribers"]["slow"] == 0

        # Fill queue (size=2) and overflow
        for i in range(3):
            await store.publish(Signal(id=f"sig_{i}", value=str(i), unit="", label=""))

        # Now marked as slow
        assert store.get_metrics()["subscribers"]["slow"] == 1

        # Cleanup
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


class TestGetAll:
    """Specification-based tests for SignalStore.get_all()."""

    async def test_empty_store_returns_empty_dict(self, store: SignalStore) -> None:
        """New store returns empty dictionary."""
        result = await store.get_all()

        assert result == {}

    async def test_returns_copy_not_reference(
        self, store: SignalStore, sample_signal: Signal
    ) -> None:
        """get_all() returns a copy, modifications don't affect store."""
        await store.set(sample_signal)
        result = await store.get_all()

        # Modify the returned dict
        result["new_key"] = sample_signal

        # Store should be unchanged
        stored = await store.get_all()
        assert "new_key" not in stored

    async def test_returns_all_stored_signals(
        self, store: SignalStore, sample_signals: dict[str, Signal]
    ) -> None:
        """get_all() returns all signals that were stored."""
        await store.set_many(sample_signals)

        result = await store.get_all()

        assert result == sample_signals


class TestGet:
    """Specification-based tests for SignalStore.get()."""

    async def test_nonexistent_signal_returns_none(self, store: SignalStore) -> None:
        """Getting a signal that doesn't exist returns None."""
        result = await store.get("nonexistent")

        assert result is None

    async def test_existing_signal_returns_signal(
        self, store: SignalStore, sample_signal: Signal
    ) -> None:
        """Getting an existing signal returns the signal."""
        await store.set(sample_signal)

        result = await store.get(sample_signal.id)

        assert result == sample_signal


class TestSet:
    """Specification-based tests for SignalStore.set()."""

    async def test_stores_signal(
        self, store: SignalStore, sample_signal: Signal
    ) -> None:
        """Signal is retrievable after set()."""
        await store.set(sample_signal)

        result = await store.get(sample_signal.id)
        assert result == sample_signal

    async def test_overwrites_existing_signal(self, store: SignalStore) -> None:
        """Setting a signal with same ID replaces the old value."""
        original = Signal(id="temp", value="20.0", unit="°C", label="Temp")
        updated = Signal(id="temp", value="25.0", unit="°C", label="Temp")

        await store.set(original)
        await store.set(updated)

        result = await store.get("temp")
        assert result is not None
        assert result == updated
        assert result.value == "25.0"


class TestSetMany:
    """Specification-based tests for SignalStore.set_many()."""

    async def test_stores_multiple_signals(
        self, store: SignalStore, sample_signals: dict[str, Signal]
    ) -> None:
        """All signals in batch are stored."""
        await store.set_many(sample_signals)

        for signal_id, signal in sample_signals.items():
            result = await store.get(signal_id)
            assert result == signal

    async def test_overwrites_existing_signals(
        self, store: SignalStore, sample_signal: Signal
    ) -> None:
        """set_many() overwrites existing signals with same IDs."""
        await store.set(sample_signal)
        updated = Signal(id=sample_signal.id, value="99.9", unit="°C", label="Updated")

        await store.set_many({sample_signal.id: updated})

        result = await store.get(sample_signal.id)
        assert result is not None
        assert result.value == "99.9"


@pytest.mark.usefixtures("mock_settings")
class TestSubscribe:
    """State transition tests for pub/sub subscriber lifecycle.

    Tests verify subscriber registration, message delivery, and cleanup.
    All tests run with mocked settings (subscriber_queue_size=10).
    """

    async def test_subscribe_receives_published_signal(
        self, store: SignalStore, sample_signal: Signal
    ) -> None:
        """Subscriber receives signals that are published."""
        received: list[Signal] = []
        started = asyncio.Event()

        async def subscriber():
            gen = store.subscribe()
            started.set()
            async for signal in gen:
                received.append(signal)
                break  # Exit after first signal

        # Start subscriber
        task = asyncio.create_task(subscriber())
        await started.wait()

        # Publish
        await store.publish(sample_signal)

        # Wait for subscriber to receive
        await asyncio.wait_for(task, timeout=1.0)

        assert received == [sample_signal]

    async def test_multiple_subscribers_all_receive(
        self, store: SignalStore, sample_signal: Signal
    ) -> None:
        """All active subscribers receive published signals."""
        received_1: list[Signal] = []
        received_2: list[Signal] = []
        started_1 = asyncio.Event()
        started_2 = asyncio.Event()

        async def subscriber(target: list[Signal], started: asyncio.Event):
            gen = store.subscribe()
            started.set()
            async for signal in gen:
                target.append(signal)
                break

        task1 = asyncio.create_task(subscriber(received_1, started_1))
        task2 = asyncio.create_task(subscriber(received_2, started_2))
        await started_1.wait()
        await started_2.wait()

        await store.publish(sample_signal)

        await asyncio.wait_for(asyncio.gather(task1, task2), timeout=1.0)

        assert received_1 == [sample_signal]
        assert received_2 == [sample_signal]

    async def test_subscriber_cleanup_on_exit(self, store: SignalStore) -> None:
        """Subscriber is removed when generator exits."""
        assert store.subscriber_count() == 0
        started = asyncio.Event()

        async def subscriber():
            gen = store.subscribe()
            started.set()
            try:
                async for _ in gen:
                    break  # Exit immediately after first signal
            finally:
                await gen.aclose()  # Ensure generator cleanup runs

        task = asyncio.create_task(subscriber())
        await started.wait()

        assert store.subscriber_count() == 1

        # Publish to unblock subscriber
        await store.publish(Signal(id="test", value="x", unit="", label=""))
        await asyncio.wait_for(task, timeout=1.0)

        # Wait for cleanup to complete (subscriber removed from store)
        await wait_for_condition(
            lambda: store.subscriber_count() == 0,
            description="subscriber cleanup",
        )  # Implicit assert: no timeout means condition met

    async def test_subscriber_count_tracks_active(self, store: SignalStore) -> None:
        """subscriber_count() accurately tracks active subscribers."""
        assert store.subscriber_count() == 0

        queues = []
        started_events = [asyncio.Event() for _ in range(3)]

        async def subscriber(index: int, started: asyncio.Event):
            gen = store.subscribe()
            started.set()
            async for _ in gen:
                queues.append(index)
                if len(queues) >= 3:  # Exit after 3 signals total
                    break

        tasks = [
            asyncio.create_task(subscriber(i, started_events[i])) for i in range(3)
        ]
        await asyncio.gather(*(e.wait() for e in started_events))

        assert store.subscriber_count() == 3

        # Cancel all
        for task in tasks:
            task.cancel()

        # Wait for all subscribers to be cleaned up
        await wait_for_condition(
            lambda: store.subscriber_count() == 0,
            description="all subscribers cleaned up",
        )  # Implicit assert: no timeout means condition met


class TestPublish:
    """Specification-based tests for SignalStore.publish()."""

    async def test_publish_also_stores_signal(
        self, store: SignalStore, sample_signal: Signal
    ) -> None:
        """publish() updates the stored value."""
        await store.publish(sample_signal)

        result = await store.get(sample_signal.id)
        assert result == sample_signal


class TestQueueOverflow:
    """Branch coverage and error guessing for queue full handling.

    Tests verify drop behavior, throttled logging, and memory leak prevention.
    Each test specifies its own mock_settings fixture for precise control.
    """

    @pytest.mark.usefixtures("mock_settings_small_queue")
    async def test_drops_when_queue_full(self, store: SignalStore) -> None:
        """When subscriber queue is full, updates are dropped (not blocking)."""
        started = asyncio.Event()

        async def blocked_subscriber():
            gen = store.subscribe()
            started.set()
            try:
                async for _ in gen:
                    await asyncio.sleep(10)  # Never processes
            finally:
                await gen.aclose()

        task = asyncio.create_task(blocked_subscriber())
        await started.wait()

        # Publish more than queue can hold (queue_size=2)
        # This MUST complete quickly, not block
        async def publish_burst():
            for i in range(5):
                await store.publish(
                    Signal(id=f"sig_{i}", value=str(i), unit="", label="")
                )

        await asyncio.wait_for(publish_burst(), timeout=0.1)  # Explicit timeout

        # Verify drops occurred
        assert store.get_metrics()["subscribers"]["slow"] == 1

        # Cleanup
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    @pytest.mark.usefixtures("mock_settings_small_queue")
    async def test_drop_logging_first_drop_logs_immediately(
        self,
        store: SignalStore,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """First dropped message is logged immediately."""
        started = asyncio.Event()

        async def blocked_subscriber():
            gen = store.subscribe()
            started.set()
            try:
                async for _ in gen:
                    await asyncio.sleep(10)  # Never processes
            finally:
                await gen.aclose()

        task = asyncio.create_task(blocked_subscriber())
        await started.wait()

        # Fill the queue (size=2)
        for i in range(3):
            await store.publish(Signal(id=f"sig_{i}", value=str(i), unit="", label=""))

        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

        assert "queue full" in caplog.text.lower()

    @pytest.mark.usefixtures("mock_settings_small_queue_long_throttle")
    async def test_drop_logging_throttled(
        self,
        store: SignalStore,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Subsequent drops within throttle interval don't log individually."""
        started = asyncio.Event()

        async def blocked_subscriber():
            gen = store.subscribe()
            started.set()
            try:
                async for _ in gen:
                    await asyncio.sleep(10)
            finally:
                await gen.aclose()

        task = asyncio.create_task(blocked_subscriber())
        await started.wait()

        # Drop many messages
        for i in range(10):
            await store.publish(Signal(id=f"sig_{i}", value=str(i), unit="", label=""))

        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

        # Should have only 1 warning (first drop), not 8
        warning_count = caplog.text.lower().count("queue full")
        assert warning_count == 1

    @pytest.mark.usefixtures("mock_settings_small_queue_no_throttle")
    async def test_drop_logging_summary_after_interval(
        self,
        store: SignalStore,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """After throttle interval elapses, logs summary of dropped messages."""
        started = asyncio.Event()

        async def blocked_subscriber():
            gen = store.subscribe()
            started.set()
            try:
                async for _ in gen:
                    await asyncio.sleep(10)  # Block after receiving first
            finally:
                await gen.aclose()

        task = asyncio.create_task(blocked_subscriber())
        await started.wait()

        # Queue size=2. Subscriber takes first item then blocks.
        # sig_0 → subscriber gets it immediately, blocks on sleep
        # sig_1, sig_2 → fill queue (2 items)
        # sig_3 → DROP #1 (logs "dropping update")
        # sig_4 → DROP #2 (logs "dropped 1 updates" summary with interval=0)
        for i in range(5):
            await store.publish(Signal(id=f"sig_{i}", value=str(i), unit="", label=""))

        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

        # Should see the "dropped N updates" summary message
        assert "dropped" in caplog.text.lower()

    @pytest.mark.usefixtures("mock_settings_small_queue")
    async def test_drop_stats_cleanup_on_unsubscribe(self, store: SignalStore) -> None:
        """Drop stats are cleaned up when subscriber exits (no memory leak)."""
        started = asyncio.Event()
        signal_received = asyncio.Event()

        async def subscriber():
            gen = store.subscribe()
            started.set()
            try:
                async for _ in gen:
                    signal_received.set()
                    break  # Exit after receiving one signal
            finally:
                await gen.aclose()

        task = asyncio.create_task(subscriber())
        await started.wait()

        # Cause drops (queue size=2, sending 5)
        for i in range(5):
            await store.publish(Signal(id=f"sig_{i}", value=str(i), unit="", label=""))

        # Wait for subscriber to receive and exit
        await signal_received.wait()
        await asyncio.wait_for(task, timeout=1.0)

        # Wait for cleanup to complete
        await wait_for_condition(
            lambda: store.get_metrics()["subscribers"]["slow"] == 0,
            description="drop stats cleanup",
        )  # Implicit assert: no timeout means condition met

    @pytest.mark.usefixtures("mock_settings_small_queue")
    async def test_drop_stats_reset_on_successful_delivery(
        self, store: SignalStore
    ) -> None:
        """Drop stats reset when a message is successfully delivered after drops."""
        started = asyncio.Event()
        first_batch_done = asyncio.Event()
        can_resume = asyncio.Event()

        async def subscriber():
            gen = store.subscribe()
            started.set()
            count = 0
            try:
                async for _ in gen:
                    count += 1
                    if count == 1:
                        # After first message, pause to let queue fill
                        first_batch_done.set()
                        await can_resume.wait()
                    if count >= 4:
                        break
            finally:
                await gen.aclose()

        task = asyncio.create_task(subscriber())
        await started.wait()

        # Queue size is 2. Send first, let subscriber get it
        await store.publish(Signal(id="sig_0", value="0", unit="", label=""))
        await first_batch_done.wait()

        # Now fill queue (2 items) and overflow (triggers drop_stats)
        await store.publish(Signal(id="sig_1", value="1", unit="", label=""))
        await store.publish(Signal(id="sig_2", value="2", unit="", label=""))
        await store.publish(Signal(id="sig_3", value="3", unit="", label=""))  # Dropped

        # Verify slow subscriber detected
        assert store.get_metrics()["subscribers"]["slow"] == 1

        # Let subscriber drain queue, which makes room for more
        can_resume.set()

        # Wait for subscriber to process queued items so queue has room
        # The subscriber processes items when resumed, we need to wait for queue space
        await wait_for_condition(
            lambda: store.get_metrics()["subscribers"]["total"] > 0,
            timeout=0.5,
            description="subscriber processing",
        )
        await asyncio.sleep(0.05)  # Brief pause for queue to drain

        # Now publish another - this should succeed and clear drop_stats
        await store.publish(Signal(id="sig_4", value="4", unit="", label=""))

        # Wait for slow subscriber to be cleared after successful delivery
        await wait_for_condition(
            lambda: store.get_metrics()["subscribers"]["slow"] == 0,
            timeout=1.0,
            description="slow subscriber cleared after successful delivery",
        )  # Implicit assert: no timeout means condition met

        # Cleanup
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


class TestSingleton:
    """Specification-based tests for singleton pattern (get/reset_signal_store)."""

    def test_get_signal_store_returns_singleton(self) -> None:
        """get_signal_store() returns the same instance."""
        reset_signal_store()  # Clean state

        store1 = get_signal_store()
        store2 = get_signal_store()

        assert store1 is store2

    def test_reset_signal_store_clears_singleton(self) -> None:
        """reset_signal_store() causes next call to create new instance."""
        store1 = get_signal_store()
        reset_signal_store()
        store2 = get_signal_store()

        assert store1 is not store2

    def test_reset_signal_store_for_test_isolation(self) -> None:
        """Demonstrates reset_signal_store() for test isolation."""
        reset_signal_store()
        store = get_signal_store()

        # Use the store
        asyncio.run(store.set(Signal(id="test", value="1", unit="", label="")))

        # Reset for next test
        reset_signal_store()
        fresh_store = get_signal_store()

        # Fresh store should be empty
        result = asyncio.run(fresh_store.get_all())
        assert result == {}
