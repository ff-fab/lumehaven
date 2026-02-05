"""Mock OpenHAB server for integration testing.

Implements a minimal OpenHAB REST API that serves fixture data for
integration tests. Uses FastAPI for consistency with the main application.

Endpoints:
- GET /rest/items - List all items
- GET /rest/items/{name} - Get single item
- GET /rest/events/states - SSE stream for state subscriptions (batch updates)
- GET /rest/events - SSE stream for individual events

The server is designed to be started/stopped by Robot Framework test suites.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from tests.fixtures.openhab_responses import ALL_ITEMS

logger = logging.getLogger(__name__)


# =============================================================================
# Server State (mutable for test scenarios)
# =============================================================================


class MockOpenHABState:
    """Mutable state for the mock server.

    Allows tests to configure items, trigger SSE events, and simulate failures.
    """

    def __init__(self) -> None:
        """Initialize with default fixture data."""
        self.reset()

    def reset(self) -> None:
        """Reset to default fixture state."""
        # Deep copy items to allow modifications
        self._items: dict[str, dict[str, Any]] = {
            item["name"]: dict(item) for item in ALL_ITEMS
        }
        self._sse_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._should_fail: bool = False
        self._fail_status: int = 500
        self._fail_message: str = "Internal Server Error"
        self._connection_delay: float = 0.0
        self._return_malformed: bool = False

    @property
    def items(self) -> dict[str, dict[str, Any]]:
        """Get all items by name."""
        return self._items

    def get_item(self, name: str) -> dict[str, Any] | None:
        """Get a single item by name."""
        return self._items.get(name)

    def set_item_state(self, name: str, state: str) -> None:
        """Update an item's state (triggers SSE event)."""
        if name in self._items:
            self._items[name]["state"] = state

    def add_item(self, item: dict[str, Any]) -> None:
        """Add or replace an item."""
        self._items[item["name"]] = item

    def remove_item(self, name: str) -> None:
        """Remove an item."""
        self._items.pop(name, None)

    async def publish_sse_event(self, event: dict[str, Any]) -> None:
        """Queue an SSE event to be sent to subscribers."""
        await self._sse_queue.put(event)

    async def get_sse_event(self) -> dict[str, Any]:
        """Get the next queued SSE event (blocks until available)."""
        return await self._sse_queue.get()

    def configure_failure(
        self, status: int = 500, message: str = "Internal Server Error"
    ) -> None:
        """Configure the server to return errors."""
        self._should_fail = True
        self._fail_status = status
        self._fail_message = message

    def clear_failure(self) -> None:
        """Clear any configured failure state."""
        self._should_fail = False
        self._return_malformed = False

    @property
    def should_fail(self) -> bool:
        """Check if server should return errors."""
        return self._should_fail

    @property
    def return_malformed(self) -> bool:
        """Check if server should return malformed responses."""
        return self._return_malformed

    def set_malformed(self, malformed: bool) -> None:
        """Configure whether to return malformed JSON responses."""
        self._return_malformed = malformed

    @property
    def fail_status(self) -> int:
        """Get configured failure status code."""
        return self._fail_status

    @property
    def fail_message(self) -> str:
        """Get configured failure message."""
        return self._fail_message

    def set_connection_delay(self, delay: float) -> None:
        """Set delay before responding (simulates slow connections)."""
        self._connection_delay = delay

    @property
    def connection_delay(self) -> float:
        """Get configured connection delay."""
        return self._connection_delay


# Global state instance (reset per test suite)
mock_state = MockOpenHABState()


