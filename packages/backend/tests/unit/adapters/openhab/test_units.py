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

# =============================================================================
# Tests
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
        # US should have fewer entries than SI (it's just overrides)
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

        # US overrides
        assert result["Temperature"] == "°F"
        assert result["Length"] == "in"
        assert result["Volume"] == "gal"

    def test_us_preserves_non_overridden_si_units(self) -> None:
        """US system preserves SI units that aren't overridden."""
        result = get_default_units("US")

        # These should still be SI values
        assert result["Power"] == "W"
        assert result["Energy"] == "J"
        assert result["ElectricCurrent"] == "A"

    def test_si_returns_copy_not_reference(self) -> None:
        """SI result is a copy, not the original dict."""
        result = get_default_units("SI")

        # Modifying result shouldn't affect DEFAULT_UNITS
        result["Temperature"] = "K"
        assert DEFAULT_UNITS["SI"]["Temperature"] == "°C"

    def test_us_result_has_all_si_keys_plus_overrides(self) -> None:
        """US result contains all SI keys with overrides applied."""
        si_result = get_default_units("SI")
        us_result = get_default_units("US")

        # US should have same keys as SI (overrides don't add new keys)
        assert set(us_result.keys()) == set(si_result.keys())


# =============================================================================
# Test extract_unit_from_pattern()
# =============================================================================


class TestExtractUnitFromPatternFloatFormat:
    """Tests for float format patterns (%.Nf).

    Technique: Equivalence Partitioning — float format class.
    """

    @pytest.mark.parametrize(
        ("pattern", "expected_unit", "expected_format"),
        [
            ("%.1f °C", "°C", "%.1f"),
            ("%.2f kWh", "kWh", "%.2f"),
            ("%.0f W", "W", "%.0f"),
            ("%.3f m³", "m³", "%.3f"),
            ("%f", "", "%f"),  # No precision, no unit
        ],
        ids=[
            "one_decimal_celsius",
            "two_decimal_energy",
            "zero_decimal_power",
            "three_decimal_volume",
            "bare_float_no_unit",
        ],
    )
    def test_float_patterns(
        self, pattern: str, expected_unit: str, expected_format: str
    ) -> None:
        """Float format patterns extract unit and format correctly."""
        unit, format_str = extract_unit_from_pattern(pattern)

        assert unit == expected_unit
        assert format_str == expected_format


class TestExtractUnitFromPatternIntegerFormat:
    """Tests for integer format patterns (%d).

    Technique: Equivalence Partitioning — integer format class.
    """

    @pytest.mark.parametrize(
        ("pattern", "expected_unit", "expected_format"),
        [
            ("%d W", "W", "%d"),
            ("%d lx", "lx", "%d"),
            ("%d", "", "%d"),  # No unit
        ],
        ids=["power_watts", "illuminance_lux", "bare_integer"],
    )
    def test_integer_patterns(
        self, pattern: str, expected_unit: str, expected_format: str
    ) -> None:
        """Integer format patterns extract unit and format correctly."""
        unit, format_str = extract_unit_from_pattern(pattern)

        assert unit == expected_unit
        assert format_str == expected_format


class TestExtractUnitFromPatternStringFormat:
    """Tests for string format patterns (%s).

    Technique: Equivalence Partitioning — string format class.
    """

    @pytest.mark.parametrize(
        ("pattern", "expected_unit", "expected_format"),
        [
            ("%s", "", "%s"),
            ("%s status", "status", "%s"),
        ],
        ids=["bare_string", "string_with_suffix"],
    )
    def test_string_patterns(
        self, pattern: str, expected_unit: str, expected_format: str
    ) -> None:
        """String format patterns extract unit and format correctly."""
        unit, format_str = extract_unit_from_pattern(pattern)

        assert unit == expected_unit
        assert format_str == expected_format


class TestExtractUnitFromPatternPercentLiteral:
    """Tests for percent literal patterns (%%).

    Technique: Specification-based Testing — docstring example verification.
    """

    def test_percent_literal_converted_to_single_percent(self) -> None:
        """Double percent (%%) in pattern becomes single % in unit."""
        unit, format_str = extract_unit_from_pattern("%d %%")

        assert unit == "%"
        assert format_str == "%d"

    def test_float_with_percent_literal(self) -> None:
        """Float format with percent literal."""
        unit, format_str = extract_unit_from_pattern("%.1f %%")

        assert unit == "%"
        assert format_str == "%.1f"


