"""Robot Framework keyword library for SSE testing.

Provides keywords to consume and verify Server-Sent Events streams,
which RESTinstance doesn't support natively.

Usage in Robot Framework:
    Library    libraries/SSEKeywords.py

Keywords:
    Connect SSE Stream    url    timeout=5
    Receive SSE Event    timeout=5
    Disconnect SSE Stream
    SSE Event Should Contain    field    expected_value
"""

from __future__ import annotations

import contextlib
import json
import threading
from queue import Empty, Queue
from typing import Any

import httpx
from robot.api import logger
from robot.api.deco import keyword


class SSEKeywords:
    """Robot Framework keywords for Server-Sent Events testing."""

    ROBOT_LIBRARY_SCOPE = "TEST"

    def __init__(self) -> None:
        """Initialize SSE client state."""
        self._client: httpx.Client | None = None
        self._response: httpx.Response | None = None
        self._events: Queue[dict[str, Any]] = Queue()
        self._reader_thread: threading.Thread | None = None
        self._stop_event: threading.Event = threading.Event()
        self._last_event: dict[str, Any] | None = None

    def _parse_sse_line(self, line: str, event_data: dict[str, Any]) -> dict[str, Any]:
        """Parse a single SSE line and update event data."""
        line = line.strip()

        if not line:
            # Empty line signals end of event
            return event_data

        if line.startswith(":"):
            # Comment, ignore
            return event_data

        if ":" in line:
            field, value = line.split(":", 1)
            value = value.lstrip()  # Remove leading space after colon
        else:
            field = line
            value = ""

        if field == "data":
            # Accumulate data fields
            if "data" in event_data:
                event_data["data"] += "\n" + value
            else:
                event_data["data"] = value
        else:
            event_data[field] = value

        return event_data

    def _read_events(self, response: httpx.Response) -> None:
        """Background thread to read SSE events."""
        event_data: dict[str, Any] = {}

        try:
            for line in response.iter_lines():
                if self._stop_event.is_set():
                    break

                line = line.strip()

                if not line:
                    # Empty line = end of event
                    if event_data:
                        # Try to parse data as JSON
                        if "data" in event_data:
                            with contextlib.suppress(json.JSONDecodeError):
                                event_data["data"] = json.loads(event_data["data"])
                        self._events.put(event_data)
                        event_data = {}
                    continue

                if line.startswith(":"):
                    continue  # Comment

                if ":" in line:
                    field, value = line.split(":", 1)
                    value = value.lstrip()
                else:
                    field = line
                    value = ""

                if field == "data":
                    if "data" in event_data:
                        event_data["data"] += "\n" + value
                    else:
                        event_data["data"] = value
                else:
                    event_data[field] = value

        except Exception as e:
            logger.debug(f"SSE reader stopped: {e}")
        finally:
            # Put any remaining partial event
            if event_data:
                self._events.put(event_data)

    @keyword("Connect SSE Stream")
    def connect_sse_stream(self, url: str, timeout: float = 5.0) -> None:
        """Connect to an SSE endpoint and start receiving events.

        Args:
            url: Full URL of the SSE endpoint
            timeout: Connection timeout in seconds (default: 5)
        """
        if self._client is not None:
            self.disconnect_sse_stream()

        self._stop_event.clear()
        self._client = httpx.Client(timeout=timeout)

        try:
            # Start streaming request
            self._response = self._client.stream(
                "GET",
                url,
                headers={"Accept": "text/event-stream"},
            ).__enter__()

            # Verify content type
            content_type = self._response.headers.get("content-type", "")
            if "text/event-stream" not in content_type:
                raise ValueError(f"Expected text/event-stream, got {content_type}")

            # Start background reader thread
            self._reader_thread = threading.Thread(
                target=self._read_events,
                args=(self._response,),
                daemon=True,
            )
            self._reader_thread.start()

            logger.info(f"Connected to SSE stream at {url}")

        except Exception as e:
            self.disconnect_sse_stream()
            raise RuntimeError(f"Failed to connect to SSE stream: {e}") from e

    @keyword("Receive SSE Event")
    def receive_sse_event(self, timeout: float = 5.0) -> dict[str, Any]:
        """Wait for and return the next SSE event.

        Args:
            timeout: Maximum time to wait in seconds (default: 5)

        Returns:
            dict containing event fields (event, data, id, etc.)
        """
        if self._client is None:
            raise RuntimeError("Not connected to SSE stream")

        try:
            event = self._events.get(timeout=timeout)
            self._last_event = event
            logger.info(f"Received SSE event: {event}")
            return event
        except Empty:
            raise RuntimeError(f"No SSE event received within {timeout}s") from None

    @keyword("Disconnect SSE Stream")
    def disconnect_sse_stream(self) -> None:
        """Close the SSE connection."""
        self._stop_event.set()

        if self._response is not None:
            with contextlib.suppress(Exception):
                self._response.close()
            self._response = None

        if self._client is not None:
            with contextlib.suppress(Exception):
                self._client.close()
            self._client = None

        if self._reader_thread is not None:
            self._reader_thread.join(timeout=2)
            self._reader_thread = None

        # Clear event queue
        while not self._events.empty():
            try:
                self._events.get_nowait()
            except Empty:
                break

        self._last_event = None
        logger.info("Disconnected from SSE stream")

    @keyword("SSE Event Should Contain")
    def sse_event_should_contain(
        self, field: str, expected_value: str | None = None
    ) -> None:
        """Verify the last received SSE event contains a field.

        Args:
            field: Field name to check (e.g., "event", "data", "id")
            expected_value: Optional expected value (if None, just checks field exists)
        """
        if self._last_event is None:
            raise RuntimeError("No SSE event has been received")

        if field not in self._last_event:
            raise AssertionError(
                f"SSE event does not contain field '{field}'. Event: {self._last_event}"
            )

        if expected_value is not None:
            actual = self._last_event[field]
            if str(actual) != str(expected_value):
                raise AssertionError(
                    f"SSE event field '{field}' expected '{expected_value}', "
                    f"got '{actual}'"
                )

    @keyword("SSE Event Data Should Contain Key")
    def sse_event_data_should_contain_key(
        self, key: str, expected_value: str | None = None
    ) -> None:
        """Verify the last event's data (parsed as JSON) contains a key.

        Args:
            key: Key to check in the data dict
            expected_value: Optional expected value
        """
        if self._last_event is None:
            raise RuntimeError("No SSE event has been received")

        data = self._last_event.get("data")
        if not isinstance(data, dict):
            raise AssertionError(f"SSE event data is not a dict: {type(data)}")

        if key not in data:
            raise AssertionError(
                f"SSE event data does not contain key '{key}'. Data: {data}"
            )

        if expected_value is not None:
            actual = data[key]
            if str(actual) != str(expected_value):
                raise AssertionError(
                    f"SSE event data key '{key}' expected '{expected_value}', "
                    f"got '{actual}'"
                )

    @keyword("Get Last SSE Event")
    def get_last_sse_event(self) -> dict[str, Any] | None:
        """Return the last received SSE event."""
        return self._last_event

    @keyword("Clear SSE Events")
    def clear_sse_events(self) -> None:
        """Clear all queued events."""
        while not self._events.empty():
            try:
                self._events.get_nowait()
            except Empty:
                break
        self._last_event = None
        logger.info("Cleared SSE event queue")
