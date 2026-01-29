"""Unit tests for the SignalStore."""

import asyncio

import pytest

from lumehaven.core.signal import Signal
from lumehaven.state.store import SignalStore, reset_signal_store


@pytest.fixture
def store() -> SignalStore:
    """Create a fresh SignalStore for each test."""
    reset_signal_store()
    return SignalStore()


@pytest.fixture
def sample_signals() -> dict[str, Signal]:
    """Sample signals for testing."""
    return {
        "temp1": Signal(id="temp1", value="21.5", unit="°C", label="Temperature 1"),
        "temp2": Signal(id="temp2", value="22.0", unit="°C", label="Temperature 2"),
        "switch": Signal(id="switch", value="ON", unit="", label="Light Switch"),
    }


class TestSignalStore:
    """Tests for SignalStore."""

    @pytest.mark.asyncio
    async def test_set_and_get(self, store: SignalStore) -> None:
        """Can store and retrieve a signal."""
        signal = Signal(id="test", value="123", unit="W")

        await store.set(signal)
        result = await store.get("test")

        assert result == signal

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, store: SignalStore) -> None:
        """Getting nonexistent signal returns None."""
        result = await store.get("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_all_empty(self, store: SignalStore) -> None:
        """Empty store returns empty dict."""
        result = await store.get_all()

        assert result == {}

    @pytest.mark.asyncio
    async def test_set_many(
        self, store: SignalStore, sample_signals: dict[str, Signal]
    ) -> None:
        """Can store multiple signals at once."""
        await store.set_many(sample_signals)
        result = await store.get_all()

        assert len(result) == 3
        assert result["temp1"] == sample_signals["temp1"]
        assert result["temp2"] == sample_signals["temp2"]
        assert result["switch"] == sample_signals["switch"]

    @pytest.mark.asyncio
    async def test_get_all_returns_copy(
        self, store: SignalStore, sample_signals: dict[str, Signal]
    ) -> None:
        """get_all returns a copy, not the internal dict."""
        await store.set_many(sample_signals)
        result = await store.get_all()

        # Modify the result
        result["new"] = Signal(id="new", value="x")

        # Internal store unchanged
        assert "new" not in await store.get_all()

    @pytest.mark.asyncio
    async def test_update_existing(self, store: SignalStore) -> None:
        """Setting a signal with existing ID updates it."""
        signal1 = Signal(id="test", value="old")
        signal2 = Signal(id="test", value="new")

        await store.set(signal1)
        await store.set(signal2)
        result = await store.get("test")

        assert result is not None
        assert result.value == "new"


class TestSignalStorePubSub:
    """Tests for SignalStore pub/sub functionality."""

    @pytest.mark.asyncio
    async def test_subscribe_receives_published(self, store: SignalStore) -> None:
        """Subscribers receive published signals."""
        signal = Signal(id="test", value="123")
        received: list[Signal] = []

        async def subscriber() -> None:
            async for s in store.subscribe():
                received.append(s)
                break  # Only receive one

        # Start subscriber
        task = asyncio.create_task(subscriber())

        # Give subscriber time to start
        await asyncio.sleep(0.01)

        # Publish
        await store.publish(signal)

        # Wait for subscriber
        await asyncio.wait_for(task, timeout=1.0)

        assert len(received) == 1
        assert received[0] == signal

    @pytest.mark.asyncio
    async def test_publish_updates_store(self, store: SignalStore) -> None:
        """Publishing a signal also updates the store."""
        signal = Signal(id="test", value="123")

        await store.publish(signal)
        result = await store.get("test")

        assert result == signal

    @pytest.mark.asyncio
    async def test_subscriber_count(self, store: SignalStore) -> None:
        """subscriber_count tracks active subscribers."""
        assert store.subscriber_count() == 0

        async def dummy_subscriber() -> None:
            async for _ in store.subscribe():
                break

        task = asyncio.create_task(dummy_subscriber())
        await asyncio.sleep(0.01)

        assert store.subscriber_count() == 1

        # Publish to complete the subscriber
        await store.publish(Signal(id="x", value="x"))
        await asyncio.wait_for(task, timeout=1.0)

        assert store.subscriber_count() == 0

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self, store: SignalStore) -> None:
        """Multiple subscribers all receive the same signal."""
        signal = Signal(id="test", value="123")
        received1: list[Signal] = []
        received2: list[Signal] = []

        async def subscriber1() -> None:
            async for s in store.subscribe():
                received1.append(s)
                break

        async def subscriber2() -> None:
            async for s in store.subscribe():
                received2.append(s)
                break

        task1 = asyncio.create_task(subscriber1())
        task2 = asyncio.create_task(subscriber2())
        await asyncio.sleep(0.01)

        await store.publish(signal)

        await asyncio.wait_for(task1, timeout=1.0)
        await asyncio.wait_for(task2, timeout=1.0)

        assert received1 == [signal]
        assert received2 == [signal]
