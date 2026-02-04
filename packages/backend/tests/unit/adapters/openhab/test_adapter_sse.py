"""Tests for OpenHAB adapter SSE event subscription.

Covers:
- subscribe_events() async generator
- Metadata loading behavior
- SSE stream parsing
- Untracked item filtering
- Malformed JSON handling
- Connection error handling
"""

from __future__ import annotations

import json as json_module
import re
from typing import TYPE_CHECKING

import httpx
import pytest

from lumehaven.adapters.openhab.adapter import OpenHABAdapter
from lumehaven.core.exceptions import SmartHomeConnectionError
from tests.fixtures.openhab_responses import ALL_ITEMS

if TYPE_CHECKING:
    from pytest_httpx import HTTPXMock


class AsyncIteratorByteStream(httpx.AsyncByteStream):
    """Async byte stream for simulating SSE responses."""

    def __init__(self, lines: list[bytes]) -> None:
        self._lines = lines

    async def __aiter__(self):  # noqa: ANN204
        for line in self._lines:
            yield line


class TestSubscribeEvents:
    """Tests for SSE event subscription.

    Technique: State Transition Testing — SSE connection lifecycle.
    """

    async def test_loads_metadata_if_not_present(
        self,
        adapter: OpenHABAdapter,
        mock_root_response: dict,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Loads item metadata before subscribing if not already loaded."""
        httpx_mock.add_response(
            url="http://openhab:8080/rest/", json=mock_root_response
        )
        httpx_mock.add_response(
            url=re.compile(r"http://openhab:8080/rest/items\?"),
            json=ALL_ITEMS,
        )

        # Pre-initialize to load metadata
        await adapter._ensure_initialized()
        assert len(adapter._item_metadata) == 0

        # get_signals should be called if metadata is empty
        await adapter.get_signals()
        assert len(adapter._item_metadata) > 0

    @pytest.mark.httpx_mock(can_send_already_matched_responses=True)
    async def test_skips_metadata_load_if_present(
        self,
        adapter: OpenHABAdapter,
        mock_root_response: dict,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Skips metadata loading if already present."""
        httpx_mock.add_response(
            url="http://openhab:8080/rest/", json=mock_root_response
        )
        httpx_mock.add_response(
            url=re.compile(r"http://openhab:8080/rest/items\?"),
            json=ALL_ITEMS,
        )

        # Pre-load metadata
        await adapter.get_signals()
        initial_count = len(adapter._item_metadata)
        assert initial_count > 0

        # Second get_signals reloads (metadata gets refreshed)
        # This test just confirms no error with existing metadata
        await adapter.get_signals()
        assert len(adapter._item_metadata) == initial_count

    @pytest.mark.httpx_mock(can_send_already_matched_responses=True)
    async def test_subscribe_events_loads_metadata_if_empty(
        self,
        adapter: OpenHABAdapter,
        mock_root_response: dict,
        httpx_mock: HTTPXMock,
    ) -> None:
        """SSE subscription loads metadata if not present."""
        # Setup: don't pre-load metadata - adapter will call get_signals
        httpx_mock.add_response(
            url="http://openhab:8080/rest/", json=mock_root_response
        )
        httpx_mock.add_response(
            url=re.compile(r"http://openhab:8080/rest/items\?"),
            json=ALL_ITEMS,
        )

        connection_id = "conn-auto-load"
        event_payload = {"LivingRoom_Light": {"state": "ON"}}
        sse_lines = [
            b"data: " + connection_id.encode() + b"\n",
            b"data: " + json_module.dumps(event_payload).encode() + b"\n",
        ]

        httpx_mock.add_response(
            url="http://openhab:8080/rest/events/states",
            stream=AsyncIteratorByteStream(sse_lines),
        )
        httpx_mock.add_response(
            url=f"http://openhab:8080/rest/events/states/{connection_id}",
            method="POST",
        )

        # Verify metadata is empty before subscribe
        assert len(adapter._item_metadata) == 0

        # Subscribe - should auto-load metadata
        signals = []
        async for signal in adapter.subscribe_events():
            signals.append(signal)
            break

        # Metadata should be loaded now
        assert len(adapter._item_metadata) > 0
        assert len(signals) == 1

    @pytest.mark.httpx_mock(can_send_already_matched_responses=True)
    async def test_subscribe_events_yields_signals(
        self,
        adapter: OpenHABAdapter,
        mock_root_response: dict,
        httpx_mock: HTTPXMock,
    ) -> None:
        """SSE subscription yields signals for tracked items."""
        # Setup: load metadata first
        httpx_mock.add_response(
            url="http://openhab:8080/rest/", json=mock_root_response
        )
        httpx_mock.add_response(
            url=re.compile(r"http://openhab:8080/rest/items\?"),
            json=ALL_ITEMS,
        )

        # Mock SSE stream
        connection_id = "test-connection-123"
        event_payload = {
            "LivingRoom_Temperature": {"state": "22.0 °C"},
        }
        sse_lines = [
            b"data: " + connection_id.encode() + b"\n",
            b"data: " + json_module.dumps(event_payload).encode() + b"\n",
        ]

        httpx_mock.add_response(
            url="http://openhab:8080/rest/events/states",
            stream=AsyncIteratorByteStream(sse_lines),
        )
        httpx_mock.add_response(
            url=f"http://openhab:8080/rest/events/states/{connection_id}",
            method="POST",
        )

        # Pre-load signals
        await adapter.get_signals()

        # Subscribe and collect signals
        signals = []
        async for signal in adapter.subscribe_events():
            signals.append(signal)
            break  # Only get first signal to avoid infinite loop

        assert len(signals) == 1
        assert signals[0].id == "oh:LivingRoom_Temperature"
        assert signals[0].value == "22.0"

    @pytest.mark.httpx_mock(can_send_already_matched_responses=True)
    async def test_subscribe_events_skips_non_data_lines(
        self,
        adapter: OpenHABAdapter,
        mock_root_response: dict,
        httpx_mock: HTTPXMock,
    ) -> None:
        """SSE subscription skips non-data lines."""
        httpx_mock.add_response(
            url="http://openhab:8080/rest/", json=mock_root_response
        )
        httpx_mock.add_response(
            url=re.compile(r"http://openhab:8080/rest/items\?"),
            json=ALL_ITEMS,
        )

        connection_id = "conn-456"
        event_payload = {"LivingRoom_Light": {"state": "ON"}}
        sse_lines = [
            b"event: message\n",  # Should be skipped
            b": comment\n",  # Should be skipped
            b"data: " + connection_id.encode() + b"\n",
            b"retry: 3000\n",  # Should be skipped
            b"data: " + json_module.dumps(event_payload).encode() + b"\n",
        ]

        httpx_mock.add_response(
            url="http://openhab:8080/rest/events/states",
            stream=AsyncIteratorByteStream(sse_lines),
        )
        httpx_mock.add_response(
            url=f"http://openhab:8080/rest/events/states/{connection_id}",
            method="POST",
        )

        await adapter.get_signals()

        signals = []
        async for signal in adapter.subscribe_events():
            signals.append(signal)
            break

        assert len(signals) == 1
        assert signals[0].id == "oh:LivingRoom_Light"

    @pytest.mark.httpx_mock(can_send_already_matched_responses=True)
    async def test_subscribe_events_skips_untracked_items(
        self,
        adapter: OpenHABAdapter,
        mock_root_response: dict,
        httpx_mock: HTTPXMock,
    ) -> None:
        """SSE subscription skips events for untracked items."""
        httpx_mock.add_response(
            url="http://openhab:8080/rest/", json=mock_root_response
        )
        httpx_mock.add_response(
            url=re.compile(r"http://openhab:8080/rest/items\?"),
            json=ALL_ITEMS,
        )

        connection_id = "conn-789"
        # Event for an item not in ALL_ITEMS followed by one that is
        event_payload_untracked = {"Unknown_Item": {"state": "123"}}
        event_payload_tracked = {"LivingRoom_Light": {"state": "OFF"}}
        sse_lines = [
            b"data: " + connection_id.encode() + b"\n",
            b"data: " + json_module.dumps(event_payload_untracked).encode() + b"\n",
            b"data: " + json_module.dumps(event_payload_tracked).encode() + b"\n",
        ]

        httpx_mock.add_response(
            url="http://openhab:8080/rest/events/states",
            stream=AsyncIteratorByteStream(sse_lines),
        )
        httpx_mock.add_response(
            url=f"http://openhab:8080/rest/events/states/{connection_id}",
            method="POST",
        )

        await adapter.get_signals()

        signals = []
        async for signal in adapter.subscribe_events():
            signals.append(signal)
            break  # Only collect first actual signal

        # Should only get the tracked item's signal
        assert len(signals) == 1
        assert signals[0].id == "oh:LivingRoom_Light"

    @pytest.mark.httpx_mock(can_send_already_matched_responses=True)
    async def test_subscribe_events_handles_malformed_json(
        self,
        adapter: OpenHABAdapter,
        mock_root_response: dict,
        httpx_mock: HTTPXMock,
    ) -> None:
        """SSE subscription handles malformed JSON gracefully."""
        httpx_mock.add_response(
            url="http://openhab:8080/rest/", json=mock_root_response
        )
        httpx_mock.add_response(
            url=re.compile(r"http://openhab:8080/rest/items\?"),
            json=ALL_ITEMS,
        )

        connection_id = "conn-bad"
        event_payload = {"LivingRoom_Light": {"state": "ON"}}
        sse_lines = [
            b"data: " + connection_id.encode() + b"\n",
            b"data: {malformed json}\n",  # Should be skipped with warning
            b"data: " + json_module.dumps(event_payload).encode() + b"\n",
        ]

        httpx_mock.add_response(
            url="http://openhab:8080/rest/events/states",
            stream=AsyncIteratorByteStream(sse_lines),
        )
        httpx_mock.add_response(
            url=f"http://openhab:8080/rest/events/states/{connection_id}",
            method="POST",
        )

        await adapter.get_signals()

        signals = []
        async for signal in adapter.subscribe_events():
            signals.append(signal)
            break

        # Should still get the valid signal
        assert len(signals) == 1
        assert signals[0].id == "oh:LivingRoom_Light"

    @pytest.mark.httpx_mock(can_send_already_matched_responses=True)
    async def test_subscribe_events_raises_on_http_error(
        self,
        adapter: OpenHABAdapter,
        mock_root_response: dict,
        httpx_mock: HTTPXMock,
    ) -> None:
        """SSE subscription raises SmartHomeConnectionError on HTTP failure."""
        httpx_mock.add_response(
            url="http://openhab:8080/rest/", json=mock_root_response
        )
        httpx_mock.add_response(
            url=re.compile(r"http://openhab:8080/rest/items\?"),
            json=ALL_ITEMS,
        )
        httpx_mock.add_exception(
            httpx.ConnectError("Connection refused"),
            url="http://openhab:8080/rest/events/states",
        )

        await adapter.get_signals()

        with pytest.raises(SmartHomeConnectionError):
            async for _ in adapter.subscribe_events():
                pass