# =============================================================================
# FastAPI Application
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Reset state on startup."""
    mock_state.reset()
    logger.info("Mock OpenHAB server started")
    yield
    logger.info("Mock OpenHAB server stopped")


app = FastAPI(
    title="Mock OpenHAB Server",
    description="Integration test mock for OpenHAB REST API",
    lifespan=lifespan,
)


# =============================================================================
# REST Endpoints
# =============================================================================


@app.get("/rest/")
async def get_rest_root() -> JSONResponse:
    """Return OpenHAB REST API root response (used for connectivity check)."""
    if mock_state.should_fail:
        raise HTTPException(
            status_code=mock_state.fail_status, detail=mock_state.fail_message
        )
    # Minimal response matching OpenHAB's /rest/ endpoint
    return JSONResponse(
        content={
            "version": "4",
            "locale": "en_US",
            "measurementSystem": "SI",
            "runtimeInfo": {
                "version": "4.0.0",
                "buildString": "Mock OpenHAB for testing",
            },
            "links": [
                {
                    "type": "items",
                    "url": "http://localhost:8081/rest/items",
                }
            ],
        }
    )


@app.get("/rest/items")
async def get_items(
    tags: str | None = Query(None, description="Filter by tag"),
) -> JSONResponse:
    """Return all items, optionally filtered by tag."""
    if mock_state.should_fail:
        raise HTTPException(
            status_code=mock_state.fail_status, detail=mock_state.fail_message
        )

    if mock_state.connection_delay > 0:
        await asyncio.sleep(mock_state.connection_delay)

    if mock_state.return_malformed:
        # Return invalid JSON (not a list)
        return JSONResponse(content={"invalid": "not a list", "missing": None})

    items = list(mock_state.items.values())

    # Filter by tag if specified (e.g., ?tags=Dashboard)
    if tags:
        tag_list = tags.split(",")
        items = [
            item
            for item in items
            if any(tag in item.get("tags", []) for tag in tag_list)
        ]

    return JSONResponse(content=items)


@app.get("/rest/items/{item_name}")
async def get_item(item_name: str) -> JSONResponse:
    """Return a single item by name."""
    if mock_state.should_fail:
        raise HTTPException(
            status_code=mock_state.fail_status, detail=mock_state.fail_message
        )

    if mock_state.connection_delay > 0:
        await asyncio.sleep(mock_state.connection_delay)

    item = mock_state.get_item(item_name)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Item '{item_name}' not found")

    return JSONResponse(content=item)


# =============================================================================
# SSE Endpoints
# =============================================================================


@app.get("/rest/events/states")
async def sse_state_subscription(
    request: Request,
    items: str | None = Query(None, description="Comma-separated item names"),
) -> EventSourceResponse:
    """SSE endpoint for batch state subscriptions.

    This is the main SSE endpoint used by OpenHABAdapter.
    Returns a connection ID event, then streams state updates.
    """
    if mock_state.should_fail:
        raise HTTPException(
            status_code=mock_state.fail_status, detail=mock_state.fail_message
        )

    async def event_generator() -> AsyncIterator[dict[str, str]]:
        # Send connection ID (OpenHAB behavior - just a plain string, not JSON)
        connection_id = "mock-connection-id-12345"
        yield {
            "event": "message",
            "id": "0",
            "data": connection_id,
        }

        # Parse requested items
        requested_items = items.split(",") if items else list(mock_state.items.keys())

        # Send initial state for all requested items as a dict keyed by item name
        # This matches OpenHAB's batch state format:
        # {"item_name": {"state": "...", ...}}
        initial_states: dict[str, dict[str, str]] = {}
        for item_name in requested_items:
            item = mock_state.get_item(item_name)
            if item:
                initial_states[item["name"]] = {
                    "state": item["state"],
                }

        if initial_states:
            yield {
                "event": "message",
                "id": "1",
                "data": json.dumps(initial_states),
            }

        # Stream queued events (from tests)
        event_id = 2
        while True:
            if await request.is_disconnected():
                break

            try:
                # Wait for events with timeout to allow disconnect checks
                event = await asyncio.wait_for(mock_state.get_sse_event(), timeout=0.5)
                data = json.dumps(event) if isinstance(event, (dict, list)) else event
                yield {
                    "event": "message",
                    "id": str(event_id),
                    "data": data,
                }
                event_id += 1
            except TimeoutError:
                # No event, continue checking for disconnect
                continue

    return EventSourceResponse(event_generator())


@app.get("/rest/events")
async def sse_events(request: Request) -> EventSourceResponse:
    """SSE endpoint for individual events (legacy format).

    Returns events in OpenHAB's traditional format with topic/payload/type.
    """
    if mock_state.should_fail:
        raise HTTPException(
            status_code=mock_state.fail_status, detail=mock_state.fail_message
        )

    async def event_generator() -> AsyncIterator[dict[str, str]]:
        while True:
            if await request.is_disconnected():
                break

            try:
                event = await asyncio.wait_for(mock_state.get_sse_event(), timeout=0.5)
                yield {
                    "event": "message",
                    "data": json.dumps(event),
                }
            except TimeoutError:
                continue

    return EventSourceResponse(event_generator())


@app.post("/rest/events/states/{connection_id}")
async def subscribe_sse_items(
    connection_id: str, items: list[str] | None = None
) -> dict[str, str]:
    """Subscribe to state updates for specific items.

    This endpoint is called by clients after receiving the connection ID
    from the SSE stream to specify which items they want to track.
    """
    # In a real implementation, this would filter the SSE stream to only
    # send updates for the specified items. For mock purposes, we just
    # acknowledge the subscription.
    item_count = len(items) if items else 0
    logger.info(f"SSE subscription for connection {connection_id}: {item_count} items")
    return {"status": "subscribed", "item_count": str(item_count)}


# =============================================================================
# Test Control Endpoints (not part of real OpenHAB API)
# =============================================================================


@app.post("/_test/reset")
async def reset_state() -> dict[str, str]:
    """Reset mock server to default state."""
    mock_state.reset()
    return {"status": "reset"}


@app.post("/_test/set_item_state")
async def set_item_state(item_name: str, state: str) -> dict[str, str]:
    """Update an item's state and trigger SSE event."""
    mock_state.set_item_state(item_name, state)

    # Queue SSE event in OpenHAB batch format (dict keyed by item name)
    await mock_state.publish_sse_event(
        {
            item_name: {
                "state": state,
            }
        }
    )

    return {"status": "updated", "item": item_name, "state": state}


@app.post("/_test/configure_failure")
async def configure_failure(
    status: int = 500, message: str = "Internal Server Error"
) -> dict[str, str]:
    """Configure server to return errors."""
    mock_state.configure_failure(status, message)
    return {"status": "configured", "fail_status": str(status), "fail_message": message}


@app.post("/_test/clear_failure")
async def clear_failure() -> dict[str, str]:
    """Clear failure configuration."""
    mock_state.clear_failure()
    return {"status": "cleared"}


@app.post("/_test/set_delay")
async def set_delay(delay: float) -> dict[str, str]:
    """Set connection delay in seconds."""
    mock_state.set_connection_delay(delay)
    return {"status": "configured", "delay": str(delay)}


@app.post("/_test/set_malformed")
async def set_malformed(malformed: bool = True) -> dict[str, str]:
    """Configure server to return malformed responses."""
    mock_state.set_malformed(malformed)
    return {"status": "configured", "malformed": str(malformed).lower()}


# =============================================================================
# Server Runner (for standalone use)
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8081)
