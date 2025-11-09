"""Command security validator.

This module validates commands before auto-execution to prevent dangerous operations.

Security Approach:
1. WHITELIST first (most secure) - only allow known-safe commands
2. BLACKLIST as fallback - block known-dangerous patterns
3. Configurable via YAML (easy to update without code changes)

Architecture:
- Strategy Pattern: Different validation strategies (whitelist, blacklist)
- Chain of Responsibility: Multiple validators in sequence
- Policy Objects: Encapsulate validation rules

Best Practices:
- Defense in depth (multiple layers)
- Fail secure (block if uncertain)
- Configurable (no hardcoded rules)
- Auditable (log all decisions)
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Set
from dataclasses import dataclass
from pathlib import Path
import yaml


@dataclass
class ValidationResult:
    """Result of command validation.

    Attributes:
        is_safe: Whether command is safe to execute
        reason: Human-readable reason for decision
        matched_rule: Which rule triggered the decision
        confidence: Confidence in decision (0.0-1.0)
    """

    is_safe: bool
    reason: str
    matched_rule: Optional[str] = None
    confidence: float = 1.0


class ValidationPolicy(ABC):
    """Abstract base class for validation policies (Strategy Pattern)."""

    @abstractmethod
    def validate(self, command: str) -> ValidationResult:
        """Validate a command.

        Args:
            command: Command to validate

        Returns:
            ValidationResult with safety decision
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get policy name for logging."""
        pass


class WhitelistPolicy(ValidationPolicy):
    """Whitelist-based validation (most secure).

    Only allows commands that explicitly match whitelist patterns.
    This is SECURE BY DEFAULT - blocks everything except known-safe commands.

    Example:
        policy = WhitelistPolicy(allowed_prefixes=["git log", "ls"])
        result = policy.validate("git log --oneline")
        # => ValidationResult(is_safe=True, reason="Matches whitelist")

        result = policy.validate("rm -rf /")
        # => ValidationResult(is_safe=False, reason="Not in whitelist")
    """

    def __init__(self, allowed_prefixes: List[str]):
        """Initialize with allowed command prefixes.

        Args:
            allowed_prefixes: List of allowed command prefixes
        """
        self.allowed_prefixes = [prefix.lower() for prefix in allowed_prefixes]

    def validate(self, command: str) -> ValidationResult:
        """Check if command starts with whitelisted prefix.

        Args:
            command: Command to validate

        Returns:
            ValidationResult
        """
        cmd_lower = command.lower().strip()

        for prefix in self.allowed_prefixes:
            if cmd_lower.startswith(prefix):
                return ValidationResult(
                    is_safe=True,
                    reason=f"Matches whitelist: {prefix}",
                    matched_rule=prefix,
                    confidence=1.0,
                )

        # Not in whitelist - block
        return ValidationResult(
            is_safe=False, reason="Command not in whitelist (fail secure)", confidence=1.0
        )

    def get_name(self) -> str:
        return "WhitelistPolicy"


class BlacklistPolicy(ValidationPolicy):
    """Blacklist-based validation (less secure, use as fallback).

    Blocks commands matching dangerous patterns.
    This is INSECURE BY DEFAULT - allows everything except known-bad commands.

    Use only when whitelist is not practical (e.g., too many safe commands).

    Example:
        policy = BlacklistPolicy(blocked_patterns=["rm ", "del "])
        result = policy.validate("ls -la")
        # => ValidationResult(is_safe=True, reason="No blacklist match")

        result = policy.validate("rm -rf /")
        # => ValidationResult(is_safe=False, reason="Matches blacklist: rm")
    """

    def __init__(self, blocked_patterns: List[str]):
        """Initialize with blocked patterns.

        Args:
            blocked_patterns: List of dangerous command patterns
        """
        self.blocked_patterns = [pattern.lower() for pattern in blocked_patterns]

    def validate(self, command: str) -> ValidationResult:
        """Check if command matches blacklisted pattern.

        Args:
            command: Command to validate

        Returns:
            ValidationResult
        """
        # Normalize whitespace (prevent tab/newline bypass)
        cmd_normalized = " ".join(command.split())
        cmd_lower = cmd_normalized.lower().strip()

        for pattern in self.blocked_patterns:
            # Check prefix match OR pattern anywhere in command
            if cmd_lower.startswith(pattern) or f" {pattern}" in cmd_lower:
                return ValidationResult(
                    is_safe=False,
                    reason=f"Matches blacklist: {pattern}",
                    matched_rule=pattern,
                    confidence=1.0,
                )

        # No blacklist match - allow
        return ValidationResult(
            is_safe=True,
            reason="No blacklist match",
            confidence=0.7,  # Lower confidence (could still be dangerous)
        )

    def get_name(self) -> str:
        return "BlacklistPolicy"


class LengthPolicy(ValidationPolicy):
    """Validates command length (prevents abuse).

    Long commands are often suspicious (e.g., encoded payloads, complex chains).
    """

    def __init__(self, max_length: int = 500):
        """Initialize with maximum command length.

        Args:
            max_length: Maximum allowed command length
        """
        self.max_length = max_length

    def validate(self, command: str) -> ValidationResult:
        """Check command length.

        Args:
            command: Command to validate

        Returns:
            ValidationResult
        """
        if len(command) > self.max_length:
            return ValidationResult(
                is_safe=False,
                reason=f"Command too long ({len(command)} > {self.max_length} chars)",
                confidence=1.0,
            )

        return ValidationResult(is_safe=True, reason="Length OK", confidence=1.0)

    def get_name(self) -> str:
        return "LengthPolicy"


class PatternPolicy(ValidationPolicy):
    """Validates against suspicious patterns (e.g., code injection).

    Blocks commands containing dangerous patterns like eval, exec, etc.
    """

    def __init__(self, suspicious_patterns: List[str]):
        """Initialize with suspicious patterns.

        Args:
            suspicious_patterns: List of patterns to block
        """
        self.suspicious_patterns = [p.lower() for p in suspicious_patterns]

    def validate(self, command: str) -> ValidationResult:
        """Check for suspicious patterns.

        Args:
            command: Command to validate

        Returns:
            ValidationResult
        """
        cmd_lower = command.lower()

        for pattern in self.suspicious_patterns:
            if pattern in cmd_lower:
                return ValidationResult(
                    is_safe=False,
                    reason=f"Suspicious pattern detected: {pattern}",
                    matched_rule=pattern,
                    confidence=0.9,
                )

        return ValidationResult(is_safe=True, reason="No suspicious patterns", confidence=1.0)

    def get_name(self) -> str:
        return "PatternPolicy"


class CommandSecurityValidator:
    """Main security validator (Chain of Responsibility).

    Combines multiple validation policies for defense in depth.
    All policies must pass for command to be considered safe.

    Example:
        validator = CommandSecurityValidator.from_config("security_rules.yaml")
        result = validator.validate("git log --oneline")

        if result.is_safe:
            execute_command(...)
        else:
            logger.warning("Blocked: %s", result.reason)
    """

    def __init__(self, policies: List[ValidationPolicy]):
        """Initialize with validation policies.

        Args:
            policies: List of ValidationPolicy instances
        """
        self.policies = policies

    def validate(self, command: str) -> ValidationResult:
        """Validate command through all policies.

        All policies must pass (AND logic) for command to be safe.

        Args:
            command: Command to validate

        Returns:
            ValidationResult (first failure or final success)
        """
        from ..logging import get_logger

        logger = get_logger(__name__)

        logger.debug("Validating command: %s", command)

        # Run all policies
        for policy in self.policies:
            result = policy.validate(command)

            logger.debug(
                "[%s] Result: safe=%s, reason=%s", policy.get_name(), result.is_safe, result.reason
            )

            if not result.is_safe:
                # First failure - block immediately
                logger.warning("Command BLOCKED by %s: %s", policy.get_name(), result.reason)
                return result

        # All policies passed
        logger.info("Command ALLOWED: %s", command)
        return ValidationResult(is_safe=True, reason="All policies passed", confidence=1.0)

    @classmethod
    def from_config(cls, config_path: Path) -> "CommandSecurityValidator":
        """Create validator from YAML config file.

        Args:
            config_path: Path to security_rules.yaml

        Returns:
            Configured CommandSecurityValidator
        """
        from ..logging import get_logger

        logger = get_logger(__name__)

        # Load config
        with open(config_path) as f:
            config = yaml.safe_load(f)

        policies = []

        # Add whitelist policy (if enabled)
        if config.get("config", {}).get("use_whitelist", False):
            # Collect all whitelisted commands
            whitelist = []
            for category in config.get("whitelist", {}).values():
                whitelist.extend(category)

            policies.append(WhitelistPolicy(whitelist))
            logger.info("Loaded whitelist with %d commands", len(whitelist))

        # Add blacklist policy
        blacklist = []
        for category in config.get("blacklist", {}).values():
            blacklist.extend(category)

        policies.append(BlacklistPolicy(blacklist))
        logger.info("Loaded blacklist with %d patterns", len(blacklist))

        # Add length policy
        max_length = config.get("config", {}).get("max_command_length", 500)
        policies.append(LengthPolicy(max_length))

        # Add pattern policy
        suspicious = config.get("config", {}).get("suspicious_patterns", [])
        if suspicious:
            policies.append(PatternPolicy(suspicious))
            logger.info("Loaded %d suspicious patterns", len(suspicious))

        return cls(policies)

    @classmethod
    def create_default(cls) -> "CommandSecurityValidator":
        """Create validator with sensible defaults (if config file missing).

        Returns:
            CommandSecurityValidator with default policies
        """
        from ..logging import get_logger

        logger = get_logger(__name__)

        logger.warning("Using default security policy (no config file)")

        # Default: strict whitelist
        whitelist = [
            "git log",
            "git show",
            "git diff",
            "git status",
            "git branch",
            "ls",
            "cat",
            "pwd",
            "echo",
            "which",
        ]

        blacklist = [
            "rm ",
            "del ",
            "sudo ",
            "su ",
            "format ",
            "dd ",
            "git push",
            "git commit",
            "> ",
            ">> ",
        ]

        return cls(
            [
                WhitelistPolicy(whitelist),
                BlacklistPolicy(blacklist),
                LengthPolicy(500),
            ]
        )
