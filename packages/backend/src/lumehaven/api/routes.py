"""FastAPI route definitions.

Defines the REST API and SSE endpoints for the lumehaven backend.
"""

import logging
from typing import Annotated, Literal, Self

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, model_validator

from lumehaven.core.signal import Signal, SignalType, SignalValue
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
    """API response model for a single signal (ADR-010 enriched)."""

    id: str
    value: SignalValue
    display_value: str
    unit: str
    label: str
    available: bool
    signal_type: SignalType

    @classmethod
    def from_signal(cls, signal: Signal) -> Self:
        """Create from domain Signal."""
        return cls(
            id=signal.id,
            value=signal.value,
            display_value=signal.display_value,
            unit=signal.unit,
            label=signal.label,
            available=signal.available,
            signal_type=signal.signal_type,
        )


class CommandRequest(BaseModel):
    """API request model for sending a command to a signal (ADR-011).

    Commands are always string values matching the platform's native
    command format.  The adapter translates as needed.

    The endpoint ``POST /api/signals/{signal_id}/command`` accepts this
    body and returns 202 Accepted (the actual state change arrives
    asynchronously via SSE).

    Example:
        >>> CommandRequest(value="ON").model_dump()
        {'value': 'ON'}
    """

    value: str


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


class MetricsResponse(BaseModel):
    """API response for internal metrics.

    Structured metrics for monitoring dashboards and debugging.
    Future: May be replaced with Prometheus-format /metrics endpoint.
    """

    subscribers: dict[str, int]
    signals: dict[str, int]


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

    # Get adapter manager from app state
    adapter_manager = getattr(request.app.state, "adapter_manager", None)

    # Build adapter status list
    adapter_statuses: list[AdapterStatus] = []
    all_connected = True

    if adapter_manager is not None:
        for state in adapter_manager.states.values():
            adapter = state.adapter
            connected = state.connected
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


@router.get("/metrics", response_model=MetricsResponse, tags=["system"])
async def metrics(
    store: Annotated[SignalStore, Depends(get_signal_store)],
) -> MetricsResponse:
    """Internal metrics for monitoring.

    Returns store metrics useful for dashboards and debugging:
    - subscribers.total: Number of active SSE subscribers
    - subscribers.slow: Subscribers experiencing backpressure (dropped messages)
    - signals.stored: Number of signals in the store

    Note: This returns JSON. For Prometheus scraping, a future endpoint
    will provide metrics in Prometheus text format.
    """
    store_metrics = store.get_metrics()
    return MetricsResponse(
        subscribers=store_metrics["subscribers"],
        signals=store_metrics["signals"],
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
