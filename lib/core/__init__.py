"""
Core Module
Provides core functionality for session management and exceptions.
"""

from .exceptions import (
    DependencyError,
    ConversionError,
    ValidationError,
    AudioProcessingError,
    SessionError
)
from .session import SessionContext, SessionTracker, recursive_proxy

__all__ = [
    # Exceptions
    'DependencyError',
    'ConversionError',
    'ValidationError',
    'AudioProcessingError',
    'SessionError',
    # Session
    'SessionContext',
    'SessionTracker',
    'recursive_proxy',
]
