"""Unit tests for adapters/openhab/units.py — Unit extraction and value formatting.

Test Techniques Used:
- Specification-based Testing: Verifying docstring examples and public API contracts
- Equivalence Partitioning: Pattern format classes via @parametrize
- Boundary Value Analysis: Rounding at .5 boundaries, format precision edges
- Decision Table: format_value() condition combinations
- Branch Coverage: SI/US paths, regex match/no-match, numeric/non-numeric
- Error Guessing: Invalid patterns, non-parseable values, encoding edge cases
"""

from __future__ import annotations

import pytest

from lumehaven.adapters.openhab.units import (
    DEFAULT_UNITS,
    extract_unit_from_pattern,
    format_value,
    get_default_units,
)
from tests.fixtures.openhab_responses import (
    CONTACT_ITEM,
    DIMENSIONLESS_ITEM,
    DIMMER_ITEM,
    ENERGY_ITEM,
    LENGTH_ITEM,
    NULL_ITEM,
    POWER_ITEM,
    PRESSURE_ITEM,
    ROLLERSHUTTER_ITEM,
    SPEED_ITEM,
    SWITCH_ITEM,
    TEMPERATURE_ITEM,
    UNDEF_ITEM,
    VOLUME_ITEM,
)

# =============================================================================
# Tests: DEFAULT_UNITS and get_default_units()
# =============================================================================


class TestDefaultUnitsConstant:
    """Tests for DEFAULT_UNITS constant structure.

    Technique: Specification-based Testing — verifying data structure contracts.
    """

    def test_contains_si_system(self) -> None:
        """DEFAULT_UNITS contains SI measurement system."""
        assert "SI" in DEFAULT_UNITS

    def test_contains_us_system(self) -> None:
        """DEFAULT_UNITS contains US measurement system."""
        assert "US" in DEFAULT_UNITS

    def test_si_has_temperature_celsius(self) -> None:
        """SI system uses Celsius for temperature."""
        assert DEFAULT_UNITS["SI"]["Temperature"] == "°C"

    def test_us_has_temperature_fahrenheit(self) -> None:
        """US system uses Fahrenheit for temperature."""
        assert DEFAULT_UNITS["US"]["Temperature"] == "°F"

    def test_si_has_common_quantity_types(self) -> None:
        """SI system includes common QuantityTypes."""
        expected_types = {
            "Temperature",
            "Power",
            "Energy",
            "Length",
            "Volume",
            "Speed",
            "Pressure",
        }
        assert expected_types.issubset(set(DEFAULT_UNITS["SI"].keys()))

    def test_us_overrides_subset_of_si(self) -> None:
        """US system only overrides specific SI units, not all."""
        assert len(DEFAULT_UNITS["US"]) < len(DEFAULT_UNITS["SI"])


class TestGetDefaultUnits:
    """Tests for get_default_units() measurement system selection.

    Technique: Branch Coverage — SI vs US path selection.
    """

    def test_default_parameter_is_si(self) -> None:
        """Default system parameter returns SI units."""
        result = get_default_units()
        assert result["Temperature"] == "°C"

    def test_explicit_si_returns_si_units(self) -> None:
        """Explicit SI parameter returns SI units."""
        result = get_default_units("SI")
        assert result["Temperature"] == "°C"
        assert result["Length"] == "m"
        assert result["Volume"] == "l"

    def test_us_returns_merged_units(self) -> None:
        """US system returns SI base with US overrides applied."""
        result = get_default_units("US")
        assert result["Temperature"] == "°F"
        assert result["Length"] == "in"
        assert result["Volume"] == "gal"

    def test_us_preserves_non_overridden_si_units(self) -> None:
        """US system preserves SI units that aren't overridden."""
        result = get_default_units("US")
        assert result["Power"] == "W"
        assert result["Energy"] == "J"
        assert result["ElectricCurrent"] == "A"

    def test_si_returns_copy_not_reference(self) -> None:
        """SI result is a copy, not the original dict."""
        result = get_default_units("SI")
        result["Temperature"] = "K"
        assert DEFAULT_UNITS["SI"]["Temperature"] == "°C"

    def test_us_result_has_all_si_keys_plus_overrides(self) -> None:
        """US result contains all SI keys with overrides applied."""
        si_result = get_default_units("SI")
        us_result = get_default_units("US")
        assert set(us_result.keys()) == set(si_result.keys())


