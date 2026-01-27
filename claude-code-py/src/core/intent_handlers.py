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
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from dataclasses import dataclass, field

from .logging import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from tools import ToolRegistry


@dataclass
class IntentResult:
    """Result of intent handling.

    NEW (Best Practice): Use tool_results instead of enriched_message!
    This follows Anthropic API format - tool results are injected as proper
    tool_use/tool_result messages, not concatenated into user message.

    Attributes:
        enriched_message: (DEPRECATED) User message enriched with pre-executed tool results.
                         Use tool_results instead for zero redundancy.
        metadata: Additional metadata about the execution
        skip_llm: If True, skip sending to Claude (result is already complete)
        tool_results: (NEW - PREFERRED) List of pre-executed tool results.
                     Each dict should have: tool_name, tool_input, tool_output
    """

    enriched_message: Optional[str] = None  # Made optional (deprecated)
    metadata: Dict[str, Any] = field(default_factory=dict)
    skip_llm: bool = False
    tool_results: Optional[List[Dict[str, Any]]] = None  # NEW - preferred approach!


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
    2. Returns tool results in Anthropic API format (zero redundancy!)
    3. Claude responds based on real data, not assumptions

    This is the STATE OF THE ART approach used by Cursor/Windsurf.
    """

    def can_handle(self, intent: str) -> bool:
        """Check if intent is explore_project."""
        return intent == "explore_project"

    def handle(self, user_message: str, intent: str) -> IntentResult:
        """Pre-execute directory listing and return as tool result.

        NEW: Returns tool_results instead of enriched_message!

        Args:
            user_message: Original message (e.g., "widzisz projekt?")
            intent: Should be "explore_project"

        Returns:
            IntentResult with tool_results (file listing)
        """
        import sys

        logger.debug("ExploreProjectHandler pre-executing directory listing")

        # Determine correct command for platform
        is_windows = sys.platform.startswith("win")
        list_cmd = "dir" if is_windows else "ls"

        # Execute bash tool to list files
        if self.tool_registry:
            result = self.tool_registry.execute_tool("bash", command=list_cmd)

            if result.status.value == "success":
                file_list = result.output
                logger.debug("ExploreProjectHandler got %d chars of output", len(file_list))

                # Return as TOOL RESULT (Anthropic API format - best practice!)
                return IntentResult(
                    tool_results=[
                        {
                            "tool_name": "bash",
                            "tool_input": {"command": list_cmd},
                            "tool_output": file_list,
                        }
                    ],
                    metadata={
                        "tool_executed": "bash",
                        "command": list_cmd,
                        "output_length": len(file_list),
                    },
                )
            else:
                # Tool failed, fall back to original message
                logger.warning("ExploreProjectHandler bash failed: %s", result.error)
                return IntentResult(
                    tool_results=[
                        {
                            "tool_name": "bash",
                            "tool_input": {"command": list_cmd},
                            "tool_output": f"Error: {result.error}",
                            "is_error": True,
                        }
                    ],
                    metadata={"error": result.error},
                )
        else:
            # No tool registry available
            logger.warning("ExploreProjectHandler no tool registry - cannot pre-execute")
            return IntentResult(metadata={"error": "No tool registry"})


class ListFilesHandler(IntentHandler):
    """Handler for 'list_files' intent.

    Similar to ExploreProjectHandler but can skip LLM if result is complete.
    """

    def can_handle(self, intent: str) -> bool:
        """Check if intent is list_files."""
        return intent == "list_files"

    def handle(self, user_message: str, intent: str) -> IntentResult:
        """Pre-execute directory listing and return as tool result.

        NEW: Returns tool_results instead of enriched_message!
        Can optionally skip_llm if result is complete.

        Args:
            user_message: Original message
            intent: Should be "list_files"

        Returns:
            IntentResult with tool_results (file listing)
        """
        import sys

        logger.debug("ListFilesHandler pre-executing directory listing")

        is_windows = sys.platform.startswith("win")
        list_cmd = "dir" if is_windows else "ls"

        if self.tool_registry:
            result = self.tool_registry.execute_tool("bash", command=list_cmd)

            if result.status.value == "success":
                # Return as TOOL RESULT with skip_llm option
                return IntentResult(
                    tool_results=[
                        {
                            "tool_name": "bash",
                            "tool_input": {"command": list_cmd},
                            "tool_output": result.output,
                        }
                    ],
                    metadata={"tool_executed": "bash", "command": list_cmd},
                    skip_llm=True,  # Result is complete, no need for LLM
                )
            else:
                return IntentResult(
                    tool_results=[
                        {
                            "tool_name": "bash",
                            "tool_input": {"command": list_cmd},
                            "tool_output": f"Error: {result.error}",
                            "is_error": True,
                        }
                    ],
                    metadata={"error": result.error},
                )

        return IntentResult(metadata={"error": "No tool registry"})


class GitLogHandler(IntentHandler):
    """Handler for 'git_log' intent.

    Pre-executes:
    1. git log to show recent commits
    2. Returns tool results in Anthropic API format (zero redundancy!)
    3. Claude responds based on actual git data
    """

    def can_handle(self, intent: str) -> bool:
        """Check if intent is git_log."""
        return intent == "git_log"

    def handle(self, user_message: str, intent: str) -> IntentResult:
        """Pre-execute git log and return as tool result.

        NEW: Returns tool_results instead of enriched_message!
        This follows Anthropic API best practices - tool results are injected
        as proper tool_use/tool_result messages, not text concatenation.

        Args:
            user_message: Original message (e.g., "widzisz ostatniego commita?")
            intent: Should be "git_log"

        Returns:
            IntentResult with tool_results (zero redundancy!)
        """
        logger.debug("GitLogHandler pre-executing git log")

        # Execute git log to get recent commits
        if self.tool_registry:
            # Try git log first (check if git repo exists)
            result = self.tool_registry.execute_tool("bash", command="git log --oneline -5")

            if result.status.value == "success":
                git_log = result.output
                logger.debug("GitLogHandler got %d chars of git log", len(git_log))

                # Return as TOOL RESULT (Anthropic API format - best practice!)
                return IntentResult(
                    tool_results=[
                        {
                            "tool_name": "bash",
                            "tool_input": {"command": "git log --oneline -5"},
                            "tool_output": git_log,
                        }
                    ],
                    metadata={
                        "tool_executed": "bash",
                        "command": "git log --oneline -5",
                        "output_length": len(git_log),
                    },
                )
            else:
                # Git failed - maybe not a git repo
                logger.warning("GitLogHandler git log failed: %s", result.error)

                # Return error in tool result format
                return IntentResult(
                    tool_results=[
                        {
                            "tool_name": "bash",
                            "tool_input": {"command": "git log --oneline -5"},
                            "tool_output": f"Error: {result.error}",
                            "is_error": True,
                        }
                    ],
                    metadata={"error": result.error},
                )
        else:
            # No tool registry available
            logger.warning("GitLogHandler no tool registry - cannot pre-execute")
            return IntentResult(metadata={"error": "No tool registry"})


class AnalyzeChangesHandler(IntentHandler):
    """Handler for 'analyze_changes' intent.

    When user says "przeanalizuj zmiany" / "analyze changes" after seeing a commit,
    this handler:
    1. Extracts commit hash from conversation context
    2. Pre-executes git show <hash>
    3. Enriches message with actual diff

    NEW: Uses ContextManager for safe caching:
    - Caches commit hash for 5 minutes
    - Auto-verifies before use
    - Prevents showing stale commits
    """

    def __init__(
        self,
        tool_registry: Optional["ToolRegistry"] = None,
        messages: list = None,
        context_manager=None,
    ):
        """Initialize with tool registry and conversation messages.

        Args:
            tool_registry: Registry for executing tools
            messages: Conversation history (to extract commit hash from)
            context_manager: ContextManager for safe caching (optional)
        """
        super().__init__(tool_registry)
        self.messages = messages or []
        self.context_manager = context_manager

    def can_handle(self, intent: str) -> bool:
        """Check if intent is analyze_changes."""
        return intent == "analyze_changes"

    def _extract_commit_hash(self) -> Optional[str]:
        """Extract commit hash from recent conversation with safe caching.

        NEW: Uses ContextManager to cache last seen commit:
        - First checks cache (with auto-verification!)
        - If cache fresh, returns immediately
        - If cache stale/missing, extracts from messages
        - Stores in cache for future use

        Looks for patterns like:
        - "e35c4f4"
        - "commit abc123"
        - "hash: 1a2b3c4"

        Returns:
            Commit hash if found, None otherwise
        """
        import re

        # Try cache first (with auto-verification!)
        if self.context_manager:
            cached = self.context_manager.get_verified("last_commit_hash")

            if cached and cached["status"] == "fresh":
                logger.debug(
                    "Using cached commit hash: %s (age: %.0fs)",
                    cached["value"],
                    cached["age_seconds"],
                )
                return cached["value"]
            elif cached and cached["status"] == "stale":
                logger.warning(
                    "Cached commit changed: %s -> %s",
                    cached["cached_value"],
                    cached["live_value"],
                )
                # Return NEW value (auto-updated!)
                return cached["live_value"]

        # Cache miss or stale - extract from messages
        # Check last 3 messages (user + assistant messages)
        recent_messages = self.messages[-3:] if len(self.messages) >= 3 else self.messages

        for msg in reversed(recent_messages):
            content = msg.get("content", "")
            if isinstance(content, str):
                # Pattern: 6+ character hex string (git short hash)
                # Git uses 6-40 character hashes (default: 7, but 6 is valid)
                # Common formats: "e35c4f4", "commit e35c4f4", "hash: e35c4f4"
                match = re.search(r"\b([0-9a-f]{6,40})\b", content, re.IGNORECASE)
                if match:
                    hash_candidate = match.group(1)
                    logger.debug("Found potential commit hash: %s", hash_candidate)

                    # Store in cache with verification
                    if self.context_manager:
                        self.context_manager.store(
                            "last_commit_hash",
                            hash_candidate,
                            ttl_seconds=300,  # Valid for 5 minutes
                            verification_cmd="git log -1 --format=%H",
                        )

                    return hash_candidate

        logger.debug("No commit hash found in recent messages")
        return None

    def handle(self, user_message: str, intent: str) -> IntentResult:
        """Pre-execute git show and return as tool result.

        NEW: Returns tool_results with analysis instructions in metadata!
        This follows Anthropic API best practices.

        Args:
            user_message: Original message (e.g., "przeanalizuj zmiany")
            intent: Should be "analyze_changes"

        Returns:
            IntentResult with tool_results (git show output)
        """
        logger.debug("AnalyzeChangesHandler pre-executing git show")

        # Extract commit hash from conversation
        commit_hash = self._extract_commit_hash()

        if not commit_hash:
            logger.debug("No commit hash in context - trying git log fallback")
            # FALLBACK: Check git log for last commit
            if self.tool_registry:
                result = self.tool_registry.execute_tool("bash", command="git log -1 --format=%H")
                if result.status.value == "success":
                    commit_hash = result.output.strip()
                    logger.debug("Got commit hash from git log: %s", commit_hash[:7])
                else:
                    logger.warning("git log failed: %s", result.error)
                    return IntentResult(
                        metadata={"error": "No commit hash found and git log failed"}
                    )
            else:
                logger.warning("No tool registry for git log fallback")
                return IntentResult(metadata={"error": "No commit hash found"})

        # Execute git show
        if self.tool_registry:
            cmd = f"git show {commit_hash}"
            logger.debug("Executing: %s", cmd)

            result = self.tool_registry.execute_tool("bash", command=cmd)

            if result.status.value == "success":
                logger.debug("Got %d chars of diff", len(result.output))

                # Return as TOOL RESULT with analysis instructions in metadata
                return IntentResult(
                    tool_results=[
                        {
                            "tool_name": "bash",
                            "tool_input": {"command": cmd},
                            "tool_output": result.output,
                        }
                    ],
                    metadata={
                        "tool_executed": "bash",
                        "command": cmd,
                        "commit_hash": commit_hash,
                        # Analysis instructions (will be added to system prompt)
                        "analysis_instructions": """Analyze WHAT CHANGED in this commit:
