"""Signal model - the unified data representation for smart home values.

This module defines the Signal dataclass as specified in ADR-005.
The Signal model is intentionally minimal, keeping the frontend "dumb"
by providing pre-formatted, display-ready values.

Key design decisions (from ADR-005):
- `value` is always a string, pre-formatted by the backend
- `unit` is the display symbol (e.g., "°C", not "CELSIUS")
- No metadata about ranges, types, or capabilities in the base model
- Backend normalizes all data; frontend just displays value + unit
"""

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Signal:
    """A unified smart home signal with display-ready values.

    This is the core data model that all smart home adapters convert to.
    The frontend receives these directly and renders them without transformation.

    Attributes:
        id: Unique identifier (OpenHAB item name / HA entity_id).
        value: Pre-formatted, display-ready value string.
        unit: Unit symbol for display (e.g., "°C", "%", "W").
        label: Human-readable name for the signal.

    Examples:
        >>> Signal(id="living_room_temp", value="21.5", unit="°C", label="Living Room")
        Signal(id='living_room_temp', value='21.5', unit='°C', label='Living Room')

        >>> Signal(id="light_switch", value="ON", unit="")
        Signal(id='light_switch', value='ON', unit='', label='')
    """

    id: str
    value: str
    unit: str = ""
    label: str = ""

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary with all signal fields.
        """
        return {
            "id": self.id,
            "value": self.value,
            "unit": self.unit,
            "label": self.label,
        }

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "Signal":
        """Create a Signal from a dictionary.

        Args:
            data: Dictionary with signal fields.

        Returns:
            New Signal instance.

        Raises:
            KeyError: If required fields (id, value) are missing.
        """
        return cls(
            id=data["id"],
            value=data["value"],
            unit=data.get("unit", ""),
            label=data.get("label", ""),
        )


# Sentinel for undefined/null states from smart home systems
UNDEFINED_VALUE = "UNDEF"
NULL_VALUE = "NULL"


def is_undefined(value: str) -> bool:
    """Check if a value represents an undefined state.

    OpenHAB and other systems use special strings for undefined states.
    This helper identifies them so callers can handle gracefully.

    Args:
        value: The value string to check.

    Returns:
        True if the value represents an undefined/null state.
    """
    return value in (UNDEFINED_VALUE, NULL_VALUE)
