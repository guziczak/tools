"""Automatic command execution when Claude asks user to paste output.

This module implements the Command Pattern for automatic command execution.
When Claude asks user to "paste output from X", we execute X automatically
and send result back to Claude.

Best Practices:
- Command Pattern: Commands are first-class objects
- Strategy Pattern: Different execution strategies
- Single Responsibility: Only handles auto-execution
"""

from typing import Optional, Dict, Any, TYPE_CHECKING
from dataclasses import dataclass
from core.logging import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from tools import ToolRegistry


@dataclass
class ExecutionResult:
    """Result of automatic command execution.

    Attributes:
        success: Whether execution succeeded
        output: Command output (if successful)
        error: Error message (if failed)
        command: Original command that was executed
    """

    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    command: Optional[str] = None


class AutoExecutor:
    """Automatically executes commands when Claude asks user to paste output.

    This is the "magic" that makes Claude Code feel intelligent:
    Instead of asking user "please run git show abc123 and paste the result",
    we detect that request, execute the command, and send result to Claude automatically.

    Architecture:
    1. ResponseAnalyzer detects paste request
    2. AutoExecutor executes the command
    3. Result is injected back into conversation
    4. Claude continues with the actual result
    """

    def __init__(self, tool_registry: Optional["ToolRegistry"] = None):
        """Initialize auto-executor.

        Args:
            tool_registry: Tool registry for executing bash commands
        """
        self.tool_registry = tool_registry

    def execute(self, command: str) -> ExecutionResult:
        """Execute command automatically.

        Args:
            command: Shell command to execute

        Returns:
            ExecutionResult with output or error
        """
        if not self.tool_registry:
            return ExecutionResult(
                success=False, error="No tool registry available", command=command
            )

        logger.debug("AutoExecutor auto-executing: %s", command)

        try:
            # Execute via bash tool (goes through CommandValidator chain)
            result = self.tool_registry.execute_tool("bash", command=command)

            if result.status.value == "success":
                logger.debug("AutoExecutor success: %d chars output", len(result.output))
                return ExecutionResult(success=True, output=result.output, command=command)
            else:
                logger.warning("AutoExecutor failed: %s", result.error)
                return ExecutionResult(success=False, error=result.error, command=command)

        except Exception as e:
            logger.warning("AutoExecutor exception: %s", e)
            return ExecutionResult(success=False, error=str(e), command=command)

    def should_auto_execute(self, command: str) -> bool:
        """Check if command should be auto-executed.

        Some commands are dangerous and should not be auto-executed:
        - Destructive commands (rm, del, format, etc.)
        - Commands that modify state (commit, push, etc.)
        - Interactive commands (vim, nano, etc.)

        Args:
            command: Command to check

        Returns:
            True if safe to auto-execute
        """
        # List of dangerous command prefixes
        dangerous_prefixes = [
            "rm ",
            "del ",
            "format ",
            "dd ",  # Destructive
            "git push",
            "git commit",  # State-modifying (should be explicit)
            "npm publish",
            "pip install",  # Package management
            "sudo ",
            "su ",  # Privilege escalation
            "vim ",
            "nano ",
            "emacs ",  # Interactive editors
            ">",
            ">>",  # File redirection (could overwrite files)
        ]

        command_lower = command.lower().strip()

        for prefix in dangerous_prefixes:
            if command_lower.startswith(prefix) or f" {prefix}" in command_lower:
                logger.warning("AutoExecutor blocking dangerous command: %s", command)
                return False

        # Safe to execute (read-only commands)
        return True

    def create_followup_message(self, command: str, result: ExecutionResult) -> str:
        """Create follow-up message to send to Claude with command result.

        This message simulates user pasting the command output, which is what
        Claude expected. Now Claude can continue with the actual result.

        Args:
            command: Command that was executed
            result: Execution result

        Returns:
            Formatted message for Claude
        """
        if result.success:
            # Format like user pasted the output
            return f"""Output from `{command}`:

```
{result.output}
```

(I ran this command for you since you have access to bash tool)"""
        else:
            # Show error
            return f"""Error executing `{command}`:

```
{result.error}
```

(Auto-execution failed - the command returned an error)"""