class TestExtractUnitFromPatternNoMatch:
    """Tests for patterns that don't match the regex (fallback behavior).

    Technique: Branch Coverage — regex no-match path.
    """

    @pytest.mark.parametrize(
        ("pattern", "expected_unit", "expected_format"),
        [
            ("Wh", "Wh", "%s"),  # No format specifier
            ("€/Monat", "€/Monat", "%s"),  # Currency without format
            ("ppm", "ppm", "%s"),  # Plain unit
            ("", "", "%s"),  # Empty string
            ("ON", "ON", "%s"),  # State value (shouldn't match)
        ],
        ids=["energy_unit_only", "currency", "ppm_unit", "empty", "state_value"],
    )
    def test_no_match_returns_pattern_as_unit_with_string_format(
        self, pattern: str, expected_unit: str, expected_format: str
    ) -> None:
        """Non-matching patterns return pattern as unit with %s format."""
        unit, format_str = extract_unit_from_pattern(pattern)

        assert unit == expected_unit
        assert format_str == expected_format


class TestExtractUnitFromPatternSpecialCases:
    """Tests for special/edge case patterns.

    Technique: Error Guessing — anticipating real-world edge cases.
    """

    def test_dynamic_unit_placeholder(self) -> None:
        """OpenHAB's %unit% placeholder is captured as unit."""
        unit, format_str = extract_unit_from_pattern("%.0f %unit%")

        assert unit == "%unit%"
        assert format_str == "%.0f"

    def test_transformation_pattern_no_match(self) -> None:
        """Transformation patterns (JS, MAP) don't match standard regex."""
        # These use special OpenHAB transformation syntax
        unit, format_str = extract_unit_from_pattern("JS(elapsed-time.js):%s")

        # The whole thing becomes the "unit" in fallback
        assert unit == "JS(elapsed-time.js):%s"
        assert format_str == "%s"

    def test_unicode_degree_symbol(self) -> None:
        """Unicode degree symbol (°) is handled correctly."""
        unit, format_str = extract_unit_from_pattern("%.1f °C")

        assert unit == "°C"
        assert "°" in unit  # Verify it's the real degree symbol

    def test_unicode_cubed_symbol(self) -> None:
        """Unicode superscript 3 (³) for volume is handled."""
        unit, format_str = extract_unit_from_pattern("%.3f m³")

        assert unit == "m³"

    def test_unicode_squared_symbol(self) -> None:
        """Unicode superscript 2 (²) for area is handled."""
        unit, format_str = extract_unit_from_pattern("%.2f m²")

        assert unit == "m²"


class TestExtractUnitFromPatternEncodingEdgeCases:
    """Tests for encoding-related edge cases.

    Technique: Error Guessing — real encoding issues from lessons learned.

    Note: These test that the function handles various Unicode representations.
    The PoC encountered issues with "Â°" appearing instead of "°" due to
    UTF-8 double-encoding.
    """

    def test_correct_degree_symbol_utf8(self) -> None:
        """Correctly encoded UTF-8 degree symbol works."""
        unit, _ = extract_unit_from_pattern("%.1f °C")

        # Should be the proper Unicode degree symbol (U+00B0)
        assert unit == "°C"
        assert ord(unit[0]) == 0x00B0

    def test_double_encoded_degree_symbol(self) -> None:
        """Double-encoded degree symbol (Â°) is passed through as-is.

        This represents a data quality issue from the source, not a parsing error.
        The function doesn't fix encoding issues — it preserves them for upstream
        handling (e.g., ftfy library).
        """
        # Simulated double-encoding: UTF-8 bytes of "°" interpreted as Latin-1
        # then re-encoded as UTF-8 produces "Â°"
        malformed_pattern = "%.1f Â°C"
        unit, format_str = extract_unit_from_pattern(malformed_pattern)

        # Function preserves the malformed encoding
        assert unit == "Â°C"
        assert format_str == "%.1f"

    def test_fullwidth_percent_sign(self) -> None:
        """Fullwidth percent sign (％) in unit is preserved."""
        # Some systems use fullwidth characters
        unit, format_str = extract_unit_from_pattern("%d ％")

        assert unit == "％"  # U+FF05 fullwidth percent
        assert format_str == "%d"


# =============================================================================
# Test format_value()
# =============================================================================


