"""Unit tests for core/exceptions.py — Custom exception hierarchy.

Test Techniques Used:
- Structural Verification: Exception inheritance hierarchy
- Specification-based: Constructor contracts and attribute storage
- Condition Coverage: SmartHomeConnectionError with/without cause
"""

import pytest

from lumehaven.core.exceptions import (
    AdapterError,
    LumehavenError,
    SignalNotFoundError,
    SmartHomeConnectionError,
)


class TestExceptionHierarchy:
    """Structural verification of exception inheritance."""

    def test_lumehaven_error_is_exception(self) -> None:
        """LumehavenError inherits from Exception."""
        assert issubclass(LumehavenError, Exception)

    @pytest.mark.parametrize(
        "exception_class",
        [
            SignalNotFoundError,
            SmartHomeConnectionError,
            AdapterError,
        ],
        ids=["SignalNotFoundError", "SmartHomeConnectionError", "AdapterError"],
    )
    def test_all_exceptions_inherit_from_lumehaven_error(
        self, exception_class: type
    ) -> None:
        """All custom exceptions inherit from LumehavenError.

        This enables catching all lumehaven errors with a single except clause.
        """
        assert issubclass(exception_class, LumehavenError)


class TestLumehavenError:
    """Specification-based tests for base LumehavenError."""

    def test_can_be_raised_and_caught(self) -> None:
        """LumehavenError can be raised with a message."""
        with pytest.raises(LumehavenError, match="test error"):
            raise LumehavenError("test error")

    def test_can_catch_derived_exceptions(self) -> None:
        """Catching LumehavenError also catches derived exceptions."""
        with pytest.raises(LumehavenError):
            raise SignalNotFoundError("test_signal")


class TestSignalNotFoundError:
    """Specification-based tests for SignalNotFoundError."""

    def test_stores_signal_id(self) -> None:
        """SignalNotFoundError stores the signal_id attribute."""
        error = SignalNotFoundError("living_room_temp")

        assert error.signal_id == "living_room_temp"

    def test_message_format(self) -> None:
        """SignalNotFoundError generates correct message format."""
        error = SignalNotFoundError("living_room_temp")

        assert str(error) == "Signal not found: living_room_temp"

    def test_can_be_raised_and_matched(self) -> None:
        """SignalNotFoundError can be raised and pattern-matched."""
        with pytest.raises(SignalNotFoundError, match="living_room_temp"):
            raise SignalNotFoundError("living_room_temp")


class TestSmartHomeConnectionError:
    """Condition Coverage tests for SmartHomeConnectionError.

    The constructor has a branch: if cause: message += f": {cause}"
    We test both branches.
    """

    def test_stores_all_attributes(self) -> None:
        """SmartHomeConnectionError stores system, url, and cause."""
        cause = ConnectionError("Connection refused")
        error = SmartHomeConnectionError(
            system="openhab",
            url="http://localhost:8080",
            cause=cause,
        )

        assert error.system == "openhab"
        assert error.url == "http://localhost:8080"
        assert error.cause is cause

    def test_message_without_cause(self) -> None:
        """Message format when no cause is provided (false branch)."""
        error = SmartHomeConnectionError(
            system="openhab",
            url="http://localhost:8080",
        )

        assert str(error) == "Failed to connect to openhab at http://localhost:8080"
        assert error.cause is None

    def test_message_with_cause(self) -> None:
        """Message format when cause is provided (true branch)."""
        cause = TimeoutError("Connection timed out")
        error = SmartHomeConnectionError(
            system="homeassistant",
            url="http://ha.local:8123",
            cause=cause,
        )

        expected = (
            "Failed to connect to homeassistant at http://ha.local:8123: "
            "Connection timed out"
        )
        assert str(error) == expected

    def test_cause_defaults_to_none(self) -> None:
        """cause parameter defaults to None when not provided."""
        error = SmartHomeConnectionError(system="openhab", url="http://localhost:8080")

        assert error.cause is None


class TestAdapterError:
    """Specification-based tests for AdapterError."""

    def test_stores_adapter_attribute(self) -> None:
        """AdapterError stores the adapter type."""
        error = AdapterError(adapter="openhab", message="Failed to parse item")

        assert error.adapter == "openhab"

    def test_message_format_with_prefix(self) -> None:
        """AdapterError message includes adapter prefix in brackets."""
        error = AdapterError(adapter="openhab", message="Invalid item state")

        assert str(error) == "[openhab] Invalid item state"

    def test_can_be_raised_and_matched(self) -> None:
        """AdapterError can be raised and pattern-matched."""
        with pytest.raises(AdapterError, match=r"\[openhab\] test"):
            raise AdapterError(adapter="openhab", message="test")
