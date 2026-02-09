"""Unit tests for signal-related routes.

Test Techniques Used:
- Specification-based Testing: Endpoint contracts, response models
- Round-trip Testing: SignalResponse.from_signal() preserves data
- Error Guessing: 404 for missing signals

Coverage Target: Medium Risk (api/routes.py)
- Line Coverage: ≥80%
- Branch Coverage: ≥75%
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from lumehaven.api.routes import SignalResponse, SignalsResponse
from lumehaven.core.signal import SignalType
from lumehaven.state.store import SignalStore
from tests.fixtures.signals import (
    ALL_TEST_SIGNALS,
    TEMPERATURE_SIGNALS,
    create_signal,
)


class TestListSignals:
    """Tests for GET /api/signals endpoint.

    Technique: Specification-based Testing — verifying endpoint contract.
    """

    async def test_returns_empty_list_when_no_signals(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Returns empty signals list for fresh store."""
        # Act
        response = await async_client.get("/api/signals")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["signals"] == []
        assert data["count"] == 0

    async def test_returns_all_signals(
        self,
        async_client: AsyncClient,
        signal_store: SignalStore,
    ) -> None:
        """Returns all signals currently in store."""
        # Arrange — add signals
        for signal in TEMPERATURE_SIGNALS:
            await signal_store.set(signal)

        # Act
        response = await async_client.get("/api/signals")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["signals"]) == len(TEMPERATURE_SIGNALS)

        # Verify signal IDs match
        returned_ids = {s["id"] for s in data["signals"]}
        expected_ids = {s.id for s in TEMPERATURE_SIGNALS}
        assert returned_ids == expected_ids

    async def test_count_matches_signals_length(
        self,
        async_client: AsyncClient,
        signal_store: SignalStore,
    ) -> None:
        """Response count field matches actual signals length."""
        # Arrange
        for signal in ALL_TEST_SIGNALS:
            await signal_store.set(signal)

        # Act
        response = await async_client.get("/api/signals")

        # Assert
        data = response.json()
        assert data["count"] == len(data["signals"])
        assert data["count"] == len(ALL_TEST_SIGNALS)

    async def test_signal_response_includes_all_fields(
        self,
        async_client: AsyncClient,
        signal_store: SignalStore,
    ) -> None:
        """Each signal in response includes all enriched fields (ADR-010)."""
        # Arrange
        signal = create_signal(
            id="test:temp",
            value=21.5,
            display_value="21.5",
            unit="°C",
            label="Temperature",
            signal_type=SignalType.NUMBER,
        )
        await signal_store.set(signal)

        # Act
        response = await async_client.get("/api/signals")

        # Assert
        data = response.json()
        sig = data["signals"][0]
        assert sig["id"] == "test:temp"
        assert sig["value"] == 21.5
        assert sig["display_value"] == "21.5"
        assert sig["unit"] == "°C"
        assert sig["label"] == "Temperature"
        assert sig["available"] is True
        assert sig["signal_type"] == "number"


