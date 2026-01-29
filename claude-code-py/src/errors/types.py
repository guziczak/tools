"""Error types and hierarchy for Claude Code Python."""

from enum import Enum
from typing import Optional


class ErrorCategory(Enum):
    """Error categories for better error handling and user feedback."""

    AUTHENTICATION = "authentication"
    FILE_SYSTEM = "file_system"
    API = "api"
    AI_SERVICE = "ai_service"
    VALIDATION = "validation"
    COMMAND = "command"
    COMMAND_EXECUTION = "command_execution"
    NETWORK = "network"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    SERVER = "server"
    UNKNOWN = "unknown"


class UserError(Exception):
    """User-facing error with helpful information."""

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        resolution: Optional[str] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.resolution = resolution
        self.cause = cause

    def __str__(self) -> str:
        result = f"{self.message}"
        if self.resolution:
            result += f"\n  Resolution: {self.resolution}"
        return result


# --- Structured error hierarchy ---


class ClaudeCodeError(Exception):
    """Base exception for all Claude Code errors."""

    pass


class AuthenticationError(ClaudeCodeError):
    """Authentication or token errors."""

    pass


class ConfigurationError(ClaudeCodeError):
    """Invalid configuration (missing keys, bad values)."""

    pass


class ToolExecutionError(ClaudeCodeError):
    """Tool execution failure."""

    def __init__(self, message: str, tool_name: str = "", cause: Optional[Exception] = None):
        super().__init__(message)
        self.tool_name = tool_name
        self.cause = cause


class APIError(ClaudeCodeError):
    """API call failure."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        retry_after: Optional[float] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after


class IntentClassificationError(ClaudeCodeError):
    """Intent classification failure."""

    pass
