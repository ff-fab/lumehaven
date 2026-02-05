"""Robot Framework keyword library for server management.

Provides keywords to start/stop the mock OpenHAB server and the
Lumehaven backend for integration testing.

Usage in Robot Framework:
    Library    libraries/ServerKeywords.py

Keywords:
    Start Mock OpenHAB Server    port=8081
    Stop Mock OpenHAB Server
    Start Lumehaven Backend    port=8000    openhab_url=http://localhost:8081
    Stop Lumehaven Backend
    Wait For Server Ready    url    timeout=10
"""

from __future__ import annotations

import multiprocessing
import os
import socket
import time
from typing import TYPE_CHECKING

import httpx
import uvicorn
from robot.api import logger
from robot.api.deco import keyword

if TYPE_CHECKING:
    from multiprocessing import Process


# =============================================================================
# Server Process Management
# =============================================================================


def _is_port_in_use(port: int) -> bool:
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex(("localhost", port)) == 0


def _run_mock_openhab(port: int) -> None:
    """Run mock OpenHAB server in a subprocess."""
    # Import here to avoid circular imports
    from tests.integration.mock_openhab.server import app

    # Suppress uvicorn access logs in test output
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="warning",
    )


def _run_lumehaven(port: int, openhab_url: str, config_path: str | None) -> None:
    """Run Lumehaven backend in a subprocess."""
    # Set environment variables for configuration
    os.environ["LUMEHAVEN_OPENHAB_URL"] = openhab_url

    if config_path:
        os.environ["LUMEHAVEN_CONFIG"] = config_path

    # Import and run the app
    from lumehaven.main import create_app

    app = create_app()
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="warning",
    )


# =============================================================================
# Robot Framework Keyword Library
# =============================================================================


