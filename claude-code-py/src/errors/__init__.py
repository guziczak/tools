"""Error handling system for Claude Code Python.

Provides structured error types and formatting utilities.
"""

from .types import ErrorCategory, UserError
from .formatter import format_error_for_display, create_user_error

__all__ = [
    "ErrorCategory",
    "UserError",
    "format_error_for_display",
    "create_user_error",
]
