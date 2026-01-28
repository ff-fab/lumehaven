"""OpenHAB adapter implementation.

This adapter connects to OpenHAB's REST API and converts items to Signals.
It handles the complexity of OpenHAB's data model, including:
- QuantityTypes with units (e.g., Number:Temperature)
- State patterns for formatting (e.g., "%.1f °C")
- Transformed states
- Special values (UNDEF, NULL)

"""

import json
import logging
from collections.abc import AsyncIterator
from typing import Any, Literal

import httpx
from ftfy import fix_encoding

from lumehaven.adapters.openhab.units import (
    extract_unit_from_pattern,
    format_value,
    get_default_units,
)
from lumehaven.core.exceptions import SignalNotFoundError, SmartHomeConnectionError
from lumehaven.core.signal import Signal

logger = logging.getLogger(__name__)

# HTTP client configuration
# Generous defaults for local network communication with OpenHAB
REQUEST_TIMEOUT_SECONDS = 30.0
CONNECT_TIMEOUT_SECONDS = 10.0

# URL-encoded comma for query parameters
COMMA = "%2C"

# Fields to request from OpenHAB REST API
ITEM_FIELDS = ["name", "label", "state", "type", "stateDescription", "transformedState"]


class OpenHABAdapter:
    """Adapter for OpenHAB smart home system.

    Implements the SmartHomeAdapter protocol for OpenHAB.
    Uses httpx for async HTTP and SSE communication.

    Attributes:
        name: Unique identifier for this adapter instance.
        prefix: Short prefix for signal ID namespacing.
        base_url: OpenHAB REST API base URL.
        tag: Optional tag to filter items.
    """

    def __init__(
        self,
        base_url: str,
        tag: str = "",
        *,
        name: str | None = None,
        prefix: str | None = None,
    ) -> None:
        """Initialize the OpenHAB adapter.

        Args:
            base_url: Base URL for OpenHAB REST API (e.g., "http://localhost:8080").
            tag: Filter items by this tag (empty string = all items).
            name: Unique identifier for this adapter instance. Defaults to "openhab".
            prefix: Short prefix for signal IDs. Defaults to "oh".
        """
        self._name = name or "openhab"
        self._prefix = prefix or "oh"
        self.base_url = base_url.rstrip("/")
        self.tag = tag
        self._client: httpx.AsyncClient | None = None
        self._default_units: dict[str, str] = {}
        self._item_metadata: dict[str, _ItemMetadata] = {}

    @property
    def name(self) -> str:
        """Unique identifier for this adapter instance."""
        return self._name

    @property
    def adapter_type(self) -> str:
        """The type of smart home system: 'openhab'."""
        return "openhab"

    @property
    def prefix(self) -> str:
        """Short prefix for signal ID namespacing."""
        return self._prefix

    def _prefixed_id(self, item_name: str) -> str:
        """Create a namespaced signal ID from an OpenHAB item name.

        Args:
            item_name: The OpenHAB item name.

        Returns:
            Signal ID in format "prefix:item_name".
        """
        return f"{self._prefix}:{item_name}"

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(
                    REQUEST_TIMEOUT_SECONDS,
                    connect=CONNECT_TIMEOUT_SECONDS,
                ),
            )
        return self._client

    async def _get_sse_client(self) -> httpx.AsyncClient:
        """Get or create SSE client with disabled read timeout.

        SSE connections are long-lived and should not timeout on idle reads.
        Returns a separate client configured for streaming.
        """
        # Create a new client with read timeout disabled for SSE
        return httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(
                REQUEST_TIMEOUT_SECONDS,
                connect=CONNECT_TIMEOUT_SECONDS,
                read=None,
            ),
        )

    async def _ensure_initialized(self) -> None:
        """Ensure default units are loaded."""
        if not self._default_units:
            system = await self._get_measurement_system()
            self._default_units = get_default_units(system)

    async def _get_measurement_system(self) -> Literal["SI", "US"]:
        """Get the measurement system configured in OpenHAB."""
        try:
            client = await self._get_client()
            response = await client.get("/rest/")
            response.raise_for_status()
            data: dict[str, Any] = response.json()
            system = data.get("measurementSystem", "SI")
            # OpenHAB only returns "SI" or "US", default to SI for safety
            return system if system in ("SI", "US") else "SI"
        except httpx.HTTPError as e:
            raise SmartHomeConnectionError("openhab", self.base_url, e) from e

    async def get_signals(self) -> dict[str, Signal]:
        """Retrieve all signals from OpenHAB.

        Returns:
            Dictionary mapping item names to Signal objects.

        Raises:
            SmartHomeConnectionError: If connection fails.
        """
        await self._ensure_initialized()

        try:
            client = await self._get_client()

            # Build query parameters
            params = f"recursive=false&fields={COMMA.join(ITEM_FIELDS)}"
            if self.tag:
                params = f"tags={self.tag}&{params}"

            response = await client.get(f"/rest/items?{params}")
            response.raise_for_status()
            items_data = response.json()

            signals: dict[str, Signal] = {}
            for item in items_data:
                signal, metadata = self._extract_signal(item)
                signals[signal.id] = signal
                self._item_metadata[signal.id] = metadata

            logger.info(f"Loaded {len(signals)} signals from OpenHAB")
            return signals

        except httpx.HTTPError as e:
            raise SmartHomeConnectionError("openhab", self.base_url, e) from e

    async def get_signal(self, signal_id: str) -> Signal:
        """Retrieve a specific signal from OpenHAB.

        Args:
            signal_id: The OpenHAB item name.

        Returns:
            Signal object for the item.

        Raises:
            SignalNotFoundError: If the item doesn't exist.
            SmartHomeConnectionError: If connection fails.
        """
        await self._ensure_initialized()

        try:
            client = await self._get_client()
            response = await client.get(
                f"/rest/items/{signal_id}?fields={COMMA.join(ITEM_FIELDS)}"
            )

            if response.status_code == 404:
                raise SignalNotFoundError(signal_id)

            response.raise_for_status()
            item = response.json()

            signal, metadata = self._extract_signal(item)
            self._item_metadata[signal.id] = metadata
            return signal

        except httpx.HTTPError as e:
            if isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 404:
                raise SignalNotFoundError(signal_id) from e
            raise SmartHomeConnectionError("openhab", self.base_url, e) from e

    async def subscribe_events(self) -> AsyncIterator[Signal]:
        """Subscribe to OpenHAB state change events via SSE.

        Yields:
            Signal objects whenever an item's state changes.

        Raises:
            SmartHomeConnectionError: If the event stream fails.
        """
        await self._ensure_initialized()

        # Ensure we have item metadata for value formatting
        if not self._item_metadata:
            await self.get_signals()

        client: httpx.AsyncClient | None = None
        try:
            client = await self._get_sse_client()

            # Connect to SSE endpoint
            async with client.stream("GET", "/rest/events/states") as response:
                # First message contains the connection ID
                connection_id = None
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue

                    data = line[5:].strip()
                    if connection_id is None:
                        # First data line is the connection ID
                        connection_id = data
                        # Subscribe to all tracked items
                        await client.post(
                            f"/rest/events/states/{connection_id}",
                            json=list(self._item_metadata.keys()),
                        )
                        logger.info(f"Subscribed to {len(self._item_metadata)} items")
                        continue

                    # Parse state change event
                    try:
                        event_data = json.loads(data)
                        for item_name, payload in event_data.items():
                            if item_name not in self._item_metadata:
                                continue

                            signal = self._process_event(item_name, payload)
                            if signal:
                                yield signal
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse SSE event: {data[:100]}")
                        continue

        except httpx.HTTPError as e:
            raise SmartHomeConnectionError("openhab", self.base_url, e) from e
        finally:
            # Clean up SSE client after subscription ends
            if client is not None:
                await client.aclose()

    def _extract_signal(self, item: dict[str, Any]) -> tuple[Signal, _ItemMetadata]:
        """Extract a Signal and metadata from an OpenHAB item response.

        This handles the complex logic of determining units and formatting
        based on item type, state patterns, and transformations.

        Args:
            item: Raw item data from OpenHAB REST API.

        Returns:
            Tuple of (Signal, ItemMetadata for event processing).
        """
        name = item["name"]
        label = item.get("label", "")
        state = item.get("state", "")
        item_type = item.get("type", "")

        # Parse item type (e.g., "Number:Temperature" -> ["Number", "Temperature"])
        type_parts = item_type.split(":")
        is_quantity_type = len(type_parts) > 1

        # If transformation was applied, use transformed state directly
        if "transformedState" in item:
            return Signal(
                id=self._prefixed_id(name),
                value=item["transformedState"],
                unit="",
                label=label,
            ), _ItemMetadata(event_state_contains_unit=False, label=label)

        # DateTime items have no units
        if type_parts[0] == "DateTime":
            return Signal(
                id=self._prefixed_id(name),
                value=state,
                unit="",
                label=label,
            ), _ItemMetadata(event_state_contains_unit=False, label=label)

        # Check for custom unit in state description pattern
        state_desc = item.get("stateDescription", {})
        pattern = state_desc.get("pattern") if state_desc else None

        if pattern:
            unit, fmt = extract_unit_from_pattern(pattern)
            value = format_value(state, unit, fmt, is_quantity_type)
            return Signal(
                id=self._prefixed_id(name),
                value=value,
                unit=unit,
                label=label,
            ), _ItemMetadata(
                unit=unit,
                format=fmt,
                is_quantity_type=is_quantity_type,
                event_state_contains_unit=True,
                label=label,
            )

        # QuantityType: use default unit from measurement system
        if is_quantity_type:
            quantity_type = type_parts[1]
            unit = self._default_units.get(quantity_type, "")
            value = format_value(state, unit, "%s", is_quantity_type=True)
            return Signal(
                id=self._prefixed_id(name),
                value=value,
                unit=unit,
                label=label,
            ), _ItemMetadata(
                unit=unit,
                format="%s",
                is_quantity_type=True,
                event_state_contains_unit=True,
                label=label,
            )

        # Rollershutter and Dimmer are percentage values
        if type_parts[0] in ("Rollershutter", "Dimmer"):
            return Signal(
                id=self._prefixed_id(name),
                value=state,
                unit="%",
                label=label,
            ), _ItemMetadata(
                unit="%",
                format="%d",
                event_state_contains_unit=False,
                label=label,
            )

        # Default: no unit
        return Signal(
            id=self._prefixed_id(name),
            value=state,
            unit="",
            label=label,
        ), _ItemMetadata(event_state_contains_unit=False, label=label)

    def _process_event(self, item_name: str, payload: dict[str, Any]) -> Signal | None:
        """Process an SSE event payload into a Signal.

        Args:
            item_name: The item that changed.
            payload: Event payload with state/displayState.

        Returns:
            Signal with updated value, or None if processing failed.
        """
        metadata = self._item_metadata.get(item_name)
        if not metadata:
            return None

        try:
            if metadata.event_state_contains_unit:
                # State contains unit, need to extract and format
                raw_state = fix_encoding(payload.get("state", ""))
                value = format_value(
                    raw_state,
                    metadata.unit,
                    metadata.format,
                    metadata.is_quantity_type,
                )
            elif "displayState" in payload:
                value = fix_encoding(payload["displayState"])
            else:
                value = fix_encoding(payload.get("state", ""))

            return Signal(
                id=self._prefixed_id(item_name),
                value=value,
                unit=metadata.unit,
                label=metadata.label,
            )
        except Exception:
            logger.exception(f"Failed to process event for {item_name}")
            return None

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def is_connected(self) -> bool:
        """Check if the adapter has an active connection.

        Returns:
            True if the HTTP client exists and is not closed.
        """
        return self._client is not None and not self._client.is_closed


class _ItemMetadata:
    """Internal metadata for processing item events.

    Stores the formatting information needed to process SSE events,
    since events don't include the full item metadata.
    """

    __slots__ = (
        "unit",
        "format",
        "is_quantity_type",
        "event_state_contains_unit",
        "label",
    )

    def __init__(
        self,
        unit: str = "",
        format: str = "%s",
        is_quantity_type: bool = False,
        event_state_contains_unit: bool = True,
        label: str = "",
    ) -> None:
        self.unit = unit
        self.format = format
        self.is_quantity_type = is_quantity_type
        self.event_state_contains_unit = event_state_contains_unit
        self.label = label
