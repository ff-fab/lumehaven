"""Unit tests for adapters/protocol.py — SmartHomeAdapter Protocol interface.

Test Techniques Used:
- Specification-based Testing: Verifying Protocol contract (required methods/properties)
- Structural Subtyping Verification: isinstance() checks with @runtime_checkable
- Error Guessing: Non-compliant classes failing isinstance() checks
- Decision Table: Compliant vs partial vs non-compliant implementations
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from lumehaven.adapters.protocol import SmartHomeAdapter
from lumehaven.core.signal import Signal

# =============================================================================
# Test Implementations (Mock Adapters)
# =============================================================================


class CompliantAdapter:
    """Fully compliant adapter implementing all Protocol requirements."""

    @property
    def name(self) -> str:
        return "test-adapter"

    @property
    def adapter_type(self) -> str:
        return "test"

    @property
    def prefix(self) -> str:
        return "tst"

    async def get_signals(self) -> dict[str, Signal]:
        return {}

    async def get_signal(self, signal_id: str) -> Signal:
        return Signal(id=signal_id, value="test")

    def subscribe_events(self) -> AsyncIterator[Signal]:
        async def _generator() -> AsyncIterator[Signal]:
            yield Signal(id="event", value="test")

        return _generator()

    def is_connected(self) -> bool:
        return True

    async def close(self) -> None:
        pass


class MissingMethodAdapter:
    """Partial implementation — missing close() method.

    Used to verify Protocol compliance detection.
    """

    @property
    def name(self) -> str:
        return "incomplete"

    @property
    def adapter_type(self) -> str:
        return "test"

    @property
    def prefix(self) -> str:
        return "inc"

    async def get_signals(self) -> dict[str, Signal]:
        return {}

    async def get_signal(self, signal_id: str) -> Signal | None:
        return Signal(id=signal_id, value="test")

    def subscribe_events(self) -> AsyncIterator[Signal]:
        async def _generator() -> AsyncIterator[Signal]:
            yield Signal(id="event", value="test")

        return _generator()

    def is_connected(self) -> bool:
        return True

    # Intentionally missing: close()


class MissingPropertyAdapter:
    """Partial implementation — missing prefix property.

    Used to verify Protocol compliance detection for properties.
    """

    @property
    def name(self) -> str:
        return "no-prefix"

    @property
    def adapter_type(self) -> str:
        return "test"

    # Intentionally missing: prefix property

    async def get_signals(self) -> dict[str, Signal]:
        return {}

    async def get_signal(self, signal_id: str) -> Signal | None:
        return Signal(id=signal_id, value="test")

    def subscribe_events(self) -> AsyncIterator[Signal]:
        async def _generator() -> AsyncIterator[Signal]:
            yield Signal(id="event", value="test")

        return _generator()

    def is_connected(self) -> bool:
        return True

    async def close(self) -> None:
        pass


class UnrelatedClass:
    """Completely unrelated class with no adapter methods."""

    def do_something(self) -> str:
        return "not an adapter"


# =============================================================================
# Tests
# =============================================================================


class TestProtocolRuntimeCheckable:
    """Tests verifying @runtime_checkable behavior with isinstance().

    Technique: Structural Subtyping Verification — Protocol's core feature.

    The @runtime_checkable decorator on SmartHomeAdapter enables isinstance()
    checks that verify structural (duck typing) compliance.
    """

    def test_compliant_class_passes_isinstance_check(self) -> None:
        """Class implementing all Protocol members passes isinstance()."""
        adapter = CompliantAdapter()

        assert isinstance(adapter, SmartHomeAdapter)

    def test_missing_method_fails_isinstance_check(self) -> None:
        """Class missing a required method fails isinstance()."""
        adapter = MissingMethodAdapter()

        assert not isinstance(adapter, SmartHomeAdapter)

    def test_missing_property_fails_isinstance_check(self) -> None:
        """Class missing a required property fails isinstance()."""
        adapter = MissingPropertyAdapter()

        assert not isinstance(adapter, SmartHomeAdapter)

    def test_unrelated_class_fails_isinstance_check(self) -> None:
        """Completely unrelated class fails isinstance()."""
        obj = UnrelatedClass()

        assert not isinstance(obj, SmartHomeAdapter)

    def test_none_fails_isinstance_check(self) -> None:
        """None is not a SmartHomeAdapter."""
        assert not isinstance(None, SmartHomeAdapter)


class TestProtocolProperties:
    """Tests verifying Protocol property specifications.

    Technique: Specification-based Testing — verifying property contracts.
    """

    def test_name_property_returns_string(self) -> None:
        """name property returns adapter identifier as string."""
        adapter = CompliantAdapter()

        result = adapter.name

        assert result == "test-adapter"
        assert isinstance(result, str)

    def test_adapter_type_property_returns_string(self) -> None:
        """adapter_type property returns system type as string."""
        adapter = CompliantAdapter()

        result = adapter.adapter_type

        assert result == "test"
        assert isinstance(result, str)

    def test_prefix_property_returns_string(self) -> None:
        """prefix property returns signal ID prefix as string."""
        adapter = CompliantAdapter()

        result = adapter.prefix

        assert result == "tst"
        assert isinstance(result, str)


class TestProtocolAsyncMethods:
    """Tests verifying Protocol async method signatures.

    Technique: Specification-based Testing — verifying async method contracts.
    """

    async def test_get_signals_returns_signal_dict(self) -> None:
        """get_signals() returns dictionary mapping IDs to Signals."""
        adapter = CompliantAdapter()

        result = await adapter.get_signals()

        assert isinstance(result, dict)

    async def test_get_signal_returns_signal(self) -> None:
        """get_signal() returns Signal for given ID."""
        adapter = CompliantAdapter()

        result = await adapter.get_signal("test:id")

        assert isinstance(result, Signal)
        assert result.id == "test:id"

    async def test_close_is_awaitable(self) -> None:
        """close() is an awaitable coroutine."""
        adapter = CompliantAdapter()

        # Should complete without error
        await adapter.close()


class TestProtocolSyncMethods:
    """Tests verifying Protocol synchronous method signatures.

    Technique: Specification-based Testing — verifying sync method contracts.
    """

    def test_is_connected_returns_bool(self) -> None:
        """is_connected() returns boolean connection status."""
        adapter = CompliantAdapter()

        result = adapter.is_connected()

        assert result is True
        assert isinstance(result, bool)

    def test_subscribe_events_returns_async_iterator(self) -> None:
        """subscribe_events() returns AsyncIterator[Signal]."""
        adapter = CompliantAdapter()

        result = adapter.subscribe_events()

        assert isinstance(result, AsyncIterator)


class TestProtocolEventSubscription:
    """Tests verifying subscribe_events() async iteration.

    Technique: Specification-based Testing — verifying async generator contract.
    """

    async def test_subscribe_events_yields_signals(self) -> None:
        """subscribe_events() yields Signal objects when iterated."""
        adapter = CompliantAdapter()

        signals: list[Signal] = []
        async for signal in adapter.subscribe_events():
            signals.append(signal)

        assert len(signals) == 1
        assert isinstance(signals[0], Signal)
        assert signals[0].id == "event"


class TestProtocolTypeChecking:
    """Tests verifying Protocol works with type checkers.

    Technique: Specification-based Testing — type annotation verification.

    Note: These tests verify runtime behavior. Static type checking
    (pyright/mypy) validates the type annotations at development time.
    """

    def test_protocol_can_be_used_as_type_hint(self) -> None:
        """SmartHomeAdapter can be used as function parameter type."""

        def process_adapter(adapter: SmartHomeAdapter) -> str:
            return adapter.name

        compliant = CompliantAdapter()
        result = process_adapter(compliant)

        assert result == "test-adapter"

    def test_protocol_in_collection_type(self) -> None:
        """SmartHomeAdapter can be used in collection type hints."""
        adapters: list[SmartHomeAdapter] = [CompliantAdapter()]

        assert len(adapters) == 1
        assert isinstance(adapters[0], SmartHomeAdapter)
