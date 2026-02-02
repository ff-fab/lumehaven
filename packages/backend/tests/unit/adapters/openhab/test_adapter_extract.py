"""Tests for OpenHAB adapter signal extraction (_extract_signal).

Covers:
- TransformedState extraction
- DateTime type handling
- Pattern parsing for units
- QuantityType without pattern
- Rollershutter/Dimmer implicit units
- Default (no unit) items
- Edge cases (empty labels, special states)
"""

from __future__ import annotations

import pytest

from lumehaven.adapters.openhab.adapter import OpenHABAdapter
from tests.fixtures.openhab_responses import (
    COLOR_ITEM,
    CONTACT_ITEM,
    DATETIME_ITEM,
    DIMENSIONLESS_ITEM,
    DIMMER_ITEM,
    DIMMER_NO_PATTERN_ITEM,
    ENERGY_ITEM,
    LENGTH_ITEM,
    LOCATION_ITEM,
    NO_LABEL_ITEM,
    NULL_ITEM,
    PLAYER_ITEM,
    POWER_ITEM,
    PRESSURE_ITEM,
    QUANTITY_NO_PATTERN_ITEM,
    ROLLERSHUTTER_ITEM,
    ROLLERSHUTTER_NO_PATTERN_ITEM,
    SPEED_ITEM,
    STRING_ITEM,
    SWITCH_ITEM,
    TEMPERATURE_ITEM,
    TRANSFORMED_ITEMS,
    UNDEF_ITEM,
    VOLUME_ITEM,
)


class TestExtractSignalTransformedState:
    """Tests for extracting signals from items with transformedState.

    Technique: Branch Coverage — B1: transformedState present.
    """

    @pytest.mark.parametrize(
        "item",
        TRANSFORMED_ITEMS,
        ids=[item["name"] for item in TRANSFORMED_ITEMS],
    )
    def test_uses_transformed_state_directly(
        self, adapter: OpenHABAdapter, item: dict
    ) -> None:
        """Items with transformedState use the transformed value directly."""
        adapter._default_units = {"Temperature": "°C", "Time": "s", "Angle": "°"}

        signal, metadata = adapter._extract_signal(item)

        assert signal.value == item["transformedState"]
        assert signal.unit == ""  # No unit for transformed states
        assert not metadata.event_state_contains_unit


class TestExtractSignalDateTime:
    """Tests for extracting signals from DateTime items.

    Technique: Branch Coverage — B2: DateTime type (no unit).
    """

    def test_datetime_has_no_unit(self, adapter: OpenHABAdapter) -> None:
        """DateTime items have empty unit."""
        adapter._default_units = {}

        signal, metadata = adapter._extract_signal(DATETIME_ITEM)

        assert signal.id == "oh:System_LastUpdate"
        assert signal.value == DATETIME_ITEM["state"]
        assert signal.unit == ""
        assert not metadata.event_state_contains_unit


class TestExtractSignalWithPattern:
    """Tests for extracting signals from items with stateDescription.pattern.

    Technique: Decision Table — B3: pattern parsing combinations.
    """

    @pytest.mark.parametrize(
        ("item", "expected_unit"),
        [
            (TEMPERATURE_ITEM, "°C"),
            (POWER_ITEM, "W"),
            (ENERGY_ITEM, "kWh"),
            (DIMMER_ITEM, "%"),  # Pattern: "%d %%"
            (DIMENSIONLESS_ITEM, "%"),  # Pattern: "%.1f %%"
            (SPEED_ITEM, "km/h"),
            (PRESSURE_ITEM, "hPa"),
            (VOLUME_ITEM, "l"),
            (LENGTH_ITEM, "mm"),
        ],
        ids=[
            "temperature",
            "power",
            "energy",
            "dimmer",
            "dimensionless",
            "speed",
            "pressure",
            "volume",
            "length",
        ],
    )
    def test_extracts_unit_from_pattern(
        self, adapter: OpenHABAdapter, item: dict, expected_unit: str
    ) -> None:
        """Correctly extracts unit from stateDescription.pattern."""
        adapter._default_units = {"Temperature": "°C", "Power": "W", "Energy": "kWh"}

        signal, metadata = adapter._extract_signal(item)

        assert signal.unit == expected_unit
        assert metadata.unit == expected_unit


