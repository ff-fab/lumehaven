"""Unit tests for AdapterManager registration and properties.

Test Techniques Used:
- Specification-based Testing: Public API contracts for add() and properties
- State-based Testing: Filtering by connection state
- Error Guessing: Duplicate adapter names

Coverage Target: Critical Risk (adapters/manager.py)
- Line Coverage: ≥90%
- Branch Coverage: ≥85%
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest

from lumehaven.adapters.manager import AdapterManager

if TYPE_CHECKING:
    from tests.unit.adapters.conftest import MockAdapter


class TestAdapterRegistration:
    """Tests for adapter registration via add() method.

    Technique: Specification-based testing — verifying public API contracts.
    """

    def test_add_single_adapter_succeeds(
        self,
        adapter_manager: AdapterManager,
        mock_adapter: MockAdapter,
    ) -> None:
        """Single adapter registration populates states dict."""
        # Arrange — manager starts empty
        assert len(adapter_manager.states) == 0

        # Act
        adapter_manager.add(mock_adapter)

        # Assert
        assert len(adapter_manager.states) == 1
        assert mock_adapter.name in adapter_manager.states
        state = adapter_manager.states[mock_adapter.name]
        assert state.adapter is mock_adapter
        assert state.connected is False
        assert state.error is None

    def test_add_multiple_adapters_succeeds(
        self,
        adapter_manager: AdapterManager,
        mock_adapter_factory: Callable[..., MockAdapter],
    ) -> None:
        """Multiple adapters with unique names register correctly."""
        # Arrange
        adapter1 = mock_adapter_factory(_name="adapter-1")
        adapter2 = mock_adapter_factory(_name="adapter-2")
        adapter3 = mock_adapter_factory(_name="adapter-3")

        # Act
        adapter_manager.add(adapter1)
        adapter_manager.add(adapter2)
        adapter_manager.add(adapter3)

        # Assert
        assert len(adapter_manager.states) == 3
        assert set(adapter_manager.states.keys()) == {
            "adapter-1",
            "adapter-2",
            "adapter-3",
        }

    def test_add_duplicate_name_raises_value_error(
        self,
        adapter_manager: AdapterManager,
        mock_adapter_factory: Callable[..., MockAdapter],
    ) -> None:
        """Duplicate adapter name raises ValueError with helpful message.

        Technique: Error Guessing — anticipating configuration mistakes.
        """
        # Arrange
        adapter1 = mock_adapter_factory(_name="duplicate-name")
        adapter2 = mock_adapter_factory(_name="duplicate-name")
        adapter_manager.add(adapter1)

        # Act & Assert
        with pytest.raises(ValueError, match="Duplicate adapter name"):
            adapter_manager.add(adapter2)

    def test_adapters_property_returns_all_registered(
        self,
        adapter_manager: AdapterManager,
        mock_adapter_factory: Callable[..., MockAdapter],
    ) -> None:
        """adapters property returns list of all registered adapters."""
        # Arrange
        adapters = [mock_adapter_factory(_name=f"adapter-{i}") for i in range(3)]
        for adapter in adapters:
            adapter_manager.add(adapter)

        # Act
        result = adapter_manager.adapters

        # Assert
        assert len(result) == 3
        assert set(result) == set(adapters)

    def test_adapters_property_returns_empty_list_when_none_registered(
        self,
        adapter_manager: AdapterManager,
    ) -> None:
        """adapters property returns empty list for fresh manager."""
        assert adapter_manager.adapters == []


class TestConnectedAdaptersProperty:
    """Tests for connected_adapters property filtering.

    Technique: State-based testing — filtering by connection state.
    """

    def test_connected_adapters_returns_only_connected(
        self,
        adapter_manager: AdapterManager,
        mock_adapter_factory: Callable[..., MockAdapter],
    ) -> None:
        """connected_adapters filters to adapters with connected=True."""
        # Arrange — create adapters and manipulate state directly
        connected = mock_adapter_factory(_name="connected-1")
        disconnected = mock_adapter_factory(_name="disconnected-1")

        adapter_manager.add(connected)
        adapter_manager.add(disconnected)

        # Manually set connection states for test
        adapter_manager.states["connected-1"].connected = True
        adapter_manager.states["disconnected-1"].connected = False

        # Act
        result = adapter_manager.connected_adapters

        # Assert
        assert len(result) == 1
        assert result[0] is connected

    def test_connected_adapters_empty_when_none_connected(
        self,
        adapter_manager: AdapterManager,
        mock_adapter: MockAdapter,
    ) -> None:
        """connected_adapters returns empty list when all disconnected."""
        # Arrange
        adapter_manager.add(mock_adapter)
        # Default state is disconnected

        # Act & Assert
        assert adapter_manager.connected_adapters == []
