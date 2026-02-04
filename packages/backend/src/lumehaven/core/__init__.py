"""Core domain models and exceptions."""

from lumehaven.core.exceptions import (
    LumehavenError,
    SmartHomeConnectionError,
)
from lumehaven.core.signal import Signal

__all__ = [
    "Signal",
    "LumehavenError",
    "SmartHomeConnectionError",
]