class TestExtractSignalQuantityTypeNoPattern:
    """Tests for QuantityType items without stateDescription.

    Technique: Branch Coverage — B4: QuantityType uses default units.
    """

    def test_uses_default_units_for_quantity_type(
        self, adapter: OpenHABAdapter
    ) -> None:
        """QuantityType without pattern uses default unit from measurement system."""
        adapter._default_units = {"Temperature": "°C"}

        signal, metadata = adapter._extract_signal(QUANTITY_NO_PATTERN_ITEM)

        assert signal.unit == "°C"
        assert metadata.unit == "°C"
        assert metadata.is_quantity_type
        assert metadata.event_state_contains_unit


class TestExtractSignalRollershutterDimmer:
    """Tests for Rollershutter and Dimmer items.

    Technique: Branch Coverage — B5/B6: implicit percentage unit.
    """

    @pytest.mark.parametrize(
        "item",
        [ROLLERSHUTTER_ITEM, DIMMER_ITEM],
        ids=["rollershutter_with_pattern", "dimmer_with_pattern"],
    )
    def test_has_percentage_unit(self, adapter: OpenHABAdapter, item: dict) -> None:
        """Rollershutter and Dimmer items have implicit % unit."""
        adapter._default_units = {}

        signal, metadata = adapter._extract_signal(item)

        assert signal.unit == "%"
        assert metadata.unit == "%"

    @pytest.mark.parametrize(
        "item",
        [ROLLERSHUTTER_NO_PATTERN_ITEM, DIMMER_NO_PATTERN_ITEM],
        ids=["rollershutter_no_pattern", "dimmer_no_pattern"],
    )
    def test_type_based_percentage_unit(
        self, adapter: OpenHABAdapter, item: dict
    ) -> None:
        """Rollershutter/Dimmer without pattern use type-based % unit."""
        adapter._default_units = {}

        signal, metadata = adapter._extract_signal(item)

        assert signal.unit == "%"
        assert metadata.unit == "%"
        assert not metadata.event_state_contains_unit  # Type-based, not QuantityType


class TestExtractSignalDefault:
    """Tests for items without special handling.

    Technique: Branch Coverage — B7: default (no unit).
    """

    @pytest.mark.parametrize(
        "item",
        [
            SWITCH_ITEM,
            STRING_ITEM,
            CONTACT_ITEM,
            PLAYER_ITEM,
            COLOR_ITEM,
            LOCATION_ITEM,
        ],
        ids=["switch", "string", "contact", "player", "color", "location"],
    )
    def test_default_items_have_no_unit(
        self, adapter: OpenHABAdapter, item: dict
    ) -> None:
        """Items without pattern or QuantityType have empty unit."""
        adapter._default_units = {}

        signal, metadata = adapter._extract_signal(item)

        assert signal.unit == ""
        assert signal.value == item["state"]


class TestExtractSignalEdgeCases:
    """Tests for edge cases in signal extraction.

    Technique: Error Guessing — anticipating specific failure modes.
    """

    def test_empty_label_uses_name(self, adapter: OpenHABAdapter) -> None:
        """Items with empty label use name as label."""
        adapter._default_units = {}

        signal, _ = adapter._extract_signal(NO_LABEL_ITEM)

        assert signal.label == ""  # Current behavior preserves empty label

    def test_special_states_preserved(self, adapter: OpenHABAdapter) -> None:
        """UNDEF and NULL states are preserved as-is."""
        adapter._default_units = {"Temperature": "°C"}

        undef_signal, _ = adapter._extract_signal(UNDEF_ITEM)
        null_signal, _ = adapter._extract_signal(NULL_ITEM)

        assert undef_signal.value == "UNDEF"
        assert null_signal.value == "NULL"
