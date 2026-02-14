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
            SmartHomeConnectionError,
            AdapterError,
            SignalNotFoundError,
        ],
        ids=["SmartHomeConnectionError", "AdapterError", "SignalNotFoundError"],
    )
    def test_all_exceptions_inherit_from_lumehaven_error(
        self, exception_class: type
    ) -> None:
        """All custom exceptions inherit from LumehavenError."""
        assert issubclass(exception_class, LumehavenError)


class TestLumehavenError:
    """Specification-based tests for base LumehavenError."""

    def test_can_be_raised_and_caught(self) -> None:
        """LumehavenError can be raised with a message."""
        with pytest.raises(LumehavenError, match="test error"):
            raise LumehavenError("test error")


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


class TestSignalNotFoundError:
    """Specification-based tests for SignalNotFoundError (ADR-011)."""

    def test_stores_signal_id(self) -> None:
        """SignalNotFoundError stores the signal_id."""
        error = SignalNotFoundError(signal_id="oh:NonExistent")

        assert error.signal_id == "oh:NonExistent"

    def test_message_format(self) -> None:
        """SignalNotFoundError message includes signal_id."""
        error = SignalNotFoundError(signal_id="oh:Missing_Light")

        assert str(error) == "Signal not found: oh:Missing_Light"

    def test_inherits_from_lumehaven_error(self) -> None:
        """SignalNotFoundError inherits from LumehavenError."""
        error = SignalNotFoundError(signal_id="test")

        assert isinstance(error, LumehavenError)
