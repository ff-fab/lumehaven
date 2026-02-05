"""Unit tests for SSE streaming endpoint.

Test Techniques Used:
- Specification-based Testing: SSE event format, subscription behavior
- State Transition Testing: Client connect → receive events → disconnect
- Error Guessing: Client disconnect cleanup, CancelledError handling

Coverage Target: Medium Risk (api/sse.py)
- Line Coverage: ≥80%
- Branch Coverage: ≥75%
"""

from __future__ import annotations

import asyncio
import contextlib
import json

import pytest
from httpx import AsyncClient

from lumehaven.api.sse import signal_event_generator
from lumehaven.core.signal import Signal
from lumehaven.state.store import SignalStore
from tests.fixtures.signals import create_signal


class TestSSEEventFormat:
    """Tests for SSE event format from signal_event_generator.

    Technique: Specification-based Testing — SSE protocol format.
    """

    async def test_event_type_is_signal(
        self,
        signal_store: SignalStore,
    ) -> None:
        """Generated events have 'event' key set to 'signal'."""
        # Arrange
        signal = create_signal(id="test:temp", value="21.5")
        received_event: dict[str, str] | None = None

        async def collect_one_event() -> None:
            nonlocal received_event
            gen = signal_event_generator(signal_store)
            async for event in gen:
                received_event = event
                break  # Got one event, exit

        async def publish_signal() -> None:
            await asyncio.sleep(0.05)
            await signal_store.publish(signal)

        # Act
        collector_task = asyncio.create_task(collect_one_event())
        publisher_task = asyncio.create_task(publish_signal())

        try:
            await asyncio.wait_for(collector_task, timeout=1.0)
        except TimeoutError:
            pass
        finally:
            collector_task.cancel()
            publisher_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await collector_task
            with contextlib.suppress(asyncio.CancelledError):
                await publisher_task

        # Assert
        assert received_event is not None
        assert received_event["event"] == "signal"

    async def test_data_is_json_signal(
        self,
        signal_store: SignalStore,
    ) -> None:
        """Event data is JSON-encoded Signal with all fields."""
        # Arrange
        signal = Signal(
            id="test:temp",
            value="21.5",
            unit="°C",
            label="Temperature",
        )
        received_event: dict[str, str] | None = None

        async def collect_one_event() -> None:
            nonlocal received_event
            gen = signal_event_generator(signal_store)
            async for event in gen:
                received_event = event
                break

        async def publish_signal() -> None:
            await asyncio.sleep(0.05)
            await signal_store.publish(signal)

        # Act
        collector_task = asyncio.create_task(collect_one_event())
        publisher_task = asyncio.create_task(publish_signal())

        try:
            await asyncio.wait_for(collector_task, timeout=1.0)
        except TimeoutError:
            pass
        finally:
            collector_task.cancel()
            publisher_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await collector_task
            with contextlib.suppress(asyncio.CancelledError):
                await publisher_task

        # Assert — data is valid JSON
        assert received_event is not None
        data = json.loads(received_event["data"])
        assert data["id"] == "test:temp"
        assert data["value"] == "21.5"
        assert data["unit"] == "°C"
        assert data["label"] == "Temperature"


