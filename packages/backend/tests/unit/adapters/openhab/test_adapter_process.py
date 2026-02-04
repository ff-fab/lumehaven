"""Tests for OpenHAB adapter event processing via subscribe_events().

Tests event processing branches for different item types:
- QuantityType events with unit extraction (E1 branch)
- Events with displayState field (E2 branch)
- Events with raw state only (E3 branch)
- Error handling (unknown items, encoding issues, exceptions)

Test Techniques Used:
- Branch Coverage: E1/E2/E3 processing branches
- Error Guessing: Malformed data, encoding issues
- Equivalence Partitioning: Item types (quantity, display, raw)

Note: Tests exercise the internal _process_event logic through the public
subscribe_events() API to avoid coupling to private implementation details.
"""

from __future__ import annotations

import json as json_module
import re
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

import httpx
import pytest

from lumehaven.adapters.openhab.adapter import OpenHABAdapter
from tests.fixtures.openhab_responses import (
    DIMENSIONLESS_ITEM,
    TEMPERATURE_ITEM,
    TRANSFORMED_ITEM,
)

if TYPE_CHECKING:
    from pytest_httpx import HTTPXMock


class AsyncIteratorByteStream(httpx.AsyncByteStream):
    """Async byte stream for simulating SSE responses."""

    def __init__(self, lines: list[bytes]) -> None:
        self._lines = lines

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for line in self._lines:
            yield line


def _make_sse_stream(
    connection_id: str, payloads: list[dict]
) -> AsyncIteratorByteStream:
    """Create SSE byte stream with connection ID and payloads."""
    lines = [b"data: " + connection_id.encode() + b"\n"]
    for payload in payloads:
        lines.append(b"data: " + json_module.dumps(payload).encode() + b"\n")
    return AsyncIteratorByteStream(lines)


@pytest.mark.httpx_mock(can_send_already_matched_responses=True)
class TestProcessEventQuantityType:
    """Tests for processing events from QuantityType items.

    Technique: Branch Coverage — E1: event_state_contains_unit.
    """

    async def test_formats_quantity_type_event(
        self,
        adapter: OpenHABAdapter,
        mock_root_response: dict,
        httpx_mock: HTTPXMock,
    ) -> None:
        """QuantityType events are formatted with unit extraction."""
        # Use only TEMPERATURE_ITEM for clean metadata
        items = [TEMPERATURE_ITEM]
        httpx_mock.add_response(
            url="http://openhab:8080/rest/", json=mock_root_response
        )
        httpx_mock.add_response(
            url=re.compile(r"http://openhab:8080/rest/items\?"),
            json=items,
        )

        connection_id = "conn-qty"
        event_payload = {TEMPERATURE_ITEM["name"]: {"state": "22.5 °C"}}

        httpx_mock.add_response(
            url="http://openhab:8080/rest/events/states",
            stream=_make_sse_stream(connection_id, [event_payload]),
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
        assert signals[0].value == "22.5"
        assert signals[0].unit == "°C"


@pytest.mark.httpx_mock(can_send_already_matched_responses=True)
class TestProcessEventDisplayState:
    """Tests for processing events with displayState field.

    Technique: Branch Coverage — E2: displayState present.
    """

    async def test_uses_display_state_when_present(
        self,
        adapter: OpenHABAdapter,
        mock_root_response: dict,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Uses displayState field when available and not quantity type."""
        items = [TRANSFORMED_ITEM]
        httpx_mock.add_response(
            url="http://openhab:8080/rest/", json=mock_root_response
        )
        httpx_mock.add_response(
            url=re.compile(r"http://openhab:8080/rest/items\?"),
            json=items,
        )

        connection_id = "conn-display"
        event_payload = {
            TRANSFORMED_ITEM["name"]: {
                "state": "4224248.0",
                "displayState": "48d 21h",
            }
        }

        httpx_mock.add_response(
            url="http://openhab:8080/rest/events/states",
            stream=_make_sse_stream(connection_id, [event_payload]),
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
        assert signals[0].value == "48d 21h"  # Uses displayState, not raw state


@pytest.mark.httpx_mock(can_send_already_matched_responses=True)
class TestProcessEventRawState:
    """Tests for processing events without displayState.

    Technique: Branch Coverage — E3: use raw state.
    """

    async def test_uses_raw_state_when_no_display_state(
        self,
        adapter: OpenHABAdapter,
        mock_root_response: dict,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Falls back to raw state when displayState not present."""
        items = [DIMENSIONLESS_ITEM]
        httpx_mock.add_response(
            url="http://openhab:8080/rest/", json=mock_root_response
        )
        httpx_mock.add_response(
            url=re.compile(r"http://openhab:8080/rest/items\?"),
            json=items,
        )

        connection_id = "conn-raw"
        event_payload = {DIMENSIONLESS_ITEM["name"]: {"state": "75"}}

        httpx_mock.add_response(
            url="http://openhab:8080/rest/events/states",
            stream=_make_sse_stream(connection_id, [event_payload]),
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
        # Value is formatted via %.1f pattern from DIMENSIONLESS_ITEM
        assert signals[0].value == "75.0"


@pytest.mark.httpx_mock(can_send_already_matched_responses=True)
class TestProcessEventErrorHandling:
    """Tests for error handling in event processing.

    Technique: Error Guessing — encoding issues, exception handling.
    """

    async def test_handles_encoding_issues(
        self,
        adapter: OpenHABAdapter,
        mock_root_response: dict,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Fixes encoding issues using ftfy."""
        items = [TEMPERATURE_ITEM]
        httpx_mock.add_response(
            url="http://openhab:8080/rest/", json=mock_root_response
        )
        httpx_mock.add_response(
            url=re.compile(r"http://openhab:8080/rest/items\?"),
            json=items,
        )

        connection_id = "conn-encoding"
        # Double-encoded UTF-8: "Â°C" should become "°C"
        event_payload = {TEMPERATURE_ITEM["name"]: {"state": "22.5 Â°C"}}

        httpx_mock.add_response(
            url="http://openhab:8080/rest/events/states",
            stream=_make_sse_stream(connection_id, [event_payload]),
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
        # ftfy should fix the encoding
        assert "Â" not in signals[0].value


@pytest.mark.httpx_mock(can_send_already_matched_responses=True)
class TestProcessEventException:
    """Tests for exception handling in _process_event.

    Technique: Error Guessing — exception in processing path.
    """

    async def test_skips_events_with_none_state(
        self,
        adapter: OpenHABAdapter,
        mock_root_response: dict,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Skips events with None state without raising."""
        items = [TEMPERATURE_ITEM]
        httpx_mock.add_response(
            url="http://openhab:8080/rest/", json=mock_root_response
        )
        httpx_mock.add_response(
            url=re.compile(r"http://openhab:8080/rest/items\?"),
            json=items,
        )

        connection_id = "conn-none"
        # Event with None state followed by valid event
        event_payloads = [
            {TEMPERATURE_ITEM["name"]: {"state": None}},
            {TEMPERATURE_ITEM["name"]: {"state": "21.0 °C"}},
        ]

        httpx_mock.add_response(
            url="http://openhab:8080/rest/events/states",
            stream=_make_sse_stream(connection_id, event_payloads),
        )
        httpx_mock.add_response(
            url=f"http://openhab:8080/rest/events/states/{connection_id}",
            method="POST",
        )

        await adapter.get_signals()

        signals = []
        async for signal in adapter.subscribe_events():
            signals.append(signal)
            break  # Get first valid signal

        # Should get the valid signal, None was skipped
        assert len(signals) == 1
        assert signals[0].value == "21.0"
