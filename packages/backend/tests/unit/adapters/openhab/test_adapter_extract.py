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
from lumehaven.core.signal import SignalType
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
        # Boolean items (Switch/Contact) have coerced values
        if item["type"] in ("Switch", "Contact"):
            assert isinstance(signal.value, bool)
        else:
            assert signal.value == item["state"]


class TestExtractSignalEdgeCases:
    """Tests for edge cases in signal extraction.

    Technique: Error Guessing — anticipating specific failure modes.
    """

    def test_empty_label_falls_back_to_name(self, adapter: OpenHABAdapter) -> None:
        """Items with empty label fall back to using name as label."""
        adapter._default_units = {}

        signal, _ = adapter._extract_signal(NO_LABEL_ITEM)

        assert signal.label == NO_LABEL_ITEM["name"]

    def test_special_states_preserved(self, adapter: OpenHABAdapter) -> None:
        """UNDEF and NULL states produce unavailable signals with None value."""
        adapter._default_units = {"Temperature": "°C"}

        undef_signal, _ = adapter._extract_signal(UNDEF_ITEM)
        null_signal, _ = adapter._extract_signal(NULL_ITEM)

        assert undef_signal.value is None
        assert undef_signal.available is False
        assert undef_signal.display_value == ""
        assert undef_signal.signal_type == SignalType.NUMBER

        assert null_signal.value is None
        assert null_signal.available is False
        assert null_signal.display_value == ""
        assert null_signal.signal_type == SignalType.NUMBER


# =========================================================================
# ADR-010 enrichment tests — typed value, display_value, signal_type
# =========================================================================


class TestEnrichmentSignalType:
    """Tests for signal_type mapping from OpenHAB item types.

    Technique: Decision Table — every OpenHAB base type maps to a SignalType.
    """

    @pytest.mark.parametrize(
        ("item", "expected_type"),
        [
            (TEMPERATURE_ITEM, SignalType.NUMBER),  # Number:Temperature
            (POWER_ITEM, SignalType.NUMBER),  # Number:Power
            (ENERGY_ITEM, SignalType.NUMBER),  # Number:Energy
            (SWITCH_ITEM, SignalType.BOOLEAN),
            (CONTACT_ITEM, SignalType.BOOLEAN),
            (DATETIME_ITEM, SignalType.DATETIME),
            (STRING_ITEM, SignalType.STRING),
            (PLAYER_ITEM, SignalType.ENUM),
            (COLOR_ITEM, SignalType.STRING),
            (LOCATION_ITEM, SignalType.STRING),
            (DIMMER_ITEM, SignalType.NUMBER),
            (ROLLERSHUTTER_ITEM, SignalType.NUMBER),
            (DIMENSIONLESS_ITEM, SignalType.NUMBER),  # Number:Dimensionless
        ],
        ids=[
            "number_temperature",
            "number_power",
            "number_energy",
            "switch",
            "contact",
            "datetime",
            "string",
            "player",
            "color",
            "location",
            "dimmer",
            "rollershutter",
            "dimensionless",
        ],
    )
    def test_signal_type_from_item_type(
        self,
        adapter: OpenHABAdapter,
        item: dict,
        expected_type: SignalType,
    ) -> None:
        """Each OpenHAB item type maps to the correct SignalType."""
        adapter._default_units = {"Temperature": "°C", "Power": "W", "Energy": "kWh"}
        signal, _ = adapter._extract_signal(item)
        assert signal.signal_type == expected_type

    def test_transformed_items_are_always_string(self, adapter: OpenHABAdapter) -> None:
        """Transformed items always have signal_type STRING."""
        adapter._default_units = {"Temperature": "°C", "Time": "s", "Angle": "°"}
        for item in TRANSFORMED_ITEMS:
            signal, _ = adapter._extract_signal(item)
            assert signal.signal_type == SignalType.STRING


