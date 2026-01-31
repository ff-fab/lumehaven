"""Unit-specific test configuration and fixtures.

Fixtures here are available to all unit tests but not integration tests.
"""

import pytest


@pytest.fixture
def mock_httpx_client(mocker):
    """Mock httpx.AsyncClient for adapter tests.

    Note: Requires pytest-mock to be installed.
    """
    # This will be implemented when we add pytest-mock
    pass