# =============================================================================
# Tests: extract_unit_from_pattern() — using real fixture data
# =============================================================================


class TestExtractUnitFromPatternRealData:
    """Tests for extract_unit_from_pattern() using real OpenHAB fixture data.

    Technique: Specification-based Testing — real-world data verification.
    """

    @pytest.mark.parametrize(
        ("fixture", "expected_unit", "expected_format"),
        [
            # Float formats with units
            (TEMPERATURE_ITEM, "°C", "%.1f"),
            (ENERGY_ITEM, "kWh", "%.2f"),
            (DIMENSIONLESS_ITEM, "%", "%.1f"),
            (SPEED_ITEM, "km/h", "%.1f"),
            (PRESSURE_ITEM, "hPa", "%.1f"),
            (LENGTH_ITEM, "mm", "%.1f"),
            # Integer formats with units
            (POWER_ITEM, "W", "%d"),
            (DIMMER_ITEM, "%", "%d"),
            (ROLLERSHUTTER_ITEM, "%", "%d"),
            (VOLUME_ITEM, "l", "%d"),
        ],
        ids=[
            "temperature_float",
            "energy_float",
            "dimensionless_percent",
            "speed_float",
            "pressure_float",
            "length_float",
            "power_integer",
            "dimmer_percent",
            "rollershutter_percent",
            "volume_integer",
        ],
    )
    def test_extracts_from_fixture_pattern(
        self, fixture: dict, expected_unit: str, expected_format: str
    ) -> None:
        """Extract unit and format from real OpenHAB stateDescription patterns."""
        pattern = fixture["stateDescription"]["pattern"]

        unit, format_str = extract_unit_from_pattern(pattern)

        assert unit == expected_unit
        assert format_str == expected_format


class TestExtractUnitFromPatternSyntheticCases:
    """Tests for patterns not covered by fixtures.

    Technique: Equivalence Partitioning + Error Guessing.
    """

    @pytest.mark.parametrize(
        ("pattern", "expected_unit", "expected_format"),
        [
            # Bare formats (no unit)
            ("%f", "", "%f"),
            ("%d", "", "%d"),
            ("%s", "", "%s"),
            # Fallback patterns (no format specifier)
            ("Wh", "Wh", "%s"),
            ("€/Monat", "€/Monat", "%s"),
            ("ppm", "ppm", "%s"),
            ("", "", "%s"),
            ("ON", "ON", "%s"),
            # Special OpenHAB patterns
            ("%.0f %unit%", "%unit%", "%.0f"),
            ("JS(elapsed-time.js):%s", "JS(elapsed-time.js):%s", "%s"),
        ],
        ids=[
            "bare_float",
            "bare_integer",
            "bare_string",
            "energy_unit_only",
            "currency",
            "ppm_unit",
            "empty",
            "state_value",
            "dynamic_unit_placeholder",
            "transformation_pattern",
        ],
    )
    def test_synthetic_patterns(
        self, pattern: str, expected_unit: str, expected_format: str
    ) -> None:
        """Synthetic patterns for edge cases not in fixtures."""
        unit, format_str = extract_unit_from_pattern(pattern)

        assert unit == expected_unit
        assert format_str == expected_format


class TestExtractUnitFromPatternUnicode:
    """Tests for Unicode handling in patterns.

    Technique: Error Guessing — encoding edge cases from lessons learned.
    """

    def test_unicode_degree_symbol(self) -> None:
        """Unicode degree symbol (°) is handled correctly."""
        unit, _ = extract_unit_from_pattern("%.1f °C")
        assert unit == "°C"
        assert ord(unit[0]) == 0x00B0

    def test_unicode_cubed_symbol(self) -> None:
        """Unicode superscript 3 (³) for volume is handled."""
        unit, _ = extract_unit_from_pattern("%.3f m³")
        assert unit == "m³"

    def test_unicode_squared_symbol(self) -> None:
        """Unicode superscript 2 (²) for area is handled."""
        unit, _ = extract_unit_from_pattern("%.2f m²")
        assert unit == "m²"

    def test_double_encoded_degree_preserved(self) -> None:
        """Double-encoded degree symbol (Â°) is passed through as-is."""
        unit, format_str = extract_unit_from_pattern("%.1f Â°C")
        assert unit == "Â°C"
        assert format_str == "%.1f"

    def test_fullwidth_percent_sign(self) -> None:
        """Fullwidth percent sign (％) in unit is preserved."""
        unit, format_str = extract_unit_from_pattern("%d ％")
        assert unit == "％"
        assert format_str == "%d"

    def test_cjk_unit_symbols(self) -> None:
        """CJK unit symbols (㎥ for cubic meter) are preserved."""
        unit, _ = extract_unit_from_pattern("%.3f ㎥")
        assert unit == "㎥"


