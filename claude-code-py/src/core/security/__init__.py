"""Security module for command validation.

Provides secure command validation for auto-execution.

Example:
    from core.security import CommandSecurityValidator
    from pathlib import Path

    # Load from config
    validator = CommandSecurityValidator.from_config(
        Path("config/security_rules.yaml")
    )

    # Validate command
    result = validator.validate("git log --oneline")
    if result.is_safe:
        execute(...)
    else:
        logger.warning("Blocked: %s", result.reason)
"""

from .validator import (
    CommandSecurityValidator,
    ValidationResult,
    ValidationPolicy,
    WhitelistPolicy,
    BlacklistPolicy,
    LengthPolicy,
    PatternPolicy
)

__all__ = [
    "CommandSecurityValidator",
    "ValidationResult",
    "ValidationPolicy",
    "WhitelistPolicy",
    "BlacklistPolicy",
    "LengthPolicy",
    "PatternPolicy"
]
