"""FastAPI route definitions.

Defines the REST API and SSE endpoints for the lumehaven backend.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from lumehaven.core.signal import Signal
from lumehaven.state.store import SignalStore, get_signal_store

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Type aliases for dependency injection
# ---------------------------------------------------------------------------

# Note: Using function signature directly instead of TypeAlias
# to avoid "Variable not allowed in type expression" errors


# ---------------------------------------------------------------------------
# Pydantic models for API responses
# ---------------------------------------------------------------------------


class SignalResponse(BaseModel):
    """API response model for a single signal."""

    id: str
    value: str
    unit: str
    label: str

    @classmethod
    def from_signal(cls, signal: Signal) -> "SignalResponse":
        """Create from domain Signal."""
        return cls(
            id=signal.id,
            value=signal.value,
            unit=signal.unit,
            label=signal.label,
        )


class SignalsResponse(BaseModel):
    """API response model for multiple signals."""

    signals: list[SignalResponse]
    count: int


class HealthResponse(BaseModel):
    """API response for health check."""

    status: str
    signal_count: int
    subscriber_count: int


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check(
    store: Annotated[SignalStore, Depends(get_signal_store)],
) -> HealthResponse:
    """Health check endpoint.

    Returns service status and basic metrics.
    """
    signals = await store.get_all()
    return HealthResponse(
        status="healthy",
        signal_count=len(signals),
        subscriber_count=store.subscriber_count(),
    )


@router.get("/api/signals", response_model=SignalsResponse, tags=["signals"])
async def list_signals(
    store: Annotated[SignalStore, Depends(get_signal_store)],
) -> SignalsResponse:
    """Get all signals.

    Returns all currently known signals with their latest values.
    """
    signals = await store.get_all()
    return SignalsResponse(
        signals=[SignalResponse.from_signal(s) for s in signals.values()],
        count=len(signals),
    )


@router.get(
    "/api/signals/{signal_id}",
    response_model=SignalResponse,
    tags=["signals"],
    responses={404: {"description": "Signal not found"}},
)
async def get_signal(
    signal_id: str,
    store: Annotated[SignalStore, Depends(get_signal_store)],
) -> SignalResponse:
    """Get a specific signal by ID.

    Args:
        signal_id: The unique identifier of the signal.

    Returns:
        The signal data.

    Raises:
        404: If the signal doesn't exist.
    """
    signal = await store.get(signal_id)
    if signal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Signal not found: {signal_id}",
        )
    return SignalResponse.from_signal(signal)