# =============================================================================
# Tests: format_value() — using real fixture data
# =============================================================================


class TestFormatValueRealData:
    """Tests for format_value() using real OpenHAB fixture data.

    Technique: Specification-based Testing — real-world data verification.
    These tests derive inputs from fixtures and verify expected outputs.
    """

    @pytest.mark.parametrize(
        ("fixture", "expected_value"),
        [
            # Float formats (Number:* QuantityTypes)
            (TEMPERATURE_ITEM, "21.5"),  # "21.5 °C" → "21.5"
            (ENERGY_ITEM, "12345.67"),  # "12345.67 kWh" → "12345.67"
            (DIMENSIONLESS_ITEM, "65.5"),  # "65.5 %" → "65.5"
            (SPEED_ITEM, "15.5"),  # "15.5 km/h" → "15.5"
            (PRESSURE_ITEM, "1013.2"),  # "1013.25 hPa" → "1013.2" (rounded)
            (LENGTH_ITEM, "12.5"),  # "12.5 mm" → "12.5"
            # Integer formats
            (POWER_ITEM, "1250"),  # "1250 W" → "1250"
            (DIMMER_ITEM, "75"),  # "75" → "75" (no unit in state)
            (ROLLERSHUTTER_ITEM, "30"),  # "30" → "30" (no unit in state)
            (VOLUME_ITEM, "500"),  # "500 l" → "500"
        ],
        ids=[
            "temperature",
            "energy",
            "dimensionless",
            "speed",
            "pressure",
            "length",
            "power",
            "dimmer",
            "rollershutter",
            "volume",
        ],
    )
    def test_formats_fixture_item(self, fixture: dict, expected_value: str) -> None:
        """Format real OpenHAB items produces expected output."""
        state = fixture["state"]
        pattern = fixture["stateDescription"]["pattern"]
        is_quantity = fixture["type"].startswith("Number:")

        unit, format_str = extract_unit_from_pattern(pattern)
        result = format_value(state, unit, format_str, is_quantity_type=is_quantity)

        assert result == expected_value


class TestFormatValueUndefinedStates:
    """Tests for UNDEF/NULL state handling using real fixtures.

    Technique: Specification-based Testing — undefined state contract.
    """

    def test_undef_from_fixture(self) -> None:
        """UNDEF state from fixture is preserved regardless of formatting."""
        state = UNDEF_ITEM["state"]
        is_quantity = UNDEF_ITEM["type"].startswith("Number:")

        result = format_value(state, "°C", "%.1f", is_quantity_type=is_quantity)

        assert result == "UNDEF"

    def test_null_from_fixture(self) -> None:
        """NULL state from fixture is preserved regardless of formatting."""
        state = NULL_ITEM["state"]
        is_quantity = NULL_ITEM["type"].startswith("Number:")

        result = format_value(state, "W", "%d", is_quantity_type=is_quantity)

        assert result == "NULL"


class TestFormatValueNonQuantityTypes:
    """Tests for non-QuantityType items using real fixtures.

    Technique: Specification-based Testing — non-numeric state handling.
    """

    def test_switch_state_preserved(self) -> None:
        """Switch ON/OFF state is preserved as-is."""
        state = SWITCH_ITEM["state"]

        result = format_value(state, "", "%s", is_quantity_type=False)

        assert result == "ON"

    def test_contact_state_preserved(self) -> None:
        """Contact OPEN/CLOSED state is preserved as-is."""
        state = CONTACT_ITEM["state"]

        result = format_value(state, "", "%s", is_quantity_type=False)

        assert result == "CLOSED"


