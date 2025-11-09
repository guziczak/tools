"""Intent handlers for pre-executing tools based on user intent.

This module implements the Strategy Pattern for handling different user intents.
Each handler can pre-execute tools and enrich the user message with results,
bypassing Claude's reluctance to use tools with claude.ai endpoint.

Architecture:
- IntentHandler (ABC): Base strategy interface
- Concrete handlers: ExploreProjectHandler, ListFilesHandler, GitLogHandler, etc.
- IntentRouter: Routes intents to appropriate handlers

This is STATE OF THE ART because:
1. Strategy Pattern - extensible without modifying existing code (Open/Closed)
2. Dependency Injection - testable, mockable
3. Single Responsibility - each handler does ONE thing
4. Command Pattern - tool execution is encapsulated
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from tools import ToolRegistry


@dataclass
class IntentResult:
    """Result of intent handling.

    Attributes:
        enriched_message: User message enriched with pre-executed tool results
        metadata: Additional metadata about the execution
        skip_llm: If True, skip sending to Claude (result is already complete)
    """
    enriched_message: str
    metadata: Dict[str, Any]
    skip_llm: bool = False


class IntentHandler(ABC):
    """Abstract base class for intent handlers (Strategy Pattern).

    Each handler implements a specific strategy for dealing with user intent:
    - Pre-execute tools
    - Enrich user message
    - Return enhanced context to Claude
    """

    def __init__(self, tool_registry: Optional["ToolRegistry"] = None):
        """Initialize handler with optional tool registry.

        Args:
            tool_registry: Registry for executing tools
        """
        self.tool_registry = tool_registry

    @abstractmethod
    def can_handle(self, intent: str) -> bool:
        """Check if this handler can handle the given intent.

        Args:
            intent: Intent identifier (e.g., "explore_project")

        Returns:
            True if this handler can handle the intent
        """
        pass

    @abstractmethod
    def handle(self, user_message: str, intent: str) -> IntentResult:
        """Handle the intent by pre-executing tools and enriching message.

        Args:
            user_message: Original user message
            intent: Intent identifier

        Returns:
            IntentResult with enriched message and metadata
        """
        pass


class ExploreProjectHandler(IntentHandler):
    """Handler for 'explore_project' intent.

    Pre-executes:
    1. bash("ls") or bash("dir") to list files
    2. Enriches user message with actual file list
    3. Claude responds based on real data, not assumptions

    This is the STATE OF THE ART approach used by Cursor/Windsurf.
    """

    def can_handle(self, intent: str) -> bool:
        """Check if intent is explore_project."""
        return intent == "explore_project"

    def handle(self, user_message: str, intent: str) -> IntentResult:
        """Pre-execute directory listing and enrich message.

        Args:
            user_message: Original message (e.g., "widzisz projekt?")
            intent: Should be "explore_project"

        Returns:
            IntentResult with file listing embedded in message
        """
        import sys

        print("🎯 [ExploreProjectHandler] Pre-executing directory listing...")

        # Determine correct command for platform
        is_windows = sys.platform.startswith('win')
        list_cmd = "dir" if is_windows else "ls"

        # Execute bash tool to list files
        if self.tool_registry:
            result = self.tool_registry.execute_tool("bash", command=list_cmd)

            if result.status.value == "success":
                file_list = result.output
                print(f"   ✅ Got {len(file_list)} chars of output")

                # Enrich message with actual file listing
                enriched = f"""The user asked: "{user_message}"

I've listed the files in the current directory for you. Here's what's there:

```
{file_list}
```

Based on these files, please answer the user's question about the project."""

                return IntentResult(
                    enriched_message=enriched,
                    metadata={
                        "tool_executed": "bash",
                        "command": list_cmd,
                        "output_length": len(file_list)
                    }
                )
            else:
                # Tool failed, fall back to original message
                print(f"   ❌ bash failed: {result.error}")
                return IntentResult(
                    enriched_message=user_message,
                    metadata={"error": result.error}
                )
        else:
            # No tool registry available
            print("   ⚠️  No tool registry - cannot pre-execute")
            return IntentResult(
                enriched_message=user_message,
                metadata={"error": "No tool registry"}
            )


