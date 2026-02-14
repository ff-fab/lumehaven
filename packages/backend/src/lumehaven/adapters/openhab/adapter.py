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
from collections.abc import AsyncIterator, Iterator
from typing import Any, Literal

import httpx
from ftfy import fix_encoding

from lumehaven.adapters.openhab.units import (
    extract_unit_from_pattern,
    format_value,
    get_default_units,
)
from lumehaven.core.exceptions import SmartHomeConnectionError
from lumehaven.core.signal import (
    NULL_VALUE,
    UNDEFINED_VALUE,
    Signal,
    SignalType,
    SignalValue,
)

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
                # Key metadata by raw item name (not prefixed) for SSE event lookup
                self._item_metadata[item["name"]] = metadata

            logger.info(f"Loaded {len(signals)} signals from OpenHAB")
            return signals

        except httpx.HTTPError as e:
            raise SmartHomeConnectionError("openhab", self.base_url, e) from e

    async def get_signal(self, signal_id: str) -> Signal | None:
        """Retrieve a specific signal from OpenHAB.

        Args:
            signal_id: The OpenHAB item name.

        Returns:
            Signal object for the item, or None if not found.

        Raises:
            SmartHomeConnectionError: If connection fails.
        """
        await self._ensure_initialized()

        try:
            client = await self._get_client()
            response = await client.get(
                f"/rest/items/{signal_id}?fields={COMMA.join(ITEM_FIELDS)}"
            )

            if response.status_code == 404:
                return None

            response.raise_for_status()
            item = response.json()

            signal, metadata = self._extract_signal(item)
            # Key metadata by raw item name (not prefixed) for SSE event lookup
            self._item_metadata[item["name"]] = metadata
            return signal

        except httpx.HTTPError as e:
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

                    # Parse and yield signals from state change event
                    for signal in self._parse_sse_events(data):
                        yield signal

        except httpx.HTTPError as e:
            raise SmartHomeConnectionError("openhab", self.base_url, e) from e
        finally:
            # Clean up SSE client after subscription ends
            if client is not None:
                await client.aclose()

    def _parse_sse_events(self, data: str) -> Iterator[Signal]:
        """Parse an SSE state-update JSON blob and yield signals.

        Extracted from subscribe_events to keep cyclomatic complexity
        manageable (each method stays at radon rank A/B).

        Args:
            data: Raw JSON string from the SSE data line.

        Yields:
            Signal for each tracked item present in the event.
        """
        try:
            event_data = json.loads(data)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse SSE event: {data[:100]}")
            return

        for item_name, payload in event_data.items():
            if item_name not in self._item_metadata:
                continue

            signal = self._process_event(item_name, payload)
            if signal:
                yield signal

    @staticmethod
    def _resolve_signal_type(base_type: str) -> SignalType:
        """Map an OpenHAB base item type to a SignalType discriminator.

        This centralises the mapping so that both ``_extract_signal`` and
        ``_process_event`` produce consistent ``signal_type`` values.

        Args:
            base_type: The base OpenHAB type (before the colon),
                e.g. ``"Number"``, ``"Switch"``, ``"Dimmer"``.

        Returns:
            The corresponding ``SignalType``.
        """
        match base_type:
            case "Number" | "Dimmer" | "Rollershutter":
                return SignalType.NUMBER
            case "Switch" | "Contact":
                return SignalType.BOOLEAN
            case "DateTime":
                return SignalType.DATETIME
            case "Player":
                return SignalType.ENUM
            case _:
                return SignalType.STRING

    @staticmethod
    def _coerce_value(display: str, signal_type: SignalType) -> SignalValue:
        """Coerce a formatted display string to a typed Python value.

        The coercion rules follow the ADR-010 mapping table:

        * ``NUMBER`` → ``int`` when the float value is a whole number,
          otherwise ``float``.
        * ``BOOLEAN`` → ``True`` for OpenHAB ``ON`` / ``OPEN``,
          ``False`` for ``OFF`` / ``CLOSED``.
        * Everything else → the original string.

        Args:
            display: The formatted value string (already stripped of units).
            signal_type: The resolved ``SignalType``.

        Returns:
            A typed Python value suitable for ``Signal.value``.
        """
        if signal_type is SignalType.NUMBER:
            try:
                f = float(display)
                return int(f) if f.is_integer() else f
            except ValueError, TypeError:
                return display
        if signal_type is SignalType.BOOLEAN:
            return display in ("ON", "OPEN")
        return display

    def _extract_signal(self, item: dict[str, Any]) -> tuple[Signal, _ItemMetadata]:
        """Extract an enriched Signal and metadata from an OpenHAB item.

        Produces an ADR-010 enriched Signal with typed ``value``,
        ``display_value``, ``available`` flag, and ``signal_type``
        discriminator.  Handles:

        * TransformedState items (JS/MAP transformations)
        * DateTime items (no unit)
        * QuantityType items with/without ``stateDescription.pattern``
        * Rollershutter/Dimmer implicit percentage
        * Default items (Switch, String, Contact, …)
        * Unavailable states (``UNDEF`` / ``NULL``)

        Args:
            item: Raw item data from OpenHAB REST API.

        Returns:
            Tuple of (enriched Signal, ItemMetadata for SSE processing).
        """
        name = item["name"]
        label = item.get("label") or name
        state = item.get("state", "")
        item_type = item.get("type", "")

        type_parts = item_type.split(":")
        base_type = type_parts[0]
        is_quantity_type = len(type_parts) > 1

        signal_type = self._resolve_signal_type(base_type)
        unavailable = state in (UNDEFINED_VALUE, NULL_VALUE)

        # --- Determine unit, display_value, metadata per item structure ---

        if "transformedState" in item:
            transformed = item["transformedState"]
            display_value = "" if unavailable else transformed
            typed_value: SignalValue = None if unavailable else transformed
            unit = ""
            # Transformed output is always a display string.
            signal_type = SignalType.STRING
            metadata = _ItemMetadata(
                event_state_contains_unit=False,
                label=label,
                signal_type=SignalType.STRING,
            )

        elif base_type == "DateTime":
            display_value = "" if unavailable else state
            typed_value = None if unavailable else state
            unit = ""
            metadata = _ItemMetadata(
                event_state_contains_unit=False,
                label=label,
                signal_type=SignalType.DATETIME,
            )

        elif (pattern := self._item_pattern(item)) is not None:
            unit, fmt = extract_unit_from_pattern(pattern)
            if unavailable:
                display_value = ""
                typed_value = None
            else:
                display_value = format_value(state, unit, fmt, is_quantity_type)
                typed_value = self._coerce_value(display_value, signal_type)
            metadata = _ItemMetadata(
                unit=unit,
                format=fmt,
                is_quantity_type=is_quantity_type,
                event_state_contains_unit=True,
                label=label,
                signal_type=signal_type,
            )

        elif is_quantity_type:
            quantity_type = type_parts[1]
            unit = self._default_units.get(quantity_type, "")
            if unavailable:
                display_value = ""
                typed_value = None
            else:
                display_value = format_value(state, unit, "%s", is_quantity_type=True)
                typed_value = self._coerce_value(display_value, signal_type)
            metadata = _ItemMetadata(
                unit=unit,
                format="%s",
                is_quantity_type=True,
                event_state_contains_unit=True,
                label=label,
                signal_type=signal_type,
            )

        elif base_type in ("Rollershutter", "Dimmer"):
            unit = "%"
            if unavailable:
                display_value = ""
                typed_value = None
            else:
                display_value = state
                typed_value = self._coerce_value(state, SignalType.NUMBER)
            metadata = _ItemMetadata(
                unit="%",
                format="%d",
                event_state_contains_unit=False,
                label=label,
                signal_type=SignalType.NUMBER,
            )

        else:
            unit = ""
            if unavailable:
                display_value = ""
                typed_value = None
            else:
                display_value = state
                typed_value = self._coerce_value(state, signal_type)
            metadata = _ItemMetadata(
                event_state_contains_unit=False,
                label=label,
                signal_type=signal_type,
            )

        return Signal(
            id=self._prefixed_id(name),
            value=typed_value,
            display_value=display_value,
            unit=unit,
            label=label,
            available=not unavailable,
            signal_type=signal_type,
        ), metadata

    @staticmethod
    def _item_pattern(item: dict[str, Any]) -> str | None:
        """Extract the stateDescription pattern from an item, if any."""
        state_desc = item.get("stateDescription", {})
        return state_desc.get("pattern") if state_desc else None

    def _process_event(self, item_name: str, payload: dict[str, Any]) -> Signal | None:
        """Process an SSE event payload into an enriched Signal.

        Produces an ADR-010 enriched Signal with typed ``value``,
        ``display_value``, ``available``, and ``signal_type``.

        Args:
            item_name: The item that changed.
            payload: Event payload with state/displayState.

        Returns:
            Enriched Signal, or None if processing failed.
        """
        metadata = self._item_metadata.get(item_name)
        if not metadata:
            return None

        try:
            raw_state = payload.get("state", "")
            unavailable = raw_state is None or (
                isinstance(raw_state, str)
                and raw_state in (UNDEFINED_VALUE, NULL_VALUE)
            )

            if unavailable:
                return Signal(
                    id=self._prefixed_id(item_name),
                    value=None,
                    display_value="",
                    unit=metadata.unit,
                    label=metadata.label,
                    available=False,
                    signal_type=metadata.signal_type,
                )

            # Compute display_value from the appropriate source
            if metadata.event_state_contains_unit:
                display_value = format_value(
                    fix_encoding(raw_state),
                    metadata.unit,
                    metadata.format,
                    metadata.is_quantity_type,
                )
            elif "displayState" in payload:
                display_value = fix_encoding(payload["displayState"])
            else:
                display_value = fix_encoding(raw_state)

            typed_value = self._coerce_value(display_value, metadata.signal_type)

            return Signal(
                id=self._prefixed_id(item_name),
                value=typed_value,
                display_value=display_value,
                unit=metadata.unit,
                label=metadata.label,
                signal_type=metadata.signal_type,
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

    async def send_command(self, signal_id: str, command: str) -> None:
        """Send a command to an OpenHAB item (ADR-011).

        .. note::
            Not yet implemented — tracked in the interactive widget phase.
            The protocol method is defined now so the adapter satisfies
            the extended ``SmartHomeAdapter`` protocol.

        Args:
            signal_id: The OpenHAB item name (without prefix).
            command: The command value as a string (e.g. ``"ON"``).

        Raises:
            NotImplementedError: Always — implementation deferred.
        """
        raise NotImplementedError(
            "OpenHAB send_command() is not yet implemented. "
            "Tracked for the interactive widget phase."
        )


class _ItemMetadata:
    """Internal metadata for processing item events.

    Stores the formatting information needed to process SSE events,
    since events don't include the full item metadata.  Includes
    ``signal_type`` so that ``_process_event`` can produce enriched
    Signals per ADR-010.
    """

    __slots__ = (
        "unit",
        "format",
        "is_quantity_type",
        "event_state_contains_unit",
        "label",
        "signal_type",
    )

    def __init__(
        self,
        unit: str = "",
        format: str = "%s",
        is_quantity_type: bool = False,
        event_state_contains_unit: bool = True,
        label: str = "",
        signal_type: SignalType = SignalType.STRING,
    ) -> None:
        self.unit = unit
        self.format = format
        self.is_quantity_type = is_quantity_type
        self.event_state_contains_unit = event_state_contains_unit
        self.label = label
        self.signal_type = signal_type
