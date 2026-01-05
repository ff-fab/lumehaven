"""Unit tests for OpenHAB unit extraction and value formatting."""

import pytest

from lumehaven.adapters.openhab.units import (
    extract_unit_from_pattern,
    format_value,
    get_default_units,
)


class TestGetDefaultUnits:
    """Tests for get_default_units function."""

    def test_si_units(self) -> None:
        """SI units are returned correctly."""
        units = get_default_units("SI")

        assert units["Temperature"] == "°C"
        assert units["Power"] == "W"
        assert units["Length"] == "m"
        assert units["Volume"] == "l"

    def test_us_units(self) -> None:
        """US units override SI defaults."""
        units = get_default_units("US")

        # US overrides
        assert units["Temperature"] == "°F"
        assert units["Length"] == "in"
        assert units["Volume"] == "gal"

        # Still has SI units for non-overridden types
        assert units["Power"] == "W"
        assert units["ElectricCurrent"] == "A"

    def test_default_is_si(self) -> None:
        """Default measurement system is SI."""
        units = get_default_units()
        assert units["Temperature"] == "°C"


class TestExtractUnitFromPattern:
    """Tests for extract_unit_from_pattern function."""

    def test_float_with_unit(self) -> None:
        """Extract unit from float pattern like '%.1f °C'."""
        unit, fmt = extract_unit_from_pattern("%.1f °C")

        assert unit == "°C"
        assert fmt == "%.1f"

    def test_integer_with_percent(self) -> None:
        """Extract percent sign from '%d %%'."""
        unit, fmt = extract_unit_from_pattern("%d %%")

        assert unit == "%"
        assert fmt == "%d"

    def test_string_format_only(self) -> None:
        """Pattern with no unit returns empty unit."""
        unit, fmt = extract_unit_from_pattern("%s")

        assert unit == ""
        assert fmt == "%s"

    def test_complex_float_format(self) -> None:
        """Extract unit from complex float pattern."""
        unit, fmt = extract_unit_from_pattern("%.2f kWh")

        assert unit == "kWh"
        assert fmt == "%.2f"

    def test_no_format_specifier(self) -> None:
        """Pattern without format specifier returns pattern as unit."""
        unit, fmt = extract_unit_from_pattern("ON/OFF")

        assert unit == "ON/OFF"
        assert fmt == "%s"

    def test_unit_with_special_chars(self) -> None:
        """Units with special characters are preserved."""
        unit, fmt = extract_unit_from_pattern("%.0f m³")

        assert unit == "m³"
        assert fmt == "%.0f"


class TestFormatValue:
    """Tests for format_value function."""

    def test_undef_preserved(self) -> None:
        """UNDEF value is returned unchanged."""
        result = format_value("UNDEF", "°C", "%.1f", is_quantity_type=True)

        assert result == "UNDEF"

    def test_null_preserved(self) -> None:
        """NULL value is returned unchanged."""
        result = format_value("NULL", "°C", "%.1f", is_quantity_type=True)

        assert result == "NULL"

    def test_strip_unit_from_quantity_type(self) -> None:
        """Unit is stripped from QuantityType state."""
        result = format_value("21.5 °C", "°C", "%s", is_quantity_type=True)

        assert result == "21.5"

    def test_float_formatting(self) -> None:
        """Float values are formatted according to pattern."""
        result = format_value("21.5678 °C", "°C", "%.1f", is_quantity_type=True)

        assert result == "21.6"

    def test_integer_formatting(self) -> None:
        """Integer formatting rounds the value."""
        result = format_value("21.7 °C", "°C", "%d", is_quantity_type=True)

        assert result == "22"

    def test_non_quantity_type(self) -> None:
        """Non-QuantityType values don't have units stripped."""
        result = format_value("42", "", "%d", is_quantity_type=False)

        assert result == "42"

    def test_invalid_number_preserved(self) -> None:
        """Non-numeric values are preserved when formatting fails."""
        result = format_value("ON", "", "%d", is_quantity_type=False)

        assert result == "ON"

    def test_empty_format(self) -> None:
        """Empty format returns value as-is."""
        result = format_value("test", "", "", is_quantity_type=False)

        assert result == "test"

    def test_precision_formatting(self) -> None:
        """Various precision formats work correctly."""
        # Two decimal places
        result = format_value("123.456 W", "W", "%.2f", is_quantity_type=True)
        assert result == "123.46"

        # Zero decimal places (float format)
        result = format_value("123.456 W", "W", "%.0f", is_quantity_type=True)
        assert result == "123"