class TestFormatValueUndefinedStates:
    """Tests for UNDEF/NULL state preservation.

    Technique: Specification-based Testing — undefined state contract.
    """

    def test_undef_state_returned_unchanged(self) -> None:
        """UNDEF state is returned as-is regardless of other parameters."""
        result = format_value("UNDEF", "°C", "%.1f", is_quantity_type=True)

        assert result == "UNDEF"

    def test_null_state_returned_unchanged(self) -> None:
        """NULL state is returned as-is regardless of other parameters."""
        result = format_value("NULL", "W", "%d", is_quantity_type=True)

        assert result == "NULL"

    def test_undef_with_no_format(self) -> None:
        """UNDEF with empty format parameters is still preserved."""
        result = format_value("UNDEF", "", "", is_quantity_type=False)

        assert result == "UNDEF"


class TestFormatValueNoFormatting:
    """Tests for early return when no formatting is needed.

    Technique: Branch Coverage — no-op path.
    """

    def test_no_unit_no_format_returns_state_unchanged(self) -> None:
        """Empty unit and format returns state as-is."""
        result = format_value("some value", "", "", is_quantity_type=False)

        assert result == "some value"

    def test_state_with_trailing_whitespace_preserved_when_no_format(self) -> None:
        """State with trailing whitespace is returned when no formatting needed."""
        result = format_value("value  ", "", "", is_quantity_type=False)

        assert result == "value  "


class TestFormatValueQuantityTypeStripping:
    """Tests for unit stripping from QuantityType states.

    Technique: Decision Table — is_quantity_type × has_unit combinations.
    """

    def test_quantity_type_strips_unit_suffix(self) -> None:
        """QuantityType state has unit suffix stripped."""
        result = format_value("21.5 °C", "°C", "%.1f", is_quantity_type=True)

        assert result == "21.5"

    def test_quantity_type_strips_unit_with_integer_format(self) -> None:
        """QuantityType with integer format strips unit and rounds."""
        result = format_value("1250 W", "W", "%d", is_quantity_type=True)

        assert result == "1250"

    def test_non_quantity_type_preserves_value(self) -> None:
        """Non-QuantityType state is not unit-stripped."""
        result = format_value("75", "", "%d", is_quantity_type=False)

        assert result == "75"

    def test_quantity_type_with_mismatched_unit_not_stripped(self) -> None:
        """QuantityType with partially matching unit suffix has unexpected behavior.

        Note: This documents actual behavior, not necessarily ideal behavior.
        When state is "100 kWh" and unit is "Wh", the string ends with "Wh"
        so stripping occurs, leaving "100 k" which can't be parsed as float.
        """
        # State ends with "Wh" (as part of "kWh") so stripping occurs
        result = format_value("100 kWh", "Wh", "%.1f", is_quantity_type=True)

        # "100 k" can't be parsed as float, returned as-is
        assert result == "100 k"

    def test_quantity_type_unit_stripping_handles_whitespace(self) -> None:
        """Unit stripping also strips trailing whitespace from value."""
        result = format_value("21.5 °C", "°C", "%.1f", is_quantity_type=True)

        # "21.5 " after removing "°C" should become "21.5"
        assert result == "21.5"
        assert not result.endswith(" ")


class TestFormatValueIntegerFormatting:
    """Tests for integer (%d) formatting.

    Technique: Boundary Value Analysis — rounding at .5 boundaries.
    """

    def test_integer_format_rounds_float_value(self) -> None:
        """Integer format rounds float to nearest integer."""
        result = format_value("75.6", "", "%d", is_quantity_type=False)

        assert result == "76"

    def test_integer_format_rounds_up_at_point_five(self) -> None:
        """Integer format rounds 0.5 up (Python round behavior)."""
        # Note: Python uses banker's rounding, but round(75.5) = 76
        result = format_value("75.5", "", "%d", is_quantity_type=False)

        assert result == "76"

    def test_integer_format_rounds_down_below_point_five(self) -> None:
        """Integer format rounds down below .5."""
        result = format_value("75.4", "", "%d", is_quantity_type=False)

        assert result == "75"

    def test_integer_format_with_already_integer_value(self) -> None:
        """Integer format with integer string value."""
        result = format_value("42", "", "%d", is_quantity_type=False)

        assert result == "42"

    def test_integer_format_negative_value(self) -> None:
        """Integer format handles negative values."""
        result = format_value("-15.7", "", "%d", is_quantity_type=False)

        assert result == "-16"