class TestEnrichmentTypedValue:
    """Tests for value type coercion per ADR-010 mapping rules.

    Technique: Equivalence Partitioning — type coercion per signal_type.
    """

    def test_number_value_is_float(self, adapter: OpenHABAdapter) -> None:
        """Number:Temperature '21.5 °C' → value=21.5 (float)."""
        adapter._default_units = {"Temperature": "°C"}
        signal, _ = adapter._extract_signal(TEMPERATURE_ITEM)
        assert signal.value == 21.5
        assert isinstance(signal.value, float)

    def test_whole_number_value_is_int(self, adapter: OpenHABAdapter) -> None:
        """Number:Power '1250 W' → value=1250 (int)."""
        adapter._default_units = {"Power": "W"}
        signal, _ = adapter._extract_signal(POWER_ITEM)
        assert signal.value == 1250
        assert isinstance(signal.value, int)

    def test_switch_on_is_true(self, adapter: OpenHABAdapter) -> None:
        """Switch 'ON' → value=True."""
        adapter._default_units = {}
        signal, _ = adapter._extract_signal(SWITCH_ITEM)
        assert signal.value is True

    def test_contact_closed_is_false(self, adapter: OpenHABAdapter) -> None:
        """Contact 'CLOSED' → value=False (not open)."""
        adapter._default_units = {}
        signal, _ = adapter._extract_signal(CONTACT_ITEM)
        assert signal.value is False

    def test_string_value_unchanged(self, adapter: OpenHABAdapter) -> None:
        """String items keep their string value."""
        adapter._default_units = {}
        signal, _ = adapter._extract_signal(STRING_ITEM)
        assert signal.value == "Partly Cloudy"
        assert isinstance(signal.value, str)

    def test_datetime_value_is_string(self, adapter: OpenHABAdapter) -> None:
        """DateTime items keep their ISO string value."""
        adapter._default_units = {}
        signal, _ = adapter._extract_signal(DATETIME_ITEM)
        assert signal.value == DATETIME_ITEM["state"]
        assert isinstance(signal.value, str)

    def test_dimmer_value_is_int(self, adapter: OpenHABAdapter) -> None:
        """Dimmer '75' → value=75 (int)."""
        adapter._default_units = {}
        signal, _ = adapter._extract_signal(DIMMER_ITEM)
        assert signal.value == 75
        assert isinstance(signal.value, int)

    def test_rollershutter_value_is_int(self, adapter: OpenHABAdapter) -> None:
        """Rollershutter '30' → value=30 (int)."""
        adapter._default_units = {}
        signal, _ = adapter._extract_signal(ROLLERSHUTTER_ITEM)
        assert signal.value == 30
        assert isinstance(signal.value, int)

    def test_player_value_is_string(self, adapter: OpenHABAdapter) -> None:
        """Player 'PAUSE' → value='PAUSE' (enum string)."""
        adapter._default_units = {}
        signal, _ = adapter._extract_signal(PLAYER_ITEM)
        assert signal.value == "PAUSE"


class TestEnrichmentDisplayValue:
    """Tests for display_value field per ADR-010.

    Technique: Specification-based — display_value is the formatted string.
    """

    def test_number_display_value(self, adapter: OpenHABAdapter) -> None:
        """display_value is the format-applied string, not the typed value."""
        adapter._default_units = {"Temperature": "°C"}
        signal, _ = adapter._extract_signal(TEMPERATURE_ITEM)
        assert signal.display_value == "21.5"
        assert isinstance(signal.display_value, str)

    def test_switch_display_value(self, adapter: OpenHABAdapter) -> None:
        """Switch display_value is the raw state string."""
        adapter._default_units = {}
        signal, _ = adapter._extract_signal(SWITCH_ITEM)
        assert signal.display_value == "ON"

    def test_transformed_display_value(self, adapter: OpenHABAdapter) -> None:
        """Transformed items use transformedState as display_value."""
        adapter._default_units = {"Time": "s", "Angle": "°"}
        for item in TRANSFORMED_ITEMS:
            signal, _ = adapter._extract_signal(item)
            assert signal.display_value == item["transformedState"]

    def test_unavailable_display_value_is_empty(self, adapter: OpenHABAdapter) -> None:
        """Unavailable signals have empty display_value."""
        adapter._default_units = {"Temperature": "°C"}
        signal, _ = adapter._extract_signal(UNDEF_ITEM)
        assert signal.display_value == ""


class TestEnrichmentAvailability:
    """Tests for available flag per ADR-010 availability rules.

    Technique: Boundary Value — UNDEF/NULL boundary.
    """

    def test_normal_signal_is_available(self, adapter: OpenHABAdapter) -> None:
        """Normal signals have available=True."""
        adapter._default_units = {"Temperature": "°C"}
        signal, _ = adapter._extract_signal(TEMPERATURE_ITEM)
        assert signal.available is True

    def test_undef_is_unavailable(self, adapter: OpenHABAdapter) -> None:
        """UNDEF state → available=False, value=None."""
        adapter._default_units = {"Temperature": "°C"}
        signal, _ = adapter._extract_signal(UNDEF_ITEM)
        assert signal.available is False
        assert signal.value is None

    def test_null_is_unavailable(self, adapter: OpenHABAdapter) -> None:
        """NULL state → available=False, value=None."""
        adapter._default_units = {}
        signal, _ = adapter._extract_signal(NULL_ITEM)
        assert signal.available is False
        assert signal.value is None

    def test_unavailable_preserves_signal_type(self, adapter: OpenHABAdapter) -> None:
        """Unavailable signals still have the correct signal_type."""
        adapter._default_units = {"Temperature": "°C"}
        signal, _ = adapter._extract_signal(UNDEF_ITEM)
        # UNDEF_ITEM is Number:Temperature → signal_type should be NUMBER
        assert signal.signal_type == SignalType.NUMBER

    def test_unavailable_preserves_unit(self, adapter: OpenHABAdapter) -> None:
        """Unavailable QuantityType signals still have the unit."""
        adapter._default_units = {"Temperature": "°C"}
        signal, _ = adapter._extract_signal(UNDEF_ITEM)
        assert signal.unit == "°C"
