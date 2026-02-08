"""Unit tests for core/signal.py — Signal dataclass, SignalType, and helpers.

Test Techniques Used:
- Specification-based: Verifying dataclass contract (creation, defaults, frozen)
- Round-trip testing: to_dict() / from_dict() transformation fidelity
- Decision Table: from_dict() with required/optional field combinations
- Branch Coverage: is_undefined() boolean conditions (deprecated path)
- Equivalence Partitioning: SignalType enum members, value type variants
- Error Guessing: Mutation of frozen dataclass, missing fields
"""

import warnings

import pytest

from lumehaven.core.signal import (
    NULL_VALUE,
    UNDEFINED_VALUE,
    Signal,
    SignalType,
    is_undefined,
)


class TestSignalType:
    """Specification-based tests for SignalType StrEnum (ADR-010)."""

    def test_all_members_present(self) -> None:
        """SignalType has exactly five members per ADR-010."""
        expected = {"STRING", "NUMBER", "BOOLEAN", "ENUM", "DATETIME"}
        assert set(SignalType.__members__) == expected

    @pytest.mark.parametrize(
        "member,wire_value",
        [
            (SignalType.STRING, "string"),
            (SignalType.NUMBER, "number"),
            (SignalType.BOOLEAN, "boolean"),
            (SignalType.ENUM, "enum"),
            (SignalType.DATETIME, "datetime"),
        ],
        ids=["string", "number", "boolean", "enum", "datetime"],
    )
    def test_str_values(self, member: SignalType, wire_value: str) -> None:
        """SignalType members have lowercase string values for JSON wire format."""
        assert member.value == wire_value
        assert str(member) == wire_value

    def test_construct_from_string(self) -> None:
        """SignalType can be constructed from a wire-format string."""
        assert SignalType("number") == SignalType.NUMBER

    def test_invalid_string_raises_value_error(self) -> None:
        """SignalType rejects unknown type strings."""
        with pytest.raises(ValueError, match="'unknown'"):
            SignalType("unknown")


class TestSignalCreation:
    """Specification-based tests for enriched Signal dataclass creation."""

    def test_create_with_all_fields(self) -> None:
        """Signal can be created with all fields explicitly set."""
        signal = Signal(
            id="oh:LivingRoom_Temp",
            value=21.5,
            display_value="21.5",
            unit="°C",
            label="Living Room Temperature",
            available=True,
            signal_type=SignalType.NUMBER,
        )

        assert signal.id == "oh:LivingRoom_Temp"
        assert signal.value == 21.5
        assert signal.display_value == "21.5"
        assert signal.unit == "°C"
        assert signal.label == "Living Room Temperature"
        assert signal.available is True
        assert signal.signal_type == SignalType.NUMBER

    def test_create_with_required_fields_only(self) -> None:
        """Signal can be created with only id and value; defaults apply."""
        signal = Signal(id="switch_1", value=True)

        assert signal.id == "switch_1"
        assert signal.value is True
        assert signal.unit == ""
        assert signal.label == ""
        assert signal.display_value == ""
        assert signal.available is True
        assert signal.signal_type == SignalType.STRING

    def test_unavailable_signal(self) -> None:
        """Unavailable signal has value=None and available=False."""
        signal = Signal(
            id="oh:Sensor_Offline",
            value=None,
            display_value="",
            available=False,
        )

        assert signal.value is None
        assert signal.available is False
        assert signal.display_value == ""

    @pytest.mark.parametrize(
        "value,expected_type",
        [
            ("hello", str),
            (42, int),
            (21.5, float),
            (True, bool),
            (None, type(None)),
        ],
        ids=["string", "int", "float", "bool", "none"],
    )
    def test_value_type_variants(self, value: object, expected_type: type) -> None:
        """Value field accepts all union members (str|int|float|bool|None).

        Technique: Equivalence Partitioning — one representative per type.
        """
        signal = Signal(id="test", value=value)
        assert isinstance(signal.value, expected_type)

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
    """Round-trip testing for Signal.to_dict() with enriched fields."""

    def test_to_dict_includes_all_fields(self) -> None:
        """to_dict() returns dictionary with all seven enriched fields."""
        signal = Signal(
            id="temp",
            value=21.5,
            display_value="21.5",
            unit="°C",
            label="Temperature",
            available=True,
            signal_type=SignalType.NUMBER,
        )

        result = signal.to_dict()

        assert result == {
            "id": "temp",
            "value": 21.5,
            "display_value": "21.5",
            "unit": "°C",
            "label": "Temperature",
            "available": True,
            "signal_type": "number",
        }

    def test_to_dict_with_defaults(self) -> None:
        """to_dict() includes default values for optional fields."""
        signal = Signal(id="switch", value=True)

        result = signal.to_dict()

        assert result == {
            "id": "switch",
            "value": True,
            "display_value": "",
            "unit": "",
            "label": "",
            "available": True,
            "signal_type": "string",
        }

    def test_to_dict_unavailable_signal(self) -> None:
        """to_dict() serializes unavailable signals with value=None."""
        signal = Signal(
            id="offline",
            value=None,
            display_value="",
            available=False,
        )

        result = signal.to_dict()

        assert result["value"] is None
        assert result["available"] is False
        assert result["display_value"] == ""

    def test_to_dict_signal_type_is_string_value(self) -> None:
        """signal_type serializes as its lowercase string value, not enum name."""
        signal = Signal(id="t", value=1, signal_type=SignalType.NUMBER)

        assert signal.to_dict()["signal_type"] == "number"


