"""FastAPI route definitions.

Defines the REST API and SSE endpoints for the lumehaven backend.
"""

import logging
from typing import Annotated, Literal, Self

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, model_validator

from lumehaven.adapters.protocol import SmartHomeAdapter
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
    def from_signal(cls, signal: Signal) -> Self:
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

    @model_validator(mode="after")
    def validate_count_matches_signals(self) -> Self:
        """Ensure count matches the actual number of signals."""
        if self.count != len(self.signals):
            raise ValueError(
                f"count ({self.count}) does not match "
                f"len(signals) ({len(self.signals)})"
            )
        return self


class AdapterStatus(BaseModel):
    """Status of a single smart home adapter."""

    name: str
    type: str
    connected: bool


class HealthResponse(BaseModel):
    """API response for health check."""

    status: Literal["healthy", "degraded"]
    signal_count: int
    subscriber_count: int
    adapters: list[AdapterStatus]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check(
    request: Request,
    store: Annotated[SignalStore, Depends(get_signal_store)],
) -> HealthResponse:
    """Health check endpoint.

    Returns service status and basic metrics.

    Status is "healthy" when signals are loaded and all adapters are connected.
    Status is "degraded" when signal_count is 0 or any adapter is disconnected.
    """
    signals = await store.get_all()
    signal_count = len(signals)

    # Get adapters from app state (supports single adapter or list)
    adapters_raw = getattr(request.app.state, "adapters", None)
    if adapters_raw is None:
        # Backwards compatibility: check for single adapter
        single_adapter = getattr(request.app.state, "adapter", None)
        adapters_raw = [single_adapter] if single_adapter else []

    # Build adapter status list
    adapter_statuses: list[AdapterStatus] = []
    all_connected = True
    for adapter in adapters_raw:
        if not isinstance(adapter, SmartHomeAdapter):
            continue
        connected = adapter.is_connected()
        if not connected:
            all_connected = False
        adapter_statuses.append(
            AdapterStatus(
                name=adapter.name,
                type=adapter.adapter_type,
                connected=connected,
            )
        )

    # Determine health status
    has_adapters = len(adapter_statuses) > 0
    is_healthy = signal_count > 0 and has_adapters and all_connected

    return HealthResponse(
        status="healthy" if is_healthy else "degraded",
        signal_count=signal_count,
        subscriber_count=store.subscriber_count(),
        adapters=adapter_statuses,
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
