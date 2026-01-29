"""Error handling system for Claude Code Python."""

from .types import (
    ErrorCategory,
    UserError,
    ClaudeCodeError,
    AuthenticationError,
    ConfigurationError,
    ToolExecutionError,
    APIError,
    IntentClassificationError,
)
from .formatter import format_error_for_display, create_user_error

__all__ = [
    "ErrorCategory",
    "UserError",
    "ClaudeCodeError",
    "AuthenticationError",
    "ConfigurationError",
    "ToolExecutionError",
    "APIError",
    "IntentClassificationError",
    "format_error_for_display",
    "create_user_error",
]
