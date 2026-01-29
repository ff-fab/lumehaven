"""Server-Sent Events (SSE) endpoint for real-time signal updates.

This module provides the SSE streaming endpoint that the frontend
uses to receive real-time updates. It bridges the signal store's
pub/sub mechanism with HTTP SSE.
"""

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from lumehaven.state.store import SignalStore, get_signal_store

logger = logging.getLogger(__name__)

router = APIRouter()

# Heartbeat interval in seconds (keeps connection alive through proxies)
HEARTBEAT_INTERVAL = 30


async def signal_event_generator(
    store: SignalStore,
) -> AsyncGenerator[dict[str, str]]:
    """Generate SSE events from signal store updates.

    Yields:
        Dict with 'event' and 'data' keys for SSE protocol.
    """
    subscriber = store.subscribe()
    try:
        async for signal in subscriber:
            yield {
                "event": "signal",
                "data": json.dumps(signal.to_dict(), ensure_ascii=False),
            }
    except asyncio.CancelledError:
        logger.debug("SSE connection cancelled")
        raise
    finally:
        logger.debug("SSE subscriber cleaned up")


@router.get("/api/events/signals", tags=["signals"])
async def signal_stream(
    store: Annotated[SignalStore, Depends(get_signal_store)],
) -> EventSourceResponse:
    """Server-Sent Events stream for real-time signal updates.

    Clients receive 'signal' events whenever a signal value changes.
    Events are JSON-encoded Signal objects.

    Example event:
        event: signal
        data: {"id": "temp_sensor", "value": "21.5", "unit": "°C", "label": "Temperature"}

    Returns:
        SSE response that streams until client disconnects.
    """
    return EventSourceResponse(
        signal_event_generator(store),
        media_type="text/event-stream",
    )