class TestFormatValueFloatFormatting:
    """Tests for float (%f) formatting.

    Technique: Boundary Value Analysis — precision edges.
    """

    def test_float_format_one_decimal(self) -> None:
        """Float format with one decimal precision."""
        result = format_value("21.5678", "", "%.1f", is_quantity_type=False)

        assert result == "21.6"

    def test_float_format_two_decimals(self) -> None:
        """Float format with two decimal precision."""
        result = format_value("12345.6789", "", "%.2f", is_quantity_type=False)

        assert result == "12345.68"

    def test_float_format_zero_decimals(self) -> None:
        """Float format with zero decimal precision (rounds to integer)."""
        result = format_value("75.6", "", "%.0f", is_quantity_type=False)

        assert result == "76"

    def test_float_format_pads_with_zeros(self) -> None:
        """Float format pads with trailing zeros as needed."""
        result = format_value("21", "", "%.2f", is_quantity_type=False)

        assert result == "21.00"

    def test_float_format_negative_value(self) -> None:
        """Float format handles negative values."""
        result = format_value("-5.123", "", "%.1f", is_quantity_type=False)

        assert result == "-5.1"

    def test_float_format_very_small_value(self) -> None:
        """Float format handles very small values."""
        result = format_value("0.001", "", "%.3f", is_quantity_type=False)

        assert result == "0.001"

    def test_float_format_very_large_value(self) -> None:
        """Float format handles large values without scientific notation."""
        result = format_value("123456789.5", "", "%.1f", is_quantity_type=False)

        assert result == "123456789.5"


class TestFormatValueBankersRounding:
    """Tests verifying Python's banker's rounding behavior.

    Technique: Boundary Value Analysis — edge cases at .5 boundaries.

    Note: Python's round() uses "round half to even" (banker's rounding).
    This differs from Java's Math.round() which rounds half up.
    These tests document the actual behavior.
    """

    def test_bankers_rounding_even_rounds_down(self) -> None:
        """Banker's rounding: 2.5 rounds to 2 (nearest even)."""
        # round(2.5) = 2 in Python
        result = format_value("2.5", "", "%d", is_quantity_type=False)

        assert result == "2"

    def test_bankers_rounding_odd_rounds_up(self) -> None:
        """Banker's rounding: 3.5 rounds to 4 (nearest even)."""
        # round(3.5) = 4 in Python
        result = format_value("3.5", "", "%d", is_quantity_type=False)

        assert result == "4"


class TestFormatValueNonNumeric:
    """Tests for non-numeric value handling.

    Technique: Error Guessing — non-parseable values.
    """

    def test_non_numeric_string_returned_as_is(self) -> None:
        """Non-numeric string is returned unchanged."""
        result = format_value("ON", "", "%d", is_quantity_type=False)

        assert result == "ON"

    def test_state_like_open_closed(self) -> None:
        """State values like OPEN/CLOSED are preserved."""
        result = format_value("CLOSED", "", "%s", is_quantity_type=False)

        assert result == "CLOSED"

    def test_text_with_numeric_format_returns_text(self) -> None:
        """Text value with numeric format falls back to returning text."""
        result = format_value("Partly Cloudy", "", "%.1f", is_quantity_type=False)

        assert result == "Partly Cloudy"

    def test_empty_string_value(self) -> None:
        """Empty string value is preserved."""
        result = format_value("", "", "%s", is_quantity_type=False)

        assert result == ""


class TestFormatValueDecisionTable:
    """Decision table tests covering condition combinations.

    Technique: Decision Table Testing — systematic condition combinations.

    Dimensions:
    - is_undefined: True/False
    - has_unit: True/False
    - is_quantity_type: True/False
    - format_type: %d / %.Nf / %s / none
    - parseable_as_number: True/False
    """

    @pytest.mark.parametrize(
        ("state", "unit", "format_str", "is_quantity_type", "expected"),
        [
            # Undefined states (early return)
            ("UNDEF", "°C", "%.1f", True, "UNDEF"),
            ("NULL", "W", "%d", True, "NULL"),
            # QuantityType with unit stripping
            ("21.5 °C", "°C", "%.1f", True, "21.5"),
            ("1250 W", "W", "%d", True, "1250"),
            ("12345.67 kWh", "kWh", "%.2f", True, "12345.67"),
            # Non-QuantityType (no stripping)
            ("75", "", "%d", False, "75"),
            ("ON", "", "%s", False, "ON"),
            # QuantityType without matching unit
            ("100", "W", "%d", True, "100"),
            # No formatting parameters
            ("some value", "", "", False, "some value"),
            # Non-numeric with numeric format (fallback)
            ("OPEN", "", "%d", False, "OPEN"),
        ],
        ids=[
            "undef_quantity",
            "null_quantity",
            "temp_celsius",
            "power_watts",
            "energy_kwh",
            "plain_integer",
            "switch_state",
            "quantity_no_unit_in_state",
            "no_formatting",
            "contact_with_int_format",
        ],
    )
    def test_condition_combinations(
        self,
        state: str,
        unit: str,
        format_str: str,
        is_quantity_type: bool,
        expected: str,
    ) -> None:
        """Test various condition combinations per decision table."""
        result = format_value(state, unit, format_str, is_quantity_type)

        assert result == expected


