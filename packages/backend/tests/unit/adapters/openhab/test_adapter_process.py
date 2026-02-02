"""Tests for OpenHAB adapter event processing (_process_event).

Covers:
- QuantityType events with unit in state
- Events with displayState field
- Events with raw state only
- Error handling (unknown items, encoding issues, exceptions)
"""

from __future__ import annotations

from lumehaven.adapters.openhab.adapter import OpenHABAdapter, _ItemMetadata
from tests.fixtures.openhab_sse import (
    SSE_STATE_WITH_DISPLAY_STATE,
    SSE_STATE_WITHOUT_DISPLAY_STATE,
)


class TestProcessEventQuantityType:
    """Tests for processing events from QuantityType items.

    Technique: Branch Coverage — E1: event_state_contains_unit.
    """

    def test_formats_quantity_type_event(self, adapter: OpenHABAdapter) -> None:
        """QuantityType events are formatted with unit extraction."""
        adapter._item_metadata = {
            "Bathroom_Humidity": _ItemMetadata(
                unit="%",
                format="%.1f",
                is_quantity_type=True,
                event_state_contains_unit=True,
                label="Bathroom Humidity",
            )
        }
        payload = {"state": "65.5 %"}

        signal = adapter._process_event("Bathroom_Humidity", payload)

        assert signal is not None
        assert signal.value == "65.5"
        assert signal.unit == "%"


class TestProcessEventDisplayState:
    """Tests for processing events with displayState field.

    Technique: Branch Coverage — E2: displayState present.
    """

    def test_uses_display_state_when_present(self, adapter: OpenHABAdapter) -> None:
        """Uses displayState field when available and not quantity type."""
        adapter._item_metadata = {
            "System_Uptime": _ItemMetadata(
                unit="",
                format="%s",
                is_quantity_type=False,
                event_state_contains_unit=False,
                label="System Uptime",
            )
        }

        signal = adapter._process_event(
            "System_Uptime", SSE_STATE_WITH_DISPLAY_STATE["System_Uptime"]
        )

        assert signal is not None
        assert signal.value == "48d 21h"  # Uses displayState


class TestProcessEventRawState:
    """Tests for processing events without displayState.

    Technique: Branch Coverage — E3: use raw state.
    """

    def test_uses_raw_state_when_no_display_state(
        self, adapter: OpenHABAdapter
    ) -> None:
        """Falls back to raw state when displayState not present."""
        adapter._item_metadata = {
            "LivingRoom_Dimmer": _ItemMetadata(
                unit="%",
                format="%d",
                is_quantity_type=False,
                event_state_contains_unit=False,
                label="Living Room Dimmer",
            )
        }

        signal = adapter._process_event(
            "LivingRoom_Dimmer", SSE_STATE_WITHOUT_DISPLAY_STATE["LivingRoom_Dimmer"]
        )

        assert signal is not None
        assert signal.value == "75"


class TestProcessEventErrorHandling:
    """Tests for error handling in event processing.

    Technique: Error Guessing — malformed data, missing items.
    """

    def test_returns_none_for_unknown_item(self, adapter: OpenHABAdapter) -> None:
        """Returns None when item not in metadata cache."""
        adapter._item_metadata = {}

        signal = adapter._process_event("UnknownItem", {"state": "42"})

        assert signal is None

    def test_handles_encoding_issues(self, adapter: OpenHABAdapter) -> None:
        """Fixes encoding issues using ftfy."""
        adapter._item_metadata = {
            "Sensor_External": _ItemMetadata(
                unit="°C",
                format="%.1f",
                is_quantity_type=True,
                event_state_contains_unit=True,
                label="External Temperature",
            )
        }
        # Double-encoded UTF-8: "Â°C" should become "°C"
        payload = {"state": "22.5 Â°C"}

        signal = adapter._process_event("Sensor_External", payload)

        assert signal is not None
        # ftfy should fix the encoding
        assert "Â" not in signal.value


class TestProcessEventException:
    """Tests for exception handling in _process_event.

    Technique: Error Guessing — exception in processing path.
    """

    def test_returns_none_on_processing_exception(
        self, adapter: OpenHABAdapter
    ) -> None:
        """Returns None when processing fails due to exception."""
        # Set up metadata that will cause fix_encoding to throw
        adapter._item_metadata = {
            "BadItem": _ItemMetadata(
                unit="°C",
                format="%.1f",
                is_quantity_type=True,
                event_state_contains_unit=True,
                label="Bad Item",
            )
        }
        # Send a payload with None state which will cause fix_encoding to throw
        payload = {"state": None}

        signal = adapter._process_event("BadItem", payload)

        # Should return None instead of raising
        assert signal is None