class TestGetSignal:
    """Tests for GET /api/signals/{signal_id} endpoint.

    Technique: Specification-based Testing + Error Guessing
    """

    async def test_returns_existing_signal(
        self,
        async_client: AsyncClient,
        signal_store: SignalStore,
    ) -> None:
        """Returns signal data for existing signal_id."""
        # Arrange
        signal = create_signal(
            id="oh:LivingRoom_Temp",
            value=21.5,
            display_value="21.5",
            unit="°C",
            label="Living Room Temperature",
            signal_type=SignalType.NUMBER,
        )
        await signal_store.set(signal)

        # Act
        response = await async_client.get("/api/signals/oh:LivingRoom_Temp")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "oh:LivingRoom_Temp"
        assert data["value"] == 21.5
        assert data["display_value"] == "21.5"
        assert data["unit"] == "°C"
        assert data["label"] == "Living Room Temperature"
        assert data["available"] is True
        assert data["signal_type"] == "number"

    async def test_returns_404_for_missing_signal(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Returns 404 with detail message for non-existent signal_id.

        Technique: Error Guessing — common failure mode.
        """
        # Act
        response = await async_client.get("/api/signals/nonexistent:signal")

        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "Signal not found" in data["detail"]
        assert "nonexistent:signal" in data["detail"]

    async def test_handles_special_characters_in_signal_id(
        self,
        async_client: AsyncClient,
        signal_store: SignalStore,
    ) -> None:
        """Handles signal IDs with colons and underscores.

        Technique: Error Guessing — URL path parameter edge case.
        """
        # Arrange
        signal = create_signal(
            id="oh:Floor_1_Room_2_Temp",
            value=20.0,
            display_value="20.0",
            unit="°C",
            label="F1R2 Temp",
            signal_type=SignalType.NUMBER,
        )
        await signal_store.set(signal)

        # Act
        response = await async_client.get("/api/signals/oh:Floor_1_Room_2_Temp")

        # Assert
        assert response.status_code == 200
        assert response.json()["id"] == "oh:Floor_1_Room_2_Temp"


class TestSignalResponseModel:
    """Tests for SignalResponse Pydantic model.

    Technique: Round-trip Testing — from_signal() preserves all data.
    """

    def test_from_signal_preserves_all_fields(self) -> None:
        """SignalResponse.from_signal() creates response with all enriched fields."""
        # Arrange
        signal = create_signal(
            id="test:id",
            value=42,
            display_value="42",
            unit="kWh",
            label="Energy Consumption",
            signal_type=SignalType.NUMBER,
        )

        # Act
        response = SignalResponse.from_signal(signal)

        # Assert
        assert response.id == signal.id
        assert response.value == signal.value
        assert response.display_value == signal.display_value
        assert response.unit == signal.unit
        assert response.label == signal.label
        assert response.available == signal.available
        assert response.signal_type == signal.signal_type

    def test_from_signal_handles_empty_strings(self) -> None:
        """from_signal() handles empty unit and label correctly."""
        # Arrange
        signal = create_signal(id="test:switch", value="ON", unit="", label="")

        # Act
        response = SignalResponse.from_signal(signal)

        # Assert
        assert response.unit == ""
        assert response.label == ""


class TestSignalsResponseModel:
    """Tests for SignalsResponse Pydantic model.

    Technique: Specification-based Testing — model validation.
    """

    def test_validates_count_matches_signals_length(self) -> None:
        """SignalsResponse raises if count doesn't match signals length."""
        # Arrange
        signals = [
            SignalResponse(
                id="1",
                value="a",
                display_value="a",
                unit="",
                label="",
                available=True,
                signal_type=SignalType.STRING,
            ),
            SignalResponse(
                id="2",
                value="b",
                display_value="b",
                unit="",
                label="",
                available=True,
                signal_type=SignalType.STRING,
            ),
        ]

        # Act & Assert — count matches (should pass)
        response = SignalsResponse(signals=signals, count=2)
        assert response.count == 2

    def test_raises_on_count_mismatch(self) -> None:
        """SignalsResponse raises ValueError if count mismatches.

        Technique: Error Guessing — incorrect count value.
        """
        # Arrange
        signals = [
            SignalResponse(
                id="1",
                value="a",
                display_value="a",
                unit="",
                label="",
                available=True,
                signal_type=SignalType.STRING,
            ),
        ]

        # Act & Assert
        with pytest.raises(ValueError, match="count.*does not match"):
            SignalsResponse(signals=signals, count=5)  # Wrong count!


class TestMetricsEndpoint:
    """Tests for GET /metrics endpoint.

    Technique: Specification-based Testing — metrics structure.
    """

    async def test_returns_subscriber_metrics(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Metrics includes subscribers.total and subscribers.slow."""
        # Act
        response = await async_client.get("/metrics")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "subscribers" in data
        assert "total" in data["subscribers"]
        assert "slow" in data["subscribers"]

    async def test_returns_signal_metrics(
        self,
        async_client: AsyncClient,
        signal_store: SignalStore,
    ) -> None:
        """Metrics includes signals.stored count."""
        # Arrange — add some signals
        for i in range(5):
            await signal_store.set(create_signal(id=f"test:sig_{i}"))

        # Act
        response = await async_client.get("/metrics")

        # Assert
        data = response.json()
        assert "signals" in data
        assert data["signals"]["stored"] == 5

    async def test_metrics_reflect_current_state(
        self,
        async_client: AsyncClient,
        signal_store: SignalStore,
    ) -> None:
        """Metrics update when store state changes."""
        # Act — initial state
        response1 = await async_client.get("/metrics")
        initial_count = response1.json()["signals"]["stored"]

        # Arrange — add signals
        await signal_store.set(create_signal(id="new:signal"))

        # Act — after change
        response2 = await async_client.get("/metrics")

        # Assert — count increased
        assert response2.json()["signals"]["stored"] == initial_count + 1