class TestFormatValueRealOpenHABData:
    """Tests using real OpenHAB item patterns from fixtures.

    Technique: Specification-based Testing — real-world data verification.
    """

    def test_temperature_item(self) -> None:
        """Format temperature from TEMPERATURE_ITEM fixture."""
        # state: "21.5 °C", pattern: "%.1f °C"
        unit, format_str = extract_unit_from_pattern("%.1f °C")
        result = format_value("21.5 °C", unit, format_str, is_quantity_type=True)

        assert result == "21.5"

    def test_dimmer_item(self) -> None:
        """Format dimmer percentage from DIMMER_ITEM fixture."""
        # state: "75", pattern: "%d %%"
        unit, format_str = extract_unit_from_pattern("%d %%")
        result = format_value("75", unit, format_str, is_quantity_type=False)

        assert result == "75"

    def test_power_item(self) -> None:
        """Format power from POWER_ITEM fixture."""
        # state: "1250 W", pattern: "%d W"
        unit, format_str = extract_unit_from_pattern("%d W")
        result = format_value("1250 W", unit, format_str, is_quantity_type=True)

        assert result == "1250"

    def test_energy_item(self) -> None:
        """Format energy from ENERGY_ITEM fixture."""
        # state: "12345.67 kWh", pattern: "%.2f kWh"
        unit, format_str = extract_unit_from_pattern("%.2f kWh")
        result = format_value("12345.67 kWh", unit, format_str, is_quantity_type=True)

        assert result == "12345.67"

    def test_undef_item(self) -> None:
        """Format UNDEF state from UNDEF_ITEM fixture."""
        result = format_value("UNDEF", "°C", "%.1f", is_quantity_type=True)

        assert result == "UNDEF"


class TestFormatValueEncodingEdgeCases:
    """Tests for encoding-related edge cases in format_value.

    Technique: Error Guessing — encoding issues from lessons learned.
    """

    def test_unicode_degree_in_state_stripped_correctly(self) -> None:
        """Unicode degree symbol in state is stripped correctly."""
        result = format_value("21.5 °C", "°C", "%.1f", is_quantity_type=True)

        assert result == "21.5"

    def test_double_encoded_degree_in_state(self) -> None:
        """Double-encoded degree (Â°) in state with matching unit is stripped."""
        # If both state and unit have the same malformed encoding, stripping works
        result = format_value("21.5 Â°C", "Â°C", "%.1f", is_quantity_type=True)

        assert result == "21.5"

    def test_mismatched_encoding_not_stripped(self) -> None:
        """Mismatched encoding between state and unit prevents stripping."""
        # State has correct "°C" but unit has malformed "Â°C"
        result = format_value("21.5 °C", "Â°C", "%.1f", is_quantity_type=True)

        # No stripping because "°C" doesn't end with "Â°C"
        # Value "21.5 °C" can't be parsed as float, returned as-is
        assert result == "21.5 °C"

    def test_unicode_cubed_in_state(self) -> None:
        """Unicode cubed symbol (³) in state is handled."""
        result = format_value("1.234 m³", "m³", "%.3f", is_quantity_type=True)

        assert result == "1.234"

    def test_cjk_unit_symbols(self) -> None:
        """CJK unit symbols (㎥ for cubic meter) are preserved."""
        # Some systems use CJK compatibility characters
        unit, format_str = extract_unit_from_pattern("%.3f ㎥")

        assert unit == "㎥"  # U+33A5

        result = format_value("1.234 ㎥", "㎥", format_str, is_quantity_type=True)
        assert result == "1.234"
