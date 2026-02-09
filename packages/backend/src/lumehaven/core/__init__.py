"""Core domain models and exceptions."""

from lumehaven.core.exceptions import (
    LumehavenError,
    SmartHomeConnectionError,
)
from lumehaven.core.signal import Signal, SignalType

__all__ = [
    "Signal",
    "SignalType",
    "LumehavenError",
    "SmartHomeConnectionError",
]