1. List which files were modified
2. Summarize key changes (added functions, deleted code, refactored logic)
3. Explain the purpose of these changes
4. Focus on CONCRETE changes, not meta-commentary about design patterns

Be specific and practical.""",
                    },
                )
            else:
                logger.warning("git show failed: %s", result.error)
                return IntentResult(
                    tool_results=[
                        {
                            "tool_name": "bash",
                            "tool_input": {"command": cmd},
                            "tool_output": f"Error: {result.error}",
                            "is_error": True,
                        }
                    ],
                    metadata={"error": result.error},
                )
        else:
            logger.warning("No tool registry - cannot pre-execute")
            return IntentResult(metadata={"error": "No tool registry"})


class IntentRouter:
    """Routes intents to appropriate handlers (Chain of Responsibility Pattern).

    This implements Chain of Responsibility:
    - Tries each handler in sequence
    - First handler that can_handle() wins
    - Extensible: just add more handlers to the chain
    """

    def __init__(self, tool_registry: Optional["ToolRegistry"] = None, context_manager=None):
        """Initialize router with handlers.

        Args:
            tool_registry: Tool registry to pass to handlers
            context_manager: ContextManager for safe caching (optional)
        """
        self.tool_registry = tool_registry
        self.context_manager = context_manager

        # Chain of handlers (order matters - first match wins)
        # Note: AnalyzeChangesHandler needs messages, created dynamically in route()
        self.handlers = [
            ExploreProjectHandler(tool_registry),
            ListFilesHandler(tool_registry),
            GitLogHandler(tool_registry),  # NEW: Git support!
        ]

    def route(
        self, intent: str, user_message: str, messages: list = None
    ) -> Optional[IntentResult]:
        """Route intent to appropriate handler.

        Args:
            intent: Intent identifier
            user_message: Original user message
            messages: Conversation history (for context-aware handlers)

        Returns:
            IntentResult if handler found, None otherwise
        """
        # For analyze_changes intent, create handler with conversation context + safe caching
        if intent == "analyze_changes":
            handler = AnalyzeChangesHandler(
                self.tool_registry,
                messages,
                context_manager=self.context_manager,  # NEW: Safe memory!
            )
            if handler.can_handle(intent):
                logger.debug("IntentRouter routing '%s' to %s", intent, handler.__class__.__name__)
                return handler.handle(user_message, intent)

        # Try other handlers
        for handler in self.handlers:
            if handler.can_handle(intent):
                logger.debug("IntentRouter routing '%s' to %s", intent, handler.__class__.__name__)
                return handler.handle(user_message, intent)

        logger.debug("IntentRouter no handler for intent '%s'", intent)
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
