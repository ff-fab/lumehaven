"""Unit extraction and value formatting for OpenHAB items.

This module handles the complexity of extracting display units and
formatting values from OpenHAB's state patterns and QuantityTypes.

Ported from PoC: old/backend/home-observer/openhab.py
Reference: old/backend/home-observer/units_of_measurement.json
"""

import re
from typing import Literal

from lumehaven.core.signal import NULL_VALUE, UNDEFINED_VALUE

# Default units by QuantityType for SI and US measurement systems
# Reference: https://www.openhab.org/docs/concepts/units-of-measurement.html
DEFAULT_UNITS: dict[str, dict[str, str]] = {
    "SI": {
        "Acceleration": "m/s²",
        "AmountOfSubstance": "mol",
        "Angle": "",
        "Area": "m²",
        "ArealDensity": "DU",
        "CatalyticActivity": "kat",
        "DataAmount": "bit",
        "DataTransferRate": "bit/s",
        "Density": "g/m³",
        "Dimensionless": "%",
        "ElectricPotential": "V",
        "ElectricCapacitance": "F",
        "ElectricCharge": "C",
        "ElectricConductance": "S",
        "ElectricConductivity": "S/m",
        "ElectricCurrent": "A",
        "ElectricInductance": "H",
        "ElectricResistance": "Ω",
        "Energy": "J",
        "Force": "N",
        "Frequency": "Hz",
        "Illuminance": "Lux",
        "Intensity": "W/m²",
        "Length": "m",
        "LuminousFlux": "lm",
        "LuminousIntensity": "cd",
        "MagneticFlux": "Wb",
        "MagneticFluxDensity": "T",
        "Mass": "g",
        "Power": "W",
        "Pressure": "Pa",
        "Radioactivity": "Bq",
        "RadiationDoseAbsorbed": "Gy",
        "RadiationDoseEffective": "Sv",
        "SolidAngle": "sr",
        "Speed": "m/s",
        "Temperature": "°C",
        "Time": "s",
        "Volume": "l",
        "VolumetricFlowRate": "l/min",
    },
    "US": {
        "Length": "in",
        "Pressure": "inHg",
        "Speed": "mph",
        "Temperature": "°F",
        "Volume": "gal",
        "VolumetricFlowRate": "gal/min",
    },
}


def get_default_units(system: Literal["SI", "US"] = "SI") -> dict[str, str]:
    """Get default units for a measurement system.

    For US system, returns SI defaults with US overrides applied.

    Args:
        system: Measurement system ("SI" or "US").

    Returns:
        Dictionary mapping QuantityType names to unit symbols.
    """
    if system == "US":
        # Start with SI, overlay US-specific units
        return DEFAULT_UNITS["SI"] | DEFAULT_UNITS["US"]
    return DEFAULT_UNITS["SI"].copy()


# Pattern to extract format specifier and unit from OpenHAB state patterns
# Examples: "%.1f °C" -> ("%f", "°C"), "%d %%" -> ("%d", "%"), "%s" -> ("%s", "")
PATTERN_REGEX = re.compile(r"(%\S*[fds])\s*(.*)")


def extract_unit_from_pattern(pattern: str) -> tuple[str, str]:
    """Extract unit and format from an OpenHAB state description pattern.

    Args:
        pattern: State pattern from OpenHAB (e.g., "%.1f °C", "%d %%").

    Returns:
        Tuple of (unit, format_string).
        Unit has %% replaced with % for display.
        Format string is like "%s", "%d", "%.2f".

    Examples:
        >>> extract_unit_from_pattern("%.1f °C")
        ('°C', '%.1f')
        >>> extract_unit_from_pattern("%d %%")
        ('%', '%d')
        >>> extract_unit_from_pattern("%s")
        ('', '%s')
    """
    match = PATTERN_REGEX.match(pattern)
    if match is None:
        return pattern, "%s"

    format_str = match.group(1)
    unit = match.group(2).replace("%%", "%")
    return unit, format_str


def format_value(
    state: str,
    unit: str,
    format_str: str,
    is_quantity_type: bool = False,
) -> str:
    """Format a raw state value according to the format pattern.

    Handles:
    - UNDEF/NULL states (returned as-is)
    - Stripping units from QuantityType states
    - Applying %d (integer) and %f (float) formatting

    Args:
        state: Raw state from OpenHAB (may include unit for QuantityTypes).
        unit: Expected unit suffix to strip.
        format_str: Format pattern (e.g., "%d", "%.1f", "%s").
        is_quantity_type: Whether the item is a QuantityType.

    Returns:
        Formatted value string ready for display.

    Examples:
        >>> format_value("21.5678 °C", "°C", "%.1f", is_quantity_type=True)
        '21.6'
        >>> format_value("UNDEF", "°C", "%.1f", is_quantity_type=True)
        'UNDEF'
        >>> format_value("42", "", "%d", is_quantity_type=False)
        '42'
    """
    # Preserve undefined states
    if state in (UNDEFINED_VALUE, NULL_VALUE):
        return state

    # No formatting needed
    if not unit and not format_str:
        return state

    # Strip unit from QuantityType states
    # e.g., "21.5 °C" -> "21.5"
    if is_quantity_type and unit and state.endswith(unit):
        value = state[: -len(unit)].rstrip()
    else:
        value = state.rstrip()

    # Apply numeric formatting
    try:
        if format_str.endswith("d"):
            return format_str % round(float(value))
        elif format_str.endswith("f"):
            return format_str % float(value)
    except ValueError, TypeError:
        # Can't convert to number, return as-is
        pass

    return value
