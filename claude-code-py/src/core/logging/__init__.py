"""Logging module for Claude Code Python.

Replace print() statements with proper logging:

Before:
    print(f"🎯 [Intent] Tier 1 match: {intent}")

After:
    from core.logging import get_logger
    logger = get_logger(__name__)
    logger.info("Tier 1 match: %s", intent)
"""

from .logger import setup_logger, get_logger, ColoredFormatter

__all__ = ["setup_logger", "get_logger", "ColoredFormatter"]
