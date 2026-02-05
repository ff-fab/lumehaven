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
        self._stream_context: contextlib.AbstractContextManager | None = None
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
            # IMPORTANT: We must store the context manager to prevent garbage collection
            # which would call __exit__() and close the stream prematurely
            self._stream_context = self._client.stream(
                "GET",
                url,
                headers={"Accept": "text/event-stream"},
            )
            self._response = self._stream_context.__enter__()

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

        # Properly exit the stream context manager
        if self._stream_context is not None:
            with contextlib.suppress(Exception):
                self._stream_context.__exit__(None, None, None)
            self._stream_context = None

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

    @keyword("Wait For SSE Event Matching")
    def wait_for_sse_event_matching(
        self,
        field: str,
        expected_value: str,
        timeout: float = 5.0,
        poll_interval: float = 0.1,
    ) -> dict[str, Any]:
        """Poll the SSE event queue until an event matches the criteria.

        This is a robust alternative to `Receive SSE Event` that handles
        timing issues in integration tests. It:
        - Continuously polls for events within the timeout
        - Checks each event for a matching field value
        - Logs all seen events on failure for debugging
        - Returns the first matching event

        Args:
            field: Field path to check. Supports nested paths like "data.id"
                   for JSON-parsed data fields.
            expected_value: Expected value (string comparison).
            timeout: Maximum time to wait in seconds (default: 5).
            poll_interval: Time between poll attempts in seconds (default: 0.1).

        Returns:
            The first matching event dict.

        Raises:
            RuntimeError: If not connected to SSE stream.
            AssertionError: If no matching event received within timeout.
        """
        if self._client is None:
            raise RuntimeError("Not connected to SSE stream")

        import time

        start_time = time.monotonic()
        seen_events: list[dict[str, Any]] = []

        while time.monotonic() - start_time < timeout:
            # Drain all available events from queue
            while True:
                try:
                    event = self._events.get_nowait()
                    seen_events.append(event)
                    self._last_event = event

                    # Check if this event matches
                    if self._event_matches(event, field, expected_value):
                        logger.info(f"Found matching SSE event: {event}")
                        return event
                except Empty:
                    break

            # Wait before next poll
            time.sleep(poll_interval)

        # Timeout - log all seen events for debugging
        logger.error(
            f"No SSE event matching {field}='{expected_value}' "
            f"within {timeout}s. Seen {len(seen_events)} events:"
        )
        for i, event in enumerate(seen_events):
            logger.error(f"  Event {i + 1}: {event}")

        raise AssertionError(
            f"No SSE event with {field}='{expected_value}' received within {timeout}s. "
            f"Saw {len(seen_events)} events."
        )

    def _event_matches(
        self, event: dict[str, Any], field: str, expected_value: str
    ) -> bool:
        """Check if an event matches the field/value criteria.

        Args:
            event: The SSE event dict.
            field: Field path (supports "data.key" for nested access).
            expected_value: Expected value as string.

        Returns:
            True if the field exists and matches expected_value.
        """
        # Support nested field access like "data.id"
        parts = field.split(".")
        value: Any = event

        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return False

        return str(value) == str(expected_value)

    @keyword("Wait For Lumehaven SSE Subscribers")
    def wait_for_lumehaven_sse_subscribers(
        self,
        min_count: int = 1,
        timeout: float = 5.0,
        poll_interval: float = 0.1,
        lumehaven_url: str = "http://localhost:8000",
    ) -> int:
        """Wait until Lumehaven has at least min_count SSE subscribers.

        This provides a synchronization barrier to ensure the SSE client
        has fully connected before triggering events. This prevents race
        conditions where events are published before the subscriber is ready.

        Uses the /metrics endpoint to check subscriber count.

        Args:
            min_count: Minimum number of subscribers required (default: 1).
            timeout: Maximum time to wait in seconds (default: 5).
            poll_interval: Time between poll attempts in seconds (default: 0.1).
            lumehaven_url: Base URL of Lumehaven backend.

        Returns:
            The actual subscriber count when condition is met.

        Raises:
            AssertionError: If subscriber count doesn't reach min_count within timeout.
        """
        import time

        start_time = time.monotonic()
        last_count = 0

        while time.monotonic() - start_time < timeout:
            try:
                with httpx.Client(timeout=2.0) as client:
                    response = client.get(f"{lumehaven_url}/metrics")
                    if response.status_code == 200:
                        metrics = response.json()
                        last_count = metrics.get("subscribers", {}).get("total", 0)
                        if last_count >= min_count:
                            logger.info(
                                f"Lumehaven has {last_count} SSE subscriber(s) "
                                f"(required: {min_count})"
                            )
                            return last_count
            except Exception as e:
                logger.debug(f"Error checking metrics: {e}")

            time.sleep(poll_interval)

        raise AssertionError(
            f"Lumehaven subscriber count ({last_count}) did not reach "
            f"{min_count} within {timeout}s"
        )
