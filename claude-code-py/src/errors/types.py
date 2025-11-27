"""Error types and categories.

Based on the TypeScript implementation from claude-code-source-code-deobfuscation-main.
"""

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
    """User-facing error with helpful information.

    Attributes:
        message: Error message
        category: Error category
        resolution: Suggested resolution
        cause: Original exception that caused this error
    """

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        resolution: Optional[str] = None,
        cause: Optional[Exception] = None,
    ):
        """Initialize user error.

        Args:
            message: Error message
            category: Error category
            resolution: Suggested resolution
            cause: Original exception
        """
        super().__init__(message)
        self.message = message
        self.category = category
        self.resolution = resolution
        self.cause = cause

    def __str__(self) -> str:
        """Format error as string."""
        result = f"{self.message}"
        if self.resolution:
            result += f"\n💡 {self.resolution}"
        return result