class ServerKeywords:
    """Robot Framework keywords for server lifecycle management."""

    ROBOT_LIBRARY_SCOPE = "SUITE"

    def __init__(self) -> None:
        """Initialize server process references."""
        self._mock_openhab_process: Process | None = None
        self._lumehaven_process: Process | None = None
        self._mock_openhab_port: int = 8081
        self._lumehaven_port: int = 8000

    @keyword("Start Mock OpenHAB Server")
    def start_mock_openhab_server(self, port: int = 8081) -> None:
        """Start the mock OpenHAB server on the specified port.

        Args:
            port: Port number (default: 8081)
        """
        if self._mock_openhab_process is not None:
            logger.warn("Mock OpenHAB server already running")
            return

        if _is_port_in_use(port):
            raise RuntimeError(f"Port {port} is already in use")

        self._mock_openhab_port = port
        self._mock_openhab_process = multiprocessing.Process(
            target=_run_mock_openhab,
            args=(port,),
            daemon=True,
        )
        self._mock_openhab_process.start()
        logger.info(f"Started mock OpenHAB server on port {port}")

    @keyword("Stop Mock OpenHAB Server")
    def stop_mock_openhab_server(self) -> None:
        """Stop the mock OpenHAB server."""
        if self._mock_openhab_process is None:
            logger.warn("Mock OpenHAB server not running")
            return

        self._mock_openhab_process.terminate()
        self._mock_openhab_process.join(timeout=5)

        if self._mock_openhab_process.is_alive():
            self._mock_openhab_process.kill()
            self._mock_openhab_process.join(timeout=2)

        self._mock_openhab_process = None
        logger.info("Stopped mock OpenHAB server")

    @keyword("Start Lumehaven Backend")
    def start_lumehaven_backend(
        self,
        port: int = 8000,
        openhab_url: str = "http://localhost:8081",
        config_path: str | None = None,
    ) -> None:
        """Start the Lumehaven backend on the specified port.

        Args:
            port: Port number (default: 8000)
            openhab_url: URL of the OpenHAB server (default: http://localhost:8081)
            config_path: Path to config file (optional)
        """
        if self._lumehaven_process is not None:
            logger.warn("Lumehaven backend already running")
            return

        if _is_port_in_use(port):
            raise RuntimeError(f"Port {port} is already in use")

        self._lumehaven_port = port
        self._lumehaven_process = multiprocessing.Process(
            target=_run_lumehaven,
            args=(port, openhab_url, config_path),
            daemon=True,
        )
        self._lumehaven_process.start()
        logger.info(f"Started Lumehaven backend on port {port}")

    @keyword("Stop Lumehaven Backend")
    def stop_lumehaven_backend(self) -> None:
        """Stop the Lumehaven backend."""
        if self._lumehaven_process is None:
            logger.warn("Lumehaven backend not running")
            return

        self._lumehaven_process.terminate()
        self._lumehaven_process.join(timeout=5)

        if self._lumehaven_process.is_alive():
            self._lumehaven_process.kill()
            self._lumehaven_process.join(timeout=2)

        self._lumehaven_process = None
        logger.info("Stopped Lumehaven backend")

    @keyword("Wait For Server Ready")
    def wait_for_server_ready(self, url: str, timeout: float = 10.0) -> None:
        """Wait until a server is ready to accept connections.

        Args:
            url: URL to check (e.g., http://localhost:8000/health)
            timeout: Maximum time to wait in seconds (default: 10)
        """
        start_time = time.time()
        last_error = None

        while time.time() - start_time < timeout:
            try:
                response = httpx.get(url, timeout=1.0)
                if response.status_code < 500:
                    logger.info(f"Server ready at {url}")
                    return
            except httpx.RequestError as e:
                last_error = e

            time.sleep(0.2)

        error_msg = f"Server at {url} not ready after {timeout}s"
        if last_error:
            error_msg += f": {last_error}"
        raise RuntimeError(error_msg)

    @keyword("Reset Mock OpenHAB State")
    def reset_mock_openhab_state(self) -> None:
        """Reset the mock OpenHAB server to default state."""
        url = f"http://localhost:{self._mock_openhab_port}/_test/reset"
        response = httpx.post(url, timeout=5.0)
        response.raise_for_status()
        logger.info("Reset mock OpenHAB state")

    @keyword("Set Mock OpenHAB Item State")
    def set_mock_openhab_item_state(self, item_name: str, state: str) -> None:
        """Update an item's state in the mock OpenHAB server.

        Args:
            item_name: Name of the item to update
            state: New state value
        """
        url = f"http://localhost:{self._mock_openhab_port}/_test/set_item_state"
        response = httpx.post(
            url,
            params={"item_name": item_name, "state": state},
            timeout=5.0,
        )
        response.raise_for_status()
        logger.info(f"Set {item_name} state to {state}")

    @keyword("Configure Mock OpenHAB Failure")
    def configure_mock_openhab_failure(
        self,
        status_code: int | None = None,
        message: str = "Internal Server Error",
        timeout: float | None = None,
        malformed: bool = False,
    ) -> None:
        """Configure the mock OpenHAB server to simulate failures.

        Args:
            status_code: HTTP status code to return (e.g., 500)
            message: Error message (default: "Internal Server Error")
            timeout: Connection delay in seconds to simulate timeout
            malformed: Whether to return malformed JSON responses
        """
        base_url = f"http://localhost:{self._mock_openhab_port}/_test"

        if status_code is not None:
            response = httpx.post(
                f"{base_url}/configure_failure",
                params={"status": status_code, "message": message},
                timeout=5.0,
            )
            response.raise_for_status()
            logger.info(f"Configured mock OpenHAB to fail with {status_code}")

        if timeout is not None:
            response = httpx.post(
                f"{base_url}/set_delay",
                params={"delay": timeout},
                timeout=5.0,
            )
            response.raise_for_status()
            logger.info(f"Configured mock OpenHAB with {timeout}s delay")

        if malformed:
            response = httpx.post(
                f"{base_url}/set_malformed",
                params={"malformed": True},
                timeout=5.0,
            )
            response.raise_for_status()
            logger.info("Configured mock OpenHAB to return malformed responses")

    @keyword("Clear Mock OpenHAB Failure")
    def clear_mock_openhab_failure(self) -> None:
        """Clear any configured failure in the mock OpenHAB server.

        Clears error status, connection delay, and malformed response settings.
        """
        base_url = f"http://localhost:{self._mock_openhab_port}/_test"

        response = httpx.post(f"{base_url}/clear_failure", timeout=5.0)
        response.raise_for_status()

        response = httpx.post(f"{base_url}/set_delay", params={"delay": 0}, timeout=5.0)
        response.raise_for_status()

        response = httpx.post(
            f"{base_url}/set_malformed", params={"malformed": False}, timeout=5.0
        )
        response.raise_for_status()

        logger.info("Cleared mock OpenHAB failure configuration")

    @keyword("Get Mock OpenHAB Port")
    def get_mock_openhab_port(self) -> int:
        """Return the port number of the mock OpenHAB server."""
        return self._mock_openhab_port

    @keyword("Get Lumehaven Port")
    def get_lumehaven_port(self) -> int:
        """Return the port number of the Lumehaven backend."""
        return self._lumehaven_port
