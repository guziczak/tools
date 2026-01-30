"""Proper logging system for Claude Code Python.

This replaces scattered print() statements with structured logging.

Features:
- Colored output (like current system)
- Log levels (DEBUG, INFO, WARNING, ERROR)
- Structured logging (easy to parse, filter, search)
- Context managers for operation tracking
- Performance logging

Best Practices:
- Use logging module (standard library)
- Structured logs (not just strings)
- Context information (module, function, line number)
- Easy filtering by level
"""

import logging
import sys
import os
from typing import Optional
from pathlib import Path


class ColoredFormatter(logging.Formatter):
    """Custom formatter with emoji and color support.

    This preserves the visual style of current print() statements
    while providing proper logging infrastructure.
    """

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[37m",  # White
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    # Emoji prefixes removed for cleaner, ASCII-friendly output
    EMOJIS = {
        "DEBUG": "",
        "INFO": "",
        "WARNING": "",
        "ERROR": "",
        "CRITICAL": "",
    }

    def format(self, record):
        """Format log record with color and emoji.

        Args:
            record: LogRecord to format

        Returns:
            Formatted string
        """
        # Get color and emoji for level
        color = self.COLORS.get(record.levelname, self.RESET)
        emoji = self.EMOJIS.get(record.levelname, "")

        # Format: [Module] Message (prefix emoji only if configured)
        if emoji:
            log_fmt = f"{emoji} [{record.name}] {record.getMessage()}"
        else:
            log_fmt = f"[{record.name}] {record.getMessage()}"

        # Add color
        colored_fmt = f"{color}{log_fmt}{self.RESET}"

        return colored_fmt


def setup_logger(
    name: str, level: Optional[str] = None, log_file: Optional[Path] = None
) -> logging.Logger:
    """Setup a logger with colored console output.

    Args:
        name: Logger name (usually module name)
        level: Log level (DEBUG, INFO, WARNING, ERROR). If None, reads from LOG_LEVEL env var (default: INFO)
        log_file: Optional file path for logging to file

    Returns:
        Configured logger
    """
    # Read log level from environment if not provided
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO")

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers (avoid duplicates)
    logger.handlers.clear()

    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(ColoredFormatter())
    logger.addHandler(console_handler)

    # File handler (if requested)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        logger.addHandler(file_handler)

    # Don't propagate to root logger
    logger.propagate = False

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get or create a logger for a module.

    This is the recommended way to get loggers in your code:

    Example:
        from core.logging import get_logger

        logger = get_logger(__name__)
        logger.info("Starting API client")
        logger.debug("Token type: %s", token_type)

    Args:
        name: Logger name (use __name__)

    Returns:
        Logger instance
    """
    # Check if logger already exists
    logger = logging.getLogger(name)

    if not logger.handlers:
        # Not configured yet - use default config
        return setup_logger(name)

    return logger


# Module-level logger for this module
logger = get_logger(__name__)


__all__ = ["setup_logger", "get_logger", "ColoredFormatter"]