class ListFilesHandler(IntentHandler):
    """Handler for 'list_files' intent.

    Similar to ExploreProjectHandler but more focused on just listing.
    """

    def can_handle(self, intent: str) -> bool:
        """Check if intent is list_files."""
        return intent == "list_files"

    def handle(self, user_message: str, intent: str) -> IntentResult:
        """Pre-execute directory listing.

        Args:
            user_message: Original message
            intent: Should be "list_files"

        Returns:
            IntentResult with file listing
        """
        import sys

        print("🎯 [ListFilesHandler] Pre-executing directory listing...")

        is_windows = sys.platform.startswith('win')
        list_cmd = "dir" if is_windows else "ls"

        if self.tool_registry:
            result = self.tool_registry.execute_tool("bash", command=list_cmd)

            if result.status.value == "success":
                enriched = f"""Files in current directory:

```
{result.output}
```"""

                return IntentResult(
                    enriched_message=enriched,
                    metadata={"tool_executed": "bash", "command": list_cmd},
                    skip_llm=True  # Result is complete, no need for LLM
                )
            else:
                return IntentResult(
                    enriched_message=user_message,
                    metadata={"error": result.error}
                )

        return IntentResult(
            enriched_message=user_message,
            metadata={"error": "No tool registry"}
        )


class GitLogHandler(IntentHandler):
    """Handler for 'git_log' intent.

    Pre-executes:
    1. git log to show recent commits
    2. Enriches user message with commit history
    3. Claude responds based on actual git data
    """

    def can_handle(self, intent: str) -> bool:
        """Check if intent is git_log."""
        return intent == "git_log"

    def handle(self, user_message: str, intent: str) -> IntentResult:
        """Pre-execute git log and enrich message.

        Args:
            user_message: Original message (e.g., "widzisz ostatniego commita?")
            intent: Should be "git_log"

        Returns:
            IntentResult with git log embedded in message
        """
        print("🎯 [GitLogHandler] Pre-executing git log...")

        # Execute git log to get recent commits
        if self.tool_registry:
            # Try git log first (check if git repo exists)
            result = self.tool_registry.execute_tool("bash", command="git log --oneline -5")

            if result.status.value == "success":
                git_log = result.output
                print(f"   ✅ Got {len(git_log)} chars of git log")

                # Enrich message with actual git log
                enriched = f"""The user asked: "{user_message}"

Here are the last 5 commits from git log:

```
{git_log}
```

Based on this commit history, please answer the user's question."""

                return IntentResult(
                    enriched_message=enriched,
                    metadata={
                        "tool_executed": "bash",
                        "command": "git log --oneline -5",
                        "output_length": len(git_log)
                    }
                )
            else:
                # Git failed - maybe not a git repo
                print(f"   ❌ git log failed: {result.error}")

                # Try to provide helpful context
                enriched = f"""The user asked: "{user_message}"

However, this doesn't appear to be a git repository (git log failed).
Please explain this to the user politely."""

                return IntentResult(
                    enriched_message=enriched,
                    metadata={"error": result.error}
                )
        else:
            # No tool registry available
            print("   ⚠️  No tool registry - cannot pre-execute")
            return IntentResult(
                enriched_message=user_message,
                metadata={"error": "No tool registry"}
            )


class IntentRouter:
    """Routes intents to appropriate handlers (Chain of Responsibility Pattern).

    This implements Chain of Responsibility:
    - Tries each handler in sequence
    - First handler that can_handle() wins
    - Extensible: just add more handlers to the chain
    """

    def __init__(self, tool_registry: Optional["ToolRegistry"] = None):
        """Initialize router with handlers.

        Args:
            tool_registry: Tool registry to pass to handlers
        """
        self.tool_registry = tool_registry

        # Chain of handlers (order matters - first match wins)
        self.handlers = [
            ExploreProjectHandler(tool_registry),
            ListFilesHandler(tool_registry),
            GitLogHandler(tool_registry),  # NEW: Git support!
        ]

    def route(self, intent: str, user_message: str) -> Optional[IntentResult]:
        """Route intent to appropriate handler.

        Args:
            intent: Intent identifier
            user_message: Original user message

        Returns:
            IntentResult if handler found, None otherwise
        """
        for handler in self.handlers:
            if handler.can_handle(intent):
                print(f"🎯 [IntentRouter] Routing '{intent}' to {handler.__class__.__name__}")
                return handler.handle(user_message, intent)

        print(f"🎯 [IntentRouter] No handler for intent '{intent}'")
        return None

    def add_handler(self, handler: IntentHandler):
        """Add a custom handler to the chain.

        This makes the system Open/Closed:
        - Open for extension (add new handlers)
        - Closed for modification (no need to change existing code)

        Args:
            handler: Custom intent handler
        """
        self.handlers.append(handler)