class TestFormatValueBankersRounding:
    """Tests verifying Python's banker's rounding behavior.

    Technique: Boundary Value Analysis — edge cases at .5 boundaries.

    Note: Python's round() uses "round half to even" (banker's rounding).
    These are synthetic tests as fixtures don't cover these edge cases.
    """

    def test_bankers_rounding_even_rounds_down(self) -> None:
        """Banker's rounding: 2.5 rounds to 2 (nearest even)."""
        result = format_value("2.5", "", "%d", is_quantity_type=False)
        assert result == "2"

    def test_bankers_rounding_odd_rounds_up(self) -> None:
        """Banker's rounding: 3.5 rounds to 4 (nearest even)."""
        result = format_value("3.5", "", "%d", is_quantity_type=False)
        assert result == "4"

    def test_negative_rounding(self) -> None:
        """Negative values round correctly."""
        result = format_value("-15.7", "", "%d", is_quantity_type=False)
        assert result == "-16"


class TestFormatValuePrecisionEdges:
    """Tests for formatting precision edge cases.

    Technique: Boundary Value Analysis — precision limits.
    """

    def test_float_pads_with_zeros(self) -> None:
        """Float format pads with trailing zeros as needed."""
        result = format_value("21", "", "%.2f", is_quantity_type=False)
        assert result == "21.00"

    def test_very_small_value(self) -> None:
        """Float format handles very small values."""
        result = format_value("0.001", "", "%.3f", is_quantity_type=False)
        assert result == "0.001"

    def test_very_large_value(self) -> None:
        """Float format handles large values without scientific notation."""
        result = format_value("123456789.5", "", "%.1f", is_quantity_type=False)
        assert result == "123456789.5"


class TestFormatValueNoFormatting:
    """Tests for early return when no formatting is needed.

    Technique: Branch Coverage — no-op path.
    """

    def test_no_unit_no_format_returns_unchanged(self) -> None:
        """Empty unit and format returns state as-is."""
        result = format_value("some value", "", "", is_quantity_type=False)
        assert result == "some value"


class TestFormatValueEncodingEdgeCases:
    """Tests for encoding-related edge cases.

    Technique: Error Guessing — encoding issues from lessons learned.
    """

    def test_unicode_degree_stripped_correctly(self) -> None:
        """Unicode degree symbol in state is stripped correctly."""
        result = format_value("21.5 °C", "°C", "%.1f", is_quantity_type=True)
        assert result == "21.5"

    def test_double_encoded_degree_matched(self) -> None:
        """Double-encoded degree (Â°) in state with matching unit is stripped."""
        result = format_value("21.5 Â°C", "Â°C", "%.1f", is_quantity_type=True)
        assert result == "21.5"

    def test_mismatched_encoding_not_stripped(self) -> None:
        """Mismatched encoding between state and unit prevents stripping."""
        result = format_value("21.5 °C", "Â°C", "%.1f", is_quantity_type=True)
        # No stripping because "°C" doesn't end with "Â°C"
        assert result == "21.5 °C"

    def test_unicode_cubed_stripped(self) -> None:
        """Unicode cubed symbol (³) in state is handled."""
        result = format_value("1.234 m³", "m³", "%.3f", is_quantity_type=True)
        assert result == "1.234"

    def test_cjk_unit_stripped(self) -> None:
        """CJK unit symbols are stripped correctly."""
        result = format_value("1.234 ㎥", "㎥", "%.3f", is_quantity_type=True)
        assert result == "1.234"


class TestFormatValueMismatchedUnitEdgeCase:
    """Tests for edge cases with mismatched units.

    Technique: Error Guessing — documenting unexpected behavior.
    """

    def test_partial_unit_match_causes_unexpected_stripping(self) -> None:
        """Partial unit match documents unexpected behavior.

        When state is "100 kWh" and unit is "Wh", the string ends with "Wh"
        so stripping occurs, leaving "100 k" which can't be parsed as float.
        """
        result = format_value("100 kWh", "Wh", "%.1f", is_quantity_type=True)
        # "100 k" can't be parsed as float, returned as-is
        assert result == "100 k"
