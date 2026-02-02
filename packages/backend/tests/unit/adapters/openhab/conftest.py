"""Shared fixtures for OpenHAB adapter tests.

These fixtures are automatically discovered by pytest and available to all
test modules in this directory.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from lumehaven.adapters.openhab.adapter import OpenHABAdapter

if TYPE_CHECKING:
    pass


# =============================================================================
# Adapter Fixtures
# =============================================================================


@pytest.fixture
def adapter() -> OpenHABAdapter:
    """Fresh OpenHAB adapter instance with default settings."""
    return OpenHABAdapter(base_url="http://openhab:8080", tag="Dashboard")


@pytest.fixture
def adapter_no_tag() -> OpenHABAdapter:
    """OpenHAB adapter without tag filtering."""
    return OpenHABAdapter(base_url="http://openhab:8080")


# =============================================================================
# Mock Response Fixtures
# =============================================================================


@pytest.fixture
def mock_root_response() -> dict[str, Any]:
    """Mock response from /rest/ endpoint."""
    return {
        "version": "5.0.1",
        "measurementSystem": "SI",
        "locale": "en_US",
        "runtimeInfo": {
            "version": "5.0.1",
            "buildString": "Release Build",
        },
    }


@pytest.fixture
def mock_root_response_us() -> dict[str, Any]:
    """Mock response from /rest/ endpoint with US measurement system."""
    return {
        "version": "5.0.1",
        "measurementSystem": "US",
        "locale": "en_US",
    }
