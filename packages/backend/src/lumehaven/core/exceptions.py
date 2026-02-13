"""Custom exceptions for the lumehaven backend.

Exception hierarchy:
    LumehavenError (base)
    ├── SmartHomeConnectionError
    ├── AdapterError
    └── SignalNotFoundError
"""


class LumehavenError(Exception):
    """Base exception for all lumehaven errors.

    All custom exceptions inherit from this, allowing callers to catch
    all lumehaven-specific errors with a single except clause.
    """

    pass


class SmartHomeConnectionError(LumehavenError):
    """Raised when connection to the smart home system fails.

    Attributes:
        system: The smart home system type (e.g., "openhab").
        url: The URL that failed to connect.
        cause: The underlying exception, if any.
    """

    def __init__(
        self,
        system: str,
        url: str,
        cause: Exception | None = None,
    ) -> None:
        self.system = system
        self.url = url
        self.cause = cause
        message = f"Failed to connect to {system} at {url}"
        if cause:
            message += f": {cause}"
        super().__init__(message)


class AdapterError(LumehavenError):
    """Raised when a smart home adapter encounters an error.

    This is for errors during data processing, not connection errors.

    Attributes:
        adapter: The adapter type (e.g., "openhab").
        message: Description of what went wrong.
    """

    def __init__(self, adapter: str, message: str) -> None:
        self.adapter = adapter
        super().__init__(f"[{adapter}] {message}")


class SignalNotFoundError(LumehavenError):
    """Raised when a signal ID does not exist in the adapter.

    Used by ``send_command()`` (ADR-011) when the target signal cannot
    be resolved.  Maps to HTTP 404 in the REST API.

    Attributes:
        signal_id: The signal ID that was not found.
    """

    def __init__(self, signal_id: str) -> None:
        self.signal_id = signal_id
        super().__init__(f"Signal not found: {signal_id}")
