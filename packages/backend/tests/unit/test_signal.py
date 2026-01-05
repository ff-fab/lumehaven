"""Unit tests for the Signal model."""

import pytest

from lumehaven.core.signal import Signal, is_undefined, UNDEFINED_VALUE, NULL_VALUE


class TestSignal:
    """Tests for the Signal dataclass."""

    def test_create_with_all_fields(self) -> None:
        """Signal can be created with all fields."""
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

    def test_create_with_defaults(self) -> None:
        """Signal uses empty strings as defaults for optional fields."""
        signal = Signal(id="switch", value="ON")

        assert signal.id == "switch"
        assert signal.value == "ON"
        assert signal.unit == ""
        assert signal.label == ""

    def test_immutable(self) -> None:
        """Signal is immutable (frozen)."""
        signal = Signal(id="test", value="123")

        with pytest.raises(AttributeError):
            signal.value = "456"  # type: ignore[misc]

    def test_to_dict(self) -> None:
        """Signal can be converted to dictionary."""
        signal = Signal(id="temp", value="20", unit="°C", label="Temperature")

        result = signal.to_dict()

        assert result == {
            "id": "temp",
            "value": "20",
            "unit": "°C",
            "label": "Temperature",
        }

    def test_from_dict(self) -> None:
        """Signal can be created from dictionary."""
        data = {
            "id": "temp",
            "value": "20",
            "unit": "°C",
            "label": "Temperature",
        }

        signal = Signal.from_dict(data)

        assert signal.id == "temp"
        assert signal.value == "20"
        assert signal.unit == "°C"
        assert signal.label == "Temperature"

    def test_from_dict_missing_optional_fields(self) -> None:
        """Signal.from_dict handles missing optional fields."""
        data = {"id": "switch", "value": "ON"}

        signal = Signal.from_dict(data)

        assert signal.unit == ""
        assert signal.label == ""

    def test_from_dict_missing_required_fields(self) -> None:
        """Signal.from_dict raises KeyError for missing required fields."""
        with pytest.raises(KeyError):
            Signal.from_dict({"id": "test"})  # missing value

        with pytest.raises(KeyError):
            Signal.from_dict({"value": "test"})  # missing id

    def test_equality(self) -> None:
        """Signals with same values are equal."""
        signal1 = Signal(id="test", value="123", unit="W")
        signal2 = Signal(id="test", value="123", unit="W")

        assert signal1 == signal2

    def test_hashable(self) -> None:
        """Signals can be used in sets and as dict keys."""
        signal1 = Signal(id="test", value="123")
        signal2 = Signal(id="test", value="456")

        # Can be added to set
        signal_set = {signal1, signal2}
        assert len(signal_set) == 2

        # Can be used as dict key
        signal_dict = {signal1: "first", signal2: "second"}
        assert signal_dict[signal1] == "first"


class TestIsUndefined:
    """Tests for the is_undefined helper function."""

    def test_undef_value(self) -> None:
        """UNDEF is recognized as undefined."""
        assert is_undefined(UNDEFINED_VALUE) is True
        assert is_undefined("UNDEF") is True

    def test_null_value(self) -> None:
        """NULL is recognized as undefined."""
        assert is_undefined(NULL_VALUE) is True
        assert is_undefined("NULL") is True

    def test_normal_values(self) -> None:
        """Normal values are not undefined."""
        assert is_undefined("21.5") is False
        assert is_undefined("ON") is False
        assert is_undefined("") is False
        assert is_undefined("0") is False
