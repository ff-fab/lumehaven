"""Signal model - the unified data representation for smart home values.

This module defines the Signal dataclass as specified in ADR-005, enriched
per ADR-010 with typed values, display formatting, availability, and type
discrimination.

Key design decisions (from ADR-005, amended by ADR-010):
- ``value`` is typed (str | int | float | bool | None) for frontend logic
- ``display_value`` is the pre-formatted string the frontend renders
- ``available`` indicates whether the signal has a valid value
- ``signal_type`` discriminates the semantic type for UI rendering
- ``unit`` is the display symbol (e.g., "°C", not "CELSIUS")
- Backend normalizes all data; frontend uses display_value + unit for display
  and value for logic (thresholds, toggles, sorting)
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class SignalType(StrEnum):
    """Semantic type discriminator for signal values.

    Enables type-aware rendering without string parsing.  The frontend
    can use ``signal_type`` to select component variants (slider for
    NUMBER, toggle for BOOLEAN, etc.) without inspecting ``value``.

    Members:
        STRING: Free-form text (weather descriptions, messages).
        NUMBER: Numeric values (temperature, humidity, power).
        BOOLEAN: Binary states (ON/OFF, OPEN/CLOSED, motion detected).
        ENUM: Finite set of named states (washing-machine modes, HVAC).
        DATETIME: ISO-8601 timestamps.
    """

    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ENUM = "enum"
    DATETIME = "datetime"


# Type alias for the enriched value union (ADR-010).
SignalValue = str | int | float | bool | None


@dataclass(frozen=True, slots=True)
class Signal:
    """A unified smart home signal with enriched, display-ready values.

    This is the core data model that all smart home adapters convert to.
    The frontend uses ``display_value`` for rendering and ``value`` for
    logic (thresholds, sorting, conditional display).

    Attributes:
        id: Unique identifier (adapter-prefixed, e.g. ``"oh:LivingRoom_Temp"``).
        value: Typed native value for frontend logic.  ``None`` when unavailable.
        unit: Unit symbol for display (e.g. "°C", "%", "W").
        label: Human-readable name for the signal.
        display_value: Pre-formatted string the frontend renders as-is.
        available: ``False`` when the device reports UNDEF / NULL / unavailable.
        signal_type: Semantic type discriminator for UI component selection.

    Examples:
        >>> s = Signal(
        ...     id="oh:LivingRoom_Temp", value=21.5,
        ...     display_value="21.5", unit="°C",
        ...     label="Living Room",
        ...     signal_type=SignalType.NUMBER,
        ... )
        >>> s.value, s.signal_type
        (21.5, <SignalType.NUMBER: 'number'>)

        >>> s = Signal(
        ...     id="oh:Sensor_Offline", value=None,
        ...     display_value="", available=False,
        ... )
        >>> s.available, s.value
        (False, None)
    """

    id: str
    value: SignalValue
    unit: str = ""
    label: str = ""
    display_value: str = ""
    available: bool = True
    signal_type: SignalType = SignalType.STRING

    def __post_init__(self) -> None:
        """Auto-populate display_value from value if empty.

        During the transition to ADR-010 enrichment, adapters may not
        explicitly set display_value. This ensures a safe default by
        computing it from the value (when not specified and value is not None).
        Uses object.__setattr__ because the dataclass is frozen=True.
        """
        if not self.display_value and self.value is not None:
            object.__setattr__(self, "display_value", str(self.value))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary with all signal fields.  ``signal_type`` is
            serialized as its string value (e.g. ``"number"``).
        """
        return {
            "id": self.id,
            "value": self.value,
            "display_value": self.display_value,
            "unit": self.unit,
            "label": self.label,
            "available": self.available,
            "signal_type": self.signal_type.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Signal:
        """Create a Signal from a dictionary.

        Handles both the enriched format (ADR-010) and the legacy
        four-field format for backward compatibility. Normalizes legacy
        sentinel values (UNDEF/NULL) to the enriched representation.

        Args:
            data: Dictionary with signal fields.

        Returns:
            New Signal instance.

        Raises:
            KeyError: If required fields ``id`` or ``value`` are missing.
            ValueError: If ``signal_type`` is present but not a valid
                ``SignalType`` member.
        """
        # Determine value: enriched dicts may have explicit None
        if "value" in data:
            value = data["value"]
        else:
            raise KeyError("value")

        # Normalize legacy sentinels (ADR-005 → ADR-010 transition).
        # Convert UNDEF/NULL strings to None with available=False.
        if isinstance(value, str) and value in (UNDEFINED_VALUE, NULL_VALUE):
            value = None

        # Parse signal_type from string if present
        raw_type = data.get("signal_type")
        signal_type = (
            SignalType(raw_type) if raw_type is not None else SignalType.STRING
        )

        # Default available based on value when not explicitly provided.
        # Enriched dicts include explicit available; legacy dicts without it
        # infer from whether value is None (after sentinel normalization).
        available = data.get("available", value is not None)

        return cls(
            id=data["id"],
            value=value,
            display_value=data.get(
                "display_value", str(value) if value is not None else ""
            ),
            unit=data.get("unit", ""),
            label=data.get("label", ""),
            available=available,
            signal_type=signal_type,
        )


# Sentinel for undefined/null states from smart home systems.
# These are internal adapter constants — NOT part of the API contract.
# Adapters use them to set ``available=False`` and ``value=None``.
UNDEFINED_VALUE = "UNDEF"
NULL_VALUE = "NULL"


def is_undefined(value: str) -> bool:
    """Check if a value represents an undefined state.

    .. deprecated::
        Use ``signal.available`` instead (ADR-010).  This helper is retained
        for adapter-internal use during the transition period but should not
        appear in new code.

    OpenHAB and other systems use special strings for undefined states.
    This helper identifies them so callers can handle gracefully.

    Args:
        value: The value string to check.

    Returns:
        True if the value represents an undefined/null state.
    """
    warnings.warn(
        "is_undefined() is deprecated — use signal.available instead (ADR-010)",
        DeprecationWarning,
        stacklevel=2,
    )
    return value in (UNDEFINED_VALUE, NULL_VALUE)
