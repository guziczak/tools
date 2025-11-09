"""Command validation and transformation for cross-platform compatibility.

This module implements the Chain of Responsibility pattern for command validation.
Each validator in the chain can:
1. Validate command syntax
2. Transform command for platform compatibility
3. Block unsafe/unsupported commands

Best Practices:
- Chain of Responsibility: Validators are chained
- Open/Closed: Add new validators without modifying existing code
- Single Responsibility: Each validator does ONE thing
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from dataclasses import dataclass
import sys
import re


@dataclass
class ValidationResult:
    """Result of command validation.

    Attributes:
        is_valid: Whether command is valid/supported
        transformed_command: Transformed command (if modified)
        error_message: Error message if invalid
    """
    is_valid: bool
    transformed_command: Optional[str] = None
    error_message: Optional[str] = None


class CommandValidator(ABC):
    """Abstract base class for command validators (Chain of Responsibility)."""

    def __init__(self, next_validator: Optional['CommandValidator'] = None):
        """Initialize validator with optional next validator in chain.

        Args:
            next_validator: Next validator in the chain
        """
        self.next_validator = next_validator

    def validate(self, command: str) -> ValidationResult:
        """Validate command and pass to next validator in chain.

        Args:
            command: Command to validate

        Returns:
            ValidationResult with is_valid, transformed_command, error_message
        """
        # First, apply this validator's logic
        result = self._validate_impl(command)

        if not result.is_valid:
            # Validation failed, stop chain
            return result

        # Validation passed, continue with transformed command
        command_to_pass = result.transformed_command or command

        if self.next_validator:
            # Pass to next validator in chain
            return self.next_validator.validate(command_to_pass)
        else:
            # End of chain
            return result

    @abstractmethod
    def _validate_impl(self, command: str) -> ValidationResult:
        """Implementation of validation logic for this validator.

        Args:
            command: Command to validate

        Returns:
            ValidationResult
        """
        pass


class UnixCommandBlocker(CommandValidator):
    """Blocks Unix-specific commands on Windows.

    Commands like find, grep, awk, sed don't work reliably on Windows PowerShell.
    This validator blocks them with a helpful error message.
    """

    # Commands that are Unix-specific and have no good PowerShell equivalent
    BLOCKED_COMMANDS = {
        'find': 'Use Get-ChildItem or dir instead',
        'grep': 'Use Select-String instead',
        'awk': 'Use PowerShell string manipulation',
        'sed': 'Use PowerShell -replace operator',
        'tail': 'Use Get-Content -Tail',
        'head': 'Use Get-Content -Head or Select-Object -First',
    }

    def _validate_impl(self, command: str) -> ValidationResult:
        """Block Unix-specific commands on Windows.

        Args:
            command: Command to validate

        Returns:
            ValidationResult (invalid if Unix command on Windows)
        """
        is_windows = sys.platform.startswith('win')

        if not is_windows:
            # On Unix, all commands are OK
            return ValidationResult(is_valid=True, transformed_command=command)

        # Check if command starts with blocked Unix command
        command_lower = command.lower().strip()
        first_word = command_lower.split()[0] if command_lower else ''

        if first_word in self.BLOCKED_COMMANDS:
            suggestion = self.BLOCKED_COMMANDS[first_word]
            error = f"Command '{first_word}' is Unix-specific and not supported on Windows. {suggestion}"
            return ValidationResult(is_valid=False, error_message=error)

        return ValidationResult(is_valid=True, transformed_command=command)


class PowerShellSyntaxFixer(CommandValidator):
    """Fixes Unix syntax for PowerShell compatibility.

    Transforms:
    - && → ; (command chaining)
    - || → ; (or operator, approximate)
    - 2>/dev/null → 2>$null (redirect stderr)
    - ls -la → dir (with flag removal)
    """

    def _validate_impl(self, command: str) -> ValidationResult:
        """Fix Unix syntax for PowerShell.

        Args:
            command: Command to fix

        Returns:
            ValidationResult with transformed command
        """
        is_windows = sys.platform.startswith('win')

        if not is_windows:
            # On Unix, no fixes needed
            return ValidationResult(is_valid=True, transformed_command=command)

        transformed = command

        # Fix 1: Command chaining operators
        transformed = transformed.replace(' && ', '; ')
        transformed = transformed.replace(' || ', '; ')

        # Fix 2: Redirect stderr to null
        transformed = transformed.replace('2>/dev/null', '2>$null')
        transformed = transformed.replace('2> /dev/null', '2>$null')

        # Fix 3: ls with flags → dir
        transformed = re.sub(r'\bls\s+-[a-z]+', 'dir', transformed)
        transformed = re.sub(r'\bls\b', 'dir', transformed)

        # Fix 4: cat → type
        transformed = re.sub(r'\bcat\b', 'type', transformed)

        # Fix 5: Virtual paths
        transformed = transformed.replace('/mnt/user-data/uploads/', './')
        transformed = transformed.replace('/mnt/user-data/', './')
        transformed = transformed.replace('/home/claude', '.')

        # Return transformed if changed
        if transformed != command:
            return ValidationResult(is_valid=True, transformed_command=transformed)
        else:
            return ValidationResult(is_valid=True, transformed_command=command)


class GitCommandValidator(CommandValidator):
    """Validates git commands and provides helpful errors if not in a git repo."""

    def _validate_impl(self, command: str) -> ValidationResult:
        """Validate git commands.

        Args:
            command: Command to validate

        Returns:
            ValidationResult (always valid, but may add context)
        """
        # Git commands are always valid, but we let them fail naturally
        # The error message from git is usually helpful enough
        return ValidationResult(is_valid=True, transformed_command=command)


def create_default_validator_chain() -> CommandValidator:
    """Create default chain of validators for command validation.

    Chain order (most strict → most lenient):
    1. UnixCommandBlocker - blocks unsupported Unix commands
    2. PowerShellSyntaxFixer - fixes PowerShell syntax
    3. GitCommandValidator - validates git commands

    Returns:
        Head of validator chain
    """
    # Build chain from tail to head
    git_validator = GitCommandValidator(next_validator=None)
    syntax_fixer = PowerShellSyntaxFixer(next_validator=git_validator)
    unix_blocker = UnixCommandBlocker(next_validator=syntax_fixer)

    return unix_blocker
