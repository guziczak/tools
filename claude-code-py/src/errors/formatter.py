"""Error formatting utilities.

Provides functions to format errors for display to users.
Based on the TypeScript implementation.
"""

import logging
from typing import Any
from .types import ErrorCategory, UserError

logger = logging.getLogger(__name__)


def create_user_error(
    message: str,
    category: ErrorCategory = ErrorCategory.UNKNOWN,
    resolution: str = None,
    cause: Exception = None,
) -> UserError:
    """Create a user-facing error.

    Args:
        message: Error message
        category: Error category
        resolution: Suggested resolution
        cause: Original exception

    Returns:
        UserError instance
    """
    return UserError(
        message=message,
        category=category,
        resolution=resolution,
        cause=cause,
    )


def format_error_for_display(error: Any) -> str:
    """Format an error for display to the user.

    Args:
        error: Error to format (UserError, Exception, or any value)

    Returns:
        Formatted error string
    """
    if isinstance(error, UserError):
        # Format user error with category and resolution
        output = f"❌ {error.message}\n"

        if error.category != ErrorCategory.UNKNOWN:
            output += f"📂 Category: {error.category.value}\n"

        if error.resolution:
            output += f"💡 {error.resolution}\n"

        if error.cause:
            logger.debug(f"Caused by: {error.cause}")

        return output

    elif isinstance(error, Exception):
        # Format generic exception
        error_name = type(error).__name__
        error_message = str(error)

        output = f"❌ {error_name}"
        if error_message:
            output += f": {error_message}"
        output += "\n"

        return output

    else:
        # Format unknown error type
        return f"❌ Error: {error}\n"


def handle_file_error(error: Exception, file_path: str, operation: str) -> UserError:
    """Handle file operation errors.

    Args:
        error: Original exception
        file_path: File path
        operation: Operation being performed (e.g., 'reading', 'writing')

    Returns:
        UserError with helpful message
    """
    if isinstance(error, FileNotFoundError):
        return create_user_error(
            f"File not found: {file_path}",
            category=ErrorCategory.FILE_SYSTEM,
            resolution="Check that the file exists and the path is correct.",
            cause=error,
        )

    elif isinstance(error, PermissionError):
        return create_user_error(
            f"Permission denied {operation} file: {file_path}",
            category=ErrorCategory.FILE_SYSTEM,
            resolution="Check file permissions or try running with elevated privileges.",
            cause=error,
        )

    elif isinstance(error, IsADirectoryError):
        return create_user_error(
            f"Expected a file but got a directory: {file_path}",
            category=ErrorCategory.FILE_SYSTEM,
            resolution="Provide a file path, not a directory path.",
            cause=error,
        )

    else:
        return create_user_error(
            f"Error {operation} file: {file_path}",
            category=ErrorCategory.FILE_SYSTEM,
            cause=error,
        )


def handle_api_error(error: Exception, status_code: int = None) -> UserError:
    """Handle API errors.

    Args:
        error: Original exception
        status_code: HTTP status code if available

    Returns:
        UserError with helpful message
    """
    if status_code == 401:
        return create_user_error(
            "Authentication failed. Please check your API key.",
            category=ErrorCategory.AUTHENTICATION,
            resolution="Verify your API key and try again. You may need to log in again with /login.",
            cause=error,
        )

    elif status_code == 403:
        return create_user_error(
            "You do not have permission to access this resource.",
            category=ErrorCategory.AUTHENTICATION,
            resolution="Verify that your API key has the necessary permissions.",
            cause=error,
        )

    elif status_code == 404:
        return create_user_error(
            "The requested resource was not found.",
            category=ErrorCategory.API,
            resolution="Check that you are using the correct API endpoint.",
            cause=error,
        )

    elif status_code == 429:
        return create_user_error(
            "Rate limit exceeded.",
            category=ErrorCategory.RATE_LIMIT,
            resolution="Please wait before sending more requests.",
            cause=error,
        )

    elif status_code and 500 <= status_code < 600:
        return create_user_error(
            "The API server encountered an error.",
            category=ErrorCategory.SERVER,
            resolution="This is likely a temporary issue. Please try again later.",
            cause=error,
        )

    else:
        return create_user_error(
            "API request failed.",
            category=ErrorCategory.API,
            resolution="Check the error details and try again.",
            cause=error,
        )


def handle_network_error(error: Exception) -> UserError:
    """Handle network errors.

    Args:
        error: Original exception

    Returns:
        UserError with helpful message
    """
    return create_user_error(
        "Network error: Unable to connect to the API.",
        category=ErrorCategory.NETWORK,
        resolution="Check your internet connection and try again.",
        cause=error,
    )


def handle_timeout_error(error: Exception) -> UserError:
    """Handle timeout errors.

    Args:
        error: Original exception

    Returns:
        UserError with helpful message
    """
    return create_user_error(
        "Request timed out.",
        category=ErrorCategory.TIMEOUT,
        resolution="Try again or increase the timeout setting.",
        cause=error,
    )
