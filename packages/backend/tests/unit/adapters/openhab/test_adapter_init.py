"""Tests for OpenHAB adapter initialization and lifecycle.

Covers:
- Constructor behavior and defaults
- Connection state management
- Client lifecycle (open/close)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lumehaven.adapters.openhab.adapter import OpenHABAdapter

if TYPE_CHECKING:
    from pytest_httpx import HTTPXMock


class TestAdapterInit:
    """Tests for OpenHABAdapter initialization.

    Technique: Specification-based Testing — verifying constructor contracts.
    """

    def test_init_with_defaults(self) -> None:
        """Adapter initializes with default name and prefix."""
        adapter = OpenHABAdapter(base_url="http://openhab:8080")

        assert adapter.name == "openhab"
        assert adapter.prefix == "oh"
        assert adapter.adapter_type == "openhab"
        assert adapter.base_url == "http://openhab:8080"
        assert adapter.tag == ""

    def test_init_with_custom_values(self) -> None:
        """Adapter accepts custom name, prefix, and tag."""
        adapter = OpenHABAdapter(
            base_url="http://custom:9090/",
            tag="MyTag",
            name="custom_openhab",
            prefix="co",
        )

        assert adapter.name == "custom_openhab"
        assert adapter.prefix == "co"
        assert adapter.base_url == "http://custom:9090"  # trailing slash stripped
        assert adapter.tag == "MyTag"


class TestAdapterLifecycle:
    """Tests for adapter lifecycle management.

    Technique: State Transition Testing — connection states.
    """

    async def test_is_connected_initially_false(self, adapter: OpenHABAdapter) -> None:
        """Adapter is not connected initially."""
        assert not adapter.is_connected()

    async def test_is_connected_after_request(
        self,
        adapter: OpenHABAdapter,
        mock_root_response: dict,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Adapter is connected after making a request."""
        httpx_mock.add_response(
            url="http://openhab:8080/rest/", json=mock_root_response
        )

        await adapter._get_measurement_system()

        assert adapter.is_connected()

    async def test_close_disconnects(
        self,
        adapter: OpenHABAdapter,
        mock_root_response: dict,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Closing adapter disconnects the client."""
        httpx_mock.add_response(
            url="http://openhab:8080/rest/", json=mock_root_response
        )
        await adapter._get_measurement_system()
        assert adapter.is_connected()

        await adapter.close()

        assert not adapter.is_connected()

    async def test_close_idempotent(self, adapter: OpenHABAdapter) -> None:
        """Closing an unconnected adapter is safe."""
        await adapter.close()  # Should not raise

        assert not adapter.is_connected()
