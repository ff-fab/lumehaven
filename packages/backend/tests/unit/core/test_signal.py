"""Unit tests for core/signal.py — Signal dataclass and helpers.

Test Techniques Used:
- Specification-based: Verifying dataclass contract (creation, defaults, frozen)
- Round-trip testing: to_dict() / from_dict() transformation fidelity
- Decision Table: from_dict() with required/optional field combinations
- Branch Coverage: is_undefined() boolean conditions
- Error Guessing: Mutation of frozen dataclass
"""

import pytest

from lumehaven.core.signal import (
    NULL_VALUE,
    UNDEFINED_VALUE,
    Signal,
    is_undefined,
)


class TestSignalCreation:
    """Specification-based tests for Signal dataclass creation."""

    def test_create_with_all_fields(self) -> None:
        """Signal can be created with all fields explicitly set."""
        signal = Signal(
            id="living_room_temp",
            value="21.5",
            unit="°C",
            label="Living Room Temperature",
        )

        assert signal.id == "living_room_temp"
        assert signal.value == "21.5"
        assert signal.unit == "°C"
        assert signal.label == "Living Room Temperature"

    def test_create_with_required_fields_only(self) -> None:
        """Signal can be created with only required fields (id, value)."""
        signal = Signal(id="switch_1", value="ON")

        assert signal.id == "switch_1"
        assert signal.value == "ON"
        assert signal.unit == ""  # Default
        assert signal.label == ""  # Default

    def test_frozen_immutability(self) -> None:
        """Signal is frozen — mutation raises FrozenInstanceError.

        Technique: Error Guessing — anticipating specific failure mode.
        """
        signal = Signal(id="test", value="100")

        with pytest.raises(AttributeError, match="cannot assign"):
            signal.value = "200"  # type: ignore[misc]

    def test_slots_optimization(self) -> None:
        """Signal uses __slots__ for memory efficiency."""
        signal = Signal(id="test", value="100")

        # Slots-based classes don't have __dict__
        assert not hasattr(signal, "__dict__")


class TestSignalToDict:
    """Round-trip testing for Signal.to_dict()."""

    def test_to_dict_includes_all_fields(self) -> None:
        """to_dict() returns dictionary with all four fields."""
        signal = Signal(id="temp", value="21.5", unit="°C", label="Temperature")

        result = signal.to_dict()

        assert result == {
            "id": "temp",
            "value": "21.5",
            "unit": "°C",
            "label": "Temperature",
        }

    def test_to_dict_with_defaults(self) -> None:
        """to_dict() includes default empty strings for unit and label."""
        signal = Signal(id="switch", value="ON")

        result = signal.to_dict()

        assert result == {
            "id": "switch",
            "value": "ON",
            "unit": "",
            "label": "",
        }


class TestSignalFromDict:
    """Decision Table testing for Signal.from_dict().

    | id present | value present | unit present | label present | Result    |
    |------------|---------------|--------------|---------------|-----------|
    | Yes        | Yes           | Yes          | Yes           | Success   |
    | Yes        | Yes           | No           | No            | Success   |
    | No         | Yes           | -            | -             | KeyError  |
    | Yes        | No            | -            | -             | KeyError  |
    """

    def test_from_dict_all_fields(self) -> None:
        """from_dict() with all fields creates complete Signal."""
        data = {"id": "temp", "value": "21.5", "unit": "°C", "label": "Temperature"}

        signal = Signal.from_dict(data)

        assert signal.id == "temp"
        assert signal.value == "21.5"
        assert signal.unit == "°C"
        assert signal.label == "Temperature"

    def test_from_dict_required_only(self) -> None:
        """from_dict() with only required fields uses defaults."""
        data = {"id": "switch", "value": "ON"}

        signal = Signal.from_dict(data)

        assert signal.id == "switch"
        assert signal.value == "ON"
        assert signal.unit == ""
        assert signal.label == ""

    def test_from_dict_missing_id_raises_key_error(self) -> None:
        """from_dict() without 'id' raises KeyError."""
        data = {"value": "ON"}

        with pytest.raises(KeyError, match="id"):
            Signal.from_dict(data)

    def test_from_dict_missing_value_raises_key_error(self) -> None:
        """from_dict() without 'value' raises KeyError."""
        data = {"id": "switch"}

        with pytest.raises(KeyError, match="value"):
            Signal.from_dict(data)


class TestSignalRoundTrip:
    """Round-trip testing: to_dict() → from_dict() preserves data."""

    @pytest.mark.parametrize(
        "signal",
        [
            Signal(id="temp", value="21.5", unit="°C", label="Temperature"),
            Signal(id="switch", value="ON"),
            Signal(id="power", value="1250", unit="W", label=""),
        ],
        ids=["full", "minimal", "partial"],
    )
    def test_round_trip_preserves_data(self, signal: Signal) -> None:
        """Converting Signal → dict → Signal yields equal object."""
        reconstructed = Signal.from_dict(signal.to_dict())

        assert reconstructed == signal


class TestIsUndefined:
    """Branch Coverage testing for is_undefined() boolean function.

    The function tests: value in (UNDEFINED_VALUE, NULL_VALUE)
    We need both True branches and the False branch.
    """

    @pytest.mark.parametrize(
        "value,expected",
        [
            (UNDEFINED_VALUE, True),  # Matches first item in tuple
            (NULL_VALUE, True),  # Matches second item in tuple
            ("ON", False),  # Normal value — false branch
            ("21.5", False),  # Numeric string — false branch
            ("", False),  # Empty string — edge case, still false
        ],
        ids=["UNDEF", "NULL", "normal-ON", "normal-numeric", "empty-string"],
    )
    def test_is_undefined(self, value: str, expected: bool) -> None:
        """is_undefined() correctly identifies undefined states."""
        assert is_undefined(value) is expected


class TestSentinelConstants:
    """Sanity tests for sentinel constant values."""

    def test_undefined_value_constant(self) -> None:
        """UNDEFINED_VALUE matches OpenHAB's undefined state string."""
        assert UNDEFINED_VALUE == "UNDEF"

    def test_null_value_constant(self) -> None:
        """NULL_VALUE matches OpenHAB's null state string."""
        assert NULL_VALUE == "NULL"