class TestSignalFromDict:
    """Decision Table testing for Signal.from_dict().

    | id  | value    | display_value | signal_type | available | Result    |
    |-----|----------|---------------|-------------|-----------|-----------|
    | Yes | numeric  | Yes           | "number"    | Yes       | Success   |
    | Yes | bool     | Yes           | "boolean"   | Yes       | Success   |
    | Yes | None     | Yes           | -           | False     | Success   |
    | Yes | str      | No            | No          | No        | Defaults  |
    | No  | -        | -             | -           | -         | KeyError  |
    | Yes | missing  | -             | -           | -         | KeyError  |
    """

    def test_from_dict_all_fields(self) -> None:
        """from_dict() with all fields creates complete Signal."""
        data = {
            "id": "temp",
            "value": 21.5,
            "display_value": "21.5",
            "unit": "°C",
            "label": "Temperature",
            "available": True,
            "signal_type": "number",
        }

        signal = Signal.from_dict(data)

        assert signal.id == "temp"
        assert signal.value == 21.5
        assert signal.display_value == "21.5"
        assert signal.unit == "°C"
        assert signal.label == "Temperature"
        assert signal.available is True
        assert signal.signal_type == SignalType.NUMBER

    def test_from_dict_required_only(self) -> None:
        """from_dict() with only id and value uses sensible defaults."""
        data = {"id": "switch", "value": True}

        signal = Signal.from_dict(data)

        assert signal.id == "switch"
        assert signal.value is True
        assert signal.display_value == "True"  # auto-generated
        assert signal.unit == ""
        assert signal.label == ""
        assert signal.available is True
        assert signal.signal_type == SignalType.STRING

    def test_from_dict_none_value(self) -> None:
        """from_dict() handles explicit None value (unavailable signal)."""
        data = {"id": "offline", "value": None, "available": False}

        signal = Signal.from_dict(data)

        assert signal.value is None
        assert signal.display_value == ""  # None produces ""
        assert signal.available is False

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

    def test_from_dict_parses_signal_type_string(self) -> None:
        """from_dict() converts signal_type string to SignalType enum."""
        data = {"id": "t", "value": True, "signal_type": "boolean"}

        signal = Signal.from_dict(data)

        assert signal.signal_type == SignalType.BOOLEAN


class TestSignalRoundTrip:
    """Round-trip testing: to_dict() → from_dict() preserves data."""

    @pytest.mark.parametrize(
        "signal",
        [
            Signal(
                id="temp",
                value=21.5,
                display_value="21.5",
                unit="°C",
                label="Temperature",
                signal_type=SignalType.NUMBER,
            ),
            Signal(
                id="switch",
                value=True,
                display_value="An",
                signal_type=SignalType.BOOLEAN,
            ),
            Signal(
                id="power",
                value=1250,
                display_value="1250",
                unit="W",
                label="",
                signal_type=SignalType.NUMBER,
            ),
            Signal(id="offline", value=None, display_value="", available=False),
            Signal(
                id="text",
                value="Eco 40",
                display_value="Eco 40",
                signal_type=SignalType.STRING,
            ),
        ],
        ids=["number", "boolean", "int-number", "unavailable", "string"],
    )
    def test_round_trip_preserves_data(self, signal: Signal) -> None:
        """Converting Signal → dict → Signal yields equal object."""
        reconstructed = Signal.from_dict(signal.to_dict())

        assert reconstructed == signal


class TestIsUndefined:
    """Branch Coverage testing for is_undefined() — now deprecated.

    The function tests: value in (UNDEFINED_VALUE, NULL_VALUE)
    We need both True branches and the False branch.
    """

    @pytest.mark.parametrize(
        "value,expected",
        [
            (UNDEFINED_VALUE, True),
            (NULL_VALUE, True),
            ("ON", False),
            ("21.5", False),
            ("", False),
        ],
        ids=["UNDEF", "NULL", "normal-ON", "normal-numeric", "empty-string"],
    )
    def test_is_undefined(self, value: str, expected: bool) -> None:
        """is_undefined() correctly identifies undefined states."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            assert is_undefined(value) is expected

    def test_emits_deprecation_warning(self) -> None:
        """is_undefined() emits DeprecationWarning per ADR-010.

        Technique: Error Guessing — verifying deprecation contract.
        """
        with pytest.warns(DeprecationWarning, match="ADR-010"):
            is_undefined("ON")


class TestSentinelConstants:
    """Sanity tests for sentinel constant values."""

    def test_undefined_value_constant(self) -> None:
        """UNDEFINED_VALUE matches OpenHAB's undefined state string."""
        assert UNDEFINED_VALUE == "UNDEF"

    def test_null_value_constant(self) -> None:
        """NULL_VALUE matches OpenHAB's null state string."""
        assert NULL_VALUE == "NULL"
