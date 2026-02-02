"""Tests for OpenHAB adapter API methods.

Covers:
- get_signals() — fetching all signals
- get_signal() — fetching single signal
- _get_measurement_system() — SI/US detection
- HTTP error handling
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import httpx
import pytest

from lumehaven.adapters.openhab.adapter import OpenHABAdapter
from lumehaven.core.exceptions import SignalNotFoundError, SmartHomeConnectionError
from tests.fixtures.openhab_responses import ALL_ITEMS, TEMPERATURE_ITEM

if TYPE_CHECKING:
    from pytest_httpx import HTTPXMock


class TestMeasurementSystem:
    """Tests for measurement system detection from OpenHAB root endpoint.

    Technique: Equivalence Partitioning — SI vs US measurement systems.
    """

    async def test_detects_si_measurement_system(
        self,
        adapter: OpenHABAdapter,
        mock_root_response: dict,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Correctly detects SI measurement system."""
        httpx_mock.add_response(
            url="http://openhab:8080/rest/", json=mock_root_response
        )

        system = await adapter._get_measurement_system()

        assert system == "SI"

    async def test_detects_us_measurement_system(
        self,
        adapter: OpenHABAdapter,
        mock_root_response_us: dict,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Correctly detects US measurement system."""
        httpx_mock.add_response(
            url="http://openhab:8080/rest/", json=mock_root_response_us
        )

        system = await adapter._get_measurement_system()

        assert system == "US"

    async def test_defaults_to_si_for_unknown(
        self, adapter: OpenHABAdapter, httpx_mock: HTTPXMock
    ) -> None:
        """Defaults to SI for unknown measurement system."""
        httpx_mock.add_response(
            url="http://openhab:8080/rest/",
            json={"measurementSystem": "METRIC"},  # Invalid value
        )

        system = await adapter._get_measurement_system()

        assert system == "SI"

    async def test_raises_connection_error_on_failure(
        self, adapter: OpenHABAdapter, httpx_mock: HTTPXMock
    ) -> None:
        """Raises SmartHomeConnectionError when connection fails."""
        httpx_mock.add_exception(httpx.ConnectError("Connection refused"))

        with pytest.raises(SmartHomeConnectionError) as exc_info:
            await adapter._get_measurement_system()

        assert "openhab" in str(exc_info.value)


class TestGetSignals:
    """Tests for fetching all signals from OpenHAB.

    Technique: Specification-based Testing — verifying get_signals() contract.
    """

    async def test_fetches_all_signals(
        self,
        adapter: OpenHABAdapter,
        mock_root_response: dict,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Fetches and converts all items to signals."""
        httpx_mock.add_response(
            url="http://openhab:8080/rest/", json=mock_root_response
        )
        httpx_mock.add_response(
            url=re.compile(r"http://openhab:8080/rest/items\?"),
            json=ALL_ITEMS,
        )

        signals = await adapter.get_signals()

        assert len(signals) == len(ALL_ITEMS)
        assert "oh:LivingRoom_Temperature" in signals

    async def test_raises_on_connection_error(
        self,
        adapter: OpenHABAdapter,
        mock_root_response: dict,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Raises SmartHomeConnectionError on HTTP failure."""
        httpx_mock.add_response(
            url="http://openhab:8080/rest/", json=mock_root_response
        )
        httpx_mock.add_exception(
            httpx.ConnectError("Connection refused"),
            url=re.compile(r"http://openhab:8080/rest/items\?"),
        )

        with pytest.raises(SmartHomeConnectionError):
            await adapter.get_signals()


class TestGetSignal:
    """Tests for fetching a single signal from OpenHAB.

    Technique: Specification-based Testing — verifying get_signal() contract.
    """

    async def test_fetches_single_signal(
        self,
        adapter: OpenHABAdapter,
        mock_root_response: dict,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Fetches and converts a single item to signal."""
        httpx_mock.add_response(
            url="http://openhab:8080/rest/", json=mock_root_response
        )
        httpx_mock.add_response(
            url=re.compile(r"http://openhab:8080/rest/items/LivingRoom_Temperature"),
            json=TEMPERATURE_ITEM,
        )

        signal = await adapter.get_signal("LivingRoom_Temperature")

        assert signal.id == "oh:LivingRoom_Temperature"
        assert signal.unit == "°C"

    async def test_raises_not_found_for_missing_item(
        self,
        adapter: OpenHABAdapter,
        mock_root_response: dict,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Raises SignalNotFoundError for 404 response."""
        httpx_mock.add_response(
            url="http://openhab:8080/rest/", json=mock_root_response
        )
        httpx_mock.add_response(
            url=re.compile(r"http://openhab:8080/rest/items/NonExistent"),
            status_code=404,
        )

        with pytest.raises(SignalNotFoundError) as exc_info:
            await adapter.get_signal("NonExistent")

        assert "NonExistent" in str(exc_info.value)


class TestGetSignalHTTPStatusError:
    """Tests for HTTP status error handling in get_signal.

    Technique: Error Guessing — various HTTP error codes.
    """

    async def test_raises_connection_error_for_non_404_status(
        self,
        adapter: OpenHABAdapter,
        mock_root_response: dict,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Raises SmartHomeConnectionError for non-404 HTTP errors."""
        httpx_mock.add_response(
            url="http://openhab:8080/rest/", json=mock_root_response
        )
        httpx_mock.add_response(
            url=re.compile(r"http://openhab:8080/rest/items/ServerError"),
            status_code=500,
        )

        with pytest.raises(SmartHomeConnectionError):
            await adapter.get_signal("ServerError")