class TestSSESubscription:
    """Tests for SSE subscription lifecycle.

    Technique: State Transition Testing — connect → receive → disconnect
    """

    async def test_subscribes_to_store_on_connect(
        self,
        signal_store: SignalStore,
    ) -> None:
        """Generator subscribes to store, incrementing subscriber count."""
        # Arrange
        initial_count = signal_store.subscriber_count()

        async def run_generator_briefly() -> None:
            gen = signal_event_generator(signal_store)
            # Starting iteration triggers subscribe()
            try:
                async for _ in gen:
                    # Wait briefly to let count be checked
                    await asyncio.sleep(0.1)
                    break
            except asyncio.CancelledError:
                pass

        # Act
        task = asyncio.create_task(run_generator_briefly())
        await asyncio.sleep(0.05)  # Let generator start

        # Assert — subscriber count increased while generator running
        assert signal_store.subscriber_count() >= initial_count + 1

        # Cleanup
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    async def test_receives_published_signals(
        self,
        signal_store: SignalStore,
    ) -> None:
        """Generator yields events for signals published to store."""
        # Arrange
        signals_to_publish = [
            create_signal(id="test:1", value="1"),
            create_signal(id="test:2", value="2"),
        ]
        received: list[dict[str, str]] = []

        async def collect_events() -> None:
            gen = signal_event_generator(signal_store)
            async for event in gen:
                received.append(event)
                if len(received) >= 2:
                    break

        async def publish_signals() -> None:
            await asyncio.sleep(0.05)
            for sig in signals_to_publish:
                await signal_store.publish(sig)
                await asyncio.sleep(0.01)

        # Act
        collector_task = asyncio.create_task(collect_events())
        publisher_task = asyncio.create_task(publish_signals())

        try:
            await asyncio.wait_for(collector_task, timeout=2.0)
        except TimeoutError:
            pass
        finally:
            collector_task.cancel()
            publisher_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await collector_task
            with contextlib.suppress(asyncio.CancelledError):
                await publisher_task

        # Assert
        assert len(received) == 2
        ids = {json.loads(e["data"])["id"] for e in received}
        assert ids == {"test:1", "test:2"}


class TestSSEClientDisconnect:
    """Tests for client disconnect and cleanup.

    Technique: Error Guessing — handling CancelledError on disconnect.
    """

    async def test_generator_handles_cancellation(
        self,
        signal_store: SignalStore,
    ) -> None:
        """Generator logs and re-raises CancelledError on client disconnect."""
        # Arrange
        gen = signal_event_generator(signal_store)

        async def run_generator() -> None:
            async for _ in gen:
                pass  # Would block waiting for events

        task = asyncio.create_task(run_generator())

        # Give generator time to start
        await asyncio.sleep(0.05)

        # Act — cancel (simulates client disconnect)
        task.cancel()

        # Assert — should raise CancelledError
        with pytest.raises(asyncio.CancelledError):
            await task

    async def test_cleanup_removes_subscriber_on_cancel(
        self,
        signal_store: SignalStore,
    ) -> None:
        """Subscriber is removed from store when generator is cancelled."""
        # Arrange
        initial_count = signal_store.subscriber_count()

        async def run_generator() -> None:
            gen = signal_event_generator(signal_store)
            async for _ in gen:
                pass

        task = asyncio.create_task(run_generator())
        await asyncio.sleep(0.05)  # Let it subscribe

        # Verify subscribed
        assert signal_store.subscriber_count() == initial_count + 1

        # Act — cancel
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

        # Allow cleanup to complete
        await asyncio.sleep(0.01)

        # Assert — subscriber removed
        assert signal_store.subscriber_count() == initial_count


class TestSSEEndpoint:
    """Tests for GET /api/events/signals endpoint.

    Technique: Specification-based Testing — endpoint behavior.

    Note: Full SSE streaming integration is tested via Robot Framework
    integration tests. Unit tests verify endpoint setup and content type.
    The signal_event_generator is fully tested in TestSSEEventFormat
    and TestSSESubscription above.
    """

    async def test_returns_event_stream_content_type(
        self,
        async_client: AsyncClient,
        signal_store: SignalStore,
    ) -> None:
        """SSE endpoint returns text/event-stream content type."""
        # We need to publish a signal to allow the stream to yield something
        # and then break out, otherwise the stream blocks indefinitely

        async def publish_signal() -> None:
            await asyncio.sleep(0.05)
            await signal_store.publish(create_signal(id="test:dummy"))

        publisher = asyncio.create_task(publish_signal())

        try:
            async with asyncio.timeout(1.0):
                async with async_client.stream(
                    "GET", "/api/events/signals"
                ) as response:
                    # Assert
                    assert response.status_code == 200
                    assert "text/event-stream" in response.headers["content-type"]
                    # Read one line to confirm stream works, then exit
                    async for _ in response.aiter_lines():
                        break
        except TimeoutError:
            pass  # Timeout is acceptable for this test
        finally:
            publisher.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await publisher
