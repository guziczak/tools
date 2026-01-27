"""Anthropic API client with streaming and extended thinking support."""

import os
import sys
import re
from typing import Iterator, Optional, Dict, Any, List, TYPE_CHECKING
from anthropic import Anthropic
from anthropic.types import (
    Message,
    MessageStreamEvent,
    ContentBlock,
    TextBlock,
)
from tools.base import ToolResult, ToolStatus

# Logging
from .logging import get_logger
from .listing_formatter import format_listing_output

logger = get_logger(__name__)

# Import unified client for OAuth support
try:
    from .unified_client import UnifiedClaudeClient
    from .oauth_anthropic_client import (
        is_oauth_token,
    )  # FIX: Use correct import that checks sessionKey

    OAUTH_SUPPORT = True
except ImportError:
    OAUTH_SUPPORT = False
    UnifiedClaudeClient = None
    is_oauth_token = None

# Import intent handlers (STATE OF THE ART: Strategy Pattern)
try:
    from .intent_handlers import IntentRouter

    INTENT_HANDLERS_AVAILABLE = True
except ImportError:
    INTENT_HANDLERS_AVAILABLE = False
    IntentRouter = None

# Import query normalizer (Best Practices: Single Responsibility)
try:
    from .query_normalizer import QueryNormalizer

    QUERY_NORMALIZER_AVAILABLE = True
except ImportError:
    QUERY_NORMALIZER_AVAILABLE = False
    QueryNormalizer = None

# Import command validator (Best Practices: Chain of Responsibility)
try:
    from .command_validator import create_default_validator_chain

    COMMAND_VALIDATOR_AVAILABLE = True
except ImportError:
    COMMAND_VALIDATOR_AVAILABLE = False
    create_default_validator_chain = None

# Import response analyzer (Best Practices: Strategy Pattern)
try:
    from .response_analyzer import ResponseAnalyzer

    RESPONSE_ANALYZER_AVAILABLE = True
except ImportError:
    RESPONSE_ANALYZER_AVAILABLE = False
    ResponseAnalyzer = None

# Import auto executor (Best Practices: Command Pattern)
try:
    from .auto_executor import AutoExecutor

    AUTO_EXECUTOR_AVAILABLE = True
except ImportError:
    AUTO_EXECUTOR_AVAILABLE = False
    AutoExecutor = None

if TYPE_CHECKING:
    from tools import ToolRegistry
    from tools.base import ToolResult


class ClaudeAPIClient:
    """Client for interacting with Claude API.

    Supports both API keys and OAuth tokens automatically:
    - API keys (sk-ant-api03-*): Standard Anthropic API
    - OAuth tokens (sk-ant-oat01-*): Claude.ai API (like official Claude Code)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 8000,
        temperature: float = 1.0,
        thinking_enabled: bool = True,
        thinking_budget: int = 10000,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_registry: Optional["ToolRegistry"] = None,
    ):
        """Initialize Claude API client.

        Args:
            api_key: API key or OAuth token
            model: Model to use
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            thinking_enabled: Enable extended thinking
            thinking_budget: Token budget for thinking
            tools: List of tool definitions (Anthropic format)
            tool_registry: Tool registry for executing tools
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("API key or OAuth token not found")

        # Debug: token detection
        logger.debug("API key starts with: %s...", self.api_key[:20])
        logger.debug(
            "OAUTH_SUPPORT=%s, is_oauth_token=%s",
            OAUTH_SUPPORT,
            "AVAILABLE" if is_oauth_token else "NONE",
        )

        # Detect token type and initialize appropriate client
        self.is_oauth = OAUTH_SUPPORT and is_oauth_token and is_oauth_token(self.api_key)
        logger.debug("is_oauth=%s", self.is_oauth)

        if self.is_oauth:
            # Use unified client for OAuth support
            self.client = UnifiedClaudeClient(
                token=self.api_key,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                thinking_enabled=thinking_enabled,
                thinking_budget=thinking_budget,
            )
            self.backend_type = "oauth"
        else:
            # Use standard Anthropic client
            self.client = Anthropic(api_key=self.api_key)
            self.backend_type = "api_key"

        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.thinking_enabled = thinking_enabled
        self.thinking_budget = thinking_budget
        self.tools = tools or []
        self.tool_registry = tool_registry

        # Tool executor (created lazily if needed)
        self._tool_executor = None

        # Context manager (SAFE MEMORY: prevents dezinformacja like Claude Desktop)
        # Caches data with automatic verification and TTL
        self.context_manager = None
        try:
            from .memory import ContextManager

            self.context_manager = ContextManager(tool_registry)
            logger.debug("ContextManager initialized")
        except ImportError:
            logger.debug("ContextManager not available")

        # Intent router (STATE OF THE ART: Strategy Pattern with Dependency Injection)
        # Routes user intents to pre-execution handlers
        self.intent_router = None
        if INTENT_HANDLERS_AVAILABLE and tool_registry:
            self.intent_router = IntentRouter(tool_registry, context_manager=self.context_manager)
            logger.debug("IntentRouter initialized")

        # Command validator (Chain of Responsibility Pattern)
        # Validates and transforms commands for platform compatibility
        self.command_validator = None
        if COMMAND_VALIDATOR_AVAILABLE:
            self.command_validator = create_default_validator_chain()
            logger.debug("CommandValidator chain initialized")

        # Response analyzer (Strategy Pattern)
        # Detects when Claude asks user to paste command output
        self.response_analyzer = None
        if RESPONSE_ANALYZER_AVAILABLE:
            self.response_analyzer = ResponseAnalyzer()
            logger.debug("ResponseAnalyzer initialized")

        # Auto executor (Command Pattern)
        # Automatically executes commands when Claude asks for paste
        self.auto_executor = None
        if AUTO_EXECUTOR_AVAILABLE and tool_registry:
            self.auto_executor = AutoExecutor(tool_registry)
            logger.debug("AutoExecutor initialized")

        # Conversation history
        self.messages: List[Dict[str, Any]] = []

    def add_message(self, role: str, content: str) -> None:
        """Add a message to conversation history."""
        self.messages.append({"role": role, "content": content})

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.messages = []

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein (edit) distance between two strings.

        This is for fuzzy matching - catches typos like "widziszi" vs "widzisz".

        Args:
            s1: First string
            s2: Second string

        Returns:
            Minimum number of edits (insert/delete/replace) to transform s1 into s2
        """
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                # Cost of insertions, deletions, or substitutions
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def _fuzzy_match(self, query: str, triggers: List[str], max_distance: int = 2) -> bool:
        """Check if query fuzzy-matches any trigger (catches typos).

        Args:
            query: User query
            triggers: List of trigger phrases
            max_distance: Maximum Levenshtein distance to consider a match

        Returns:
            True if query is within max_distance of any trigger
        """
        query_lower = query.lower().strip()

        for trigger in triggers:
            distance = self._levenshtein_distance(query_lower, trigger)
            if distance <= max_distance:
                logger.debug(
                    "Fuzzy match: '%s' ~= '%s' (distance=%d)",
                    query_lower,
                    trigger,
                    distance,
                )
                return True

        return False

    def _get_semantic_similarity(self, query: str, reference_queries: List[str]) -> float:
        """Calculate semantic similarity using simple cosine similarity of word overlaps.

        This is a lightweight approach. For production, you'd use embeddings from
        Anthropic/OpenAI, but this is good enough for MVP.

        Args:
            query: User's query
            reference_queries: List of reference queries to compare against

        Returns:
            Max similarity score (0-1)
        """
        # Simple word overlap similarity (good enough for MVP)
        query_words = set(query.lower().split())

        max_similarity = 0.0
        for ref in reference_queries:
            ref_words = set(ref.lower().split())
            if not ref_words:
                continue

            # Jaccard similarity: intersection / union
            intersection = len(query_words & ref_words)
            union = len(query_words | ref_words)
            similarity = intersection / union if union > 0 else 0

            max_similarity = max(max_similarity, similarity)

        return max_similarity

    def _classify_query_intent(self, message: str) -> tuple[str, Optional[Dict[str, Any]]]:
        """Classify user query intent using 4-tier state-of-the-art approach:

        Tier 1: Exact trigger matching (fast path)
        Tier 1.5: Fuzzy matching (catches typos with Levenshtein distance)
        Tier 2: Semantic similarity matching (flexible)
        Tier 3: Let Claude decide (fallback)

        This combines:
        - Speed of exact matching
        - Robustness to typos (fuzzy)
        - Flexibility of semantic understanding
        - Intelligence of LLM decision making

        Args:
            message: User's message

        Returns:
            Tuple of (intent, tool_choice_config)
            - intent: "explore_project", "list_files", "general"
            - tool_choice_config: Dict for API tool_choice parameter, or None
        """
        message_lower = message.lower().strip()

        # TIER 1: Exact trigger matching (O(1) - fast path)
        # Intent: Explore project (Polish + English)
        explore_triggers = [
            "widzisz projekt",
            "czy widzisz projekt",
            "do you see project",
            "do you see the project",
            "show me the project",
            "what's in the project",
        ]

        if any(trigger in message_lower for trigger in explore_triggers):
            logger.debug("Intent tier1 match: explore_project (exact trigger)")
            return ("explore_project", {"type": "tool", "name": "bash"})

        # Intent: List files
        list_triggers = [
            "jakie pliki",
            "jakie są pliki",
            "list files",
            "show files",
            "what files",
            "list directory",
            "co tu widzisz",
            "co tutaj widzisz",
            "co tu jest",
            "co tutaj jest",
            "co jest w tym folderze",
            "co jest w tym katalogu",
            "co jest w projekcie",
            "co masz w tym folderze",
            "co masz w folderze",
            "co masz w tym katalogu",
            "co masz w katalogu",
            "co masz w projekcie",
            "co masz tu",
            "co masz tutaj",
            "pokaż zawartość",
            "pokaz zawartość",
            "pokaz zawartosc",
            "zawartość folderu",
            "zawartość katalogu",
            "zawartość projektu",
            "what's here",
            "what is here",
            "what's in this folder",
            "what is in this folder",
            "show directory contents",
            "list directory contents",
            "obczaj folder",
            "obczaj ten folder",
            "obczaj katalog",
            "obczaj ten katalog",
            "sprawdz folder",
            "sprawdź folder",
            "sprawdz katalog",
            "sprawdź katalog",
            "zobacz folder",
            "zobacz katalog",
            "pokaz folder",
            "pokaż folder",
            "pokaz katalog",
            "pokaż katalog",
            "przejrzyj folder",
            "przejrzyj katalog",
            "show folder",
            "check folder",
            "browse folder",
            "show directory",
        ]

        if any(trigger in message_lower for trigger in list_triggers):
            logger.debug("Intent tier1 match: list_files (exact trigger)")
            return ("list_files", {"type": "tool", "name": "bash"})

        # Keyword-based folder/project intents (word-order invariant)
        if QUERY_NORMALIZER_AVAILABLE:
            folder_terms = ["folder", "folderze", "katalog", "katalogu", "directory", "dir"]
            project_terms = ["projekt", "projekcie", "project"]
            location_terms = ["tu", "tutaj", "here"]
            verbs = [
                "widzisz",
                "see",
                "masz",
                "have",
                "got",
                "obczaj",
                "sprawdz",
                "sprawdź",
                "zobacz",
                "pokaz",
                "pokaż",
                "przejrzyj",
                "list",
                "show",
                "check",
                "browse",
                "open",
            ]

            # Folder listing intent
            for verb in verbs:
                for noun in folder_terms:
                    if QueryNormalizer.contains_keywords(message, [verb, noun]):
                        logger.debug("Intent tier1 match: list_files (keyword verb+noun)")
                        return ("list_files", {"type": "tool", "name": "bash"})

            for verb in verbs:
                for loc in location_terms:
                    if QueryNormalizer.contains_keywords(message, [verb, loc]):
                        logger.debug("Intent tier1 match: list_files (keyword verb+location)")
                        return ("list_files", {"type": "tool", "name": "bash"})

            # "co masz/what is" + folder/project
            if QueryNormalizer.contains_keywords(message, ["co", "folder"]) or QueryNormalizer.contains_keywords(
                message, ["co", "katalog"]
            ):
                logger.debug("Intent tier1 match: list_files (keyword co+folder)")
                return ("list_files", {"type": "tool", "name": "bash"})
            if QueryNormalizer.contains_keywords(message, ["co", "projekt"]):
                logger.debug("Intent tier1 match: explore_project (keyword co+project)")
                return ("explore_project", {"type": "tool", "name": "bash"})

            # Project exploration intent
            for verb in verbs:
                for noun in project_terms:
                    if QueryNormalizer.contains_keywords(message, [verb, noun]):
                        logger.debug("Intent tier1 match: explore_project (keyword verb+noun)")
                        return ("explore_project", {"type": "tool", "name": "bash"})

        # TIER 1.5: Fuzzy matching (catches typos like "widziszi projekt")
        # Uses Levenshtein distance - allows up to 2 character edits
        if self._fuzzy_match(message, explore_triggers, max_distance=2):
            logger.debug("Intent tier1.5 match: explore_project (fuzzy)")
            return ("explore_project", {"type": "tool", "name": "bash"})

        if self._fuzzy_match(message, list_triggers, max_distance=2):
            logger.debug("Intent tier1.5 match: list_files (fuzzy)")
            return ("list_files", {"type": "tool", "name": "bash"})

        # Intent: Git log / commits (WORD-ORDER INVARIANT!)
        # Uses QueryNormalizer for flexible keyword matching
        # "widzisz commita ostatniego?" → {widzisz, commit, ostatni} ✅
        # "ostatni commit widzisz?" → {widzisz, commit, ostatni} ✅
        if QUERY_NORMALIZER_AVAILABLE:
            # Keyword-based matching (bag of words)
            # Polish: ostatni/ostatniego + commit/commita
            if QueryNormalizer.contains_keywords(message, ["ostatni", "commit"]):
                logger.debug("Intent tier1 match: git_log (keyword: ostatni+commit)")
                return ("git_log", None)

            # English: last/recent + commit/commits
            if QueryNormalizer.contains_keywords(
                message, ["last", "commit"]
            ) or QueryNormalizer.contains_keywords(message, ["recent", "commit"]):
                logger.debug("Intent tier1 match: git_log (keyword: last/recent+commit)")
                return ("git_log", None)

            # git log / git history
            if QueryNormalizer.contains_keywords(
                message, ["git", "log"]
            ) or QueryNormalizer.contains_keywords(message, ["git", "history"]):
                logger.debug("Intent tier1 match: git_log (keyword: git+log/history)")
                return ("git_log", None)

            # Intent: Analyze changes (CONTEXT-AWARE + AGGRESSIVE!)
            # Single keyword is enough if in git context:
            # "przeanalizuj" / "analyze" / "show" / "pokaż" / "details" / "szczegóły"
            # This is INTENTIONALLY AGGRESSIVE - better false positive than false negative
            if (
                QueryNormalizer.contains_keywords(message, ["przeanalizuj"])
                or QueryNormalizer.contains_keywords(message, ["przeanalizuj", "zmiany"])
                or QueryNormalizer.contains_keywords(message, ["analyze"])
                or QueryNormalizer.contains_keywords(message, ["analyze", "changes"])
                or QueryNormalizer.contains_keywords(message, ["show", "details"])
                or QueryNormalizer.contains_keywords(message, ["pokaż"])
                or QueryNormalizer.contains_keywords(message, ["szczegóły"])
            ):
                logger.debug(
                    "Intent tier1 match: analyze_changes (keyword: przeanalizuj/analyze/show)"
                )
                return ("analyze_changes", None)
        else:
            # Fallback: exact matching (for backwards compatibility)
            git_triggers = [
                "ostatni commit",
                "widzisz ostatniego commita",
                "ostatniego commita",
                "git log",
                "git history",
                "last commit",
                "recent commits",
                "show commits",
                "commit history",
            ]

            if any(trigger in message_lower for trigger in git_triggers):
                logger.debug("Intent tier1 match: git_log (exact trigger)")
                return ("git_log", None)

            if self._fuzzy_match(message, git_triggers, max_distance=2):
                logger.debug("Intent tier1.5 match: git_log (fuzzy)")
                return ("git_log", None)

        # TIER 2: Semantic similarity matching
        # Reference queries for "explore project" intent
        explore_references = [
            "show project files",
            "what is in this project",
            "list project contents",
            "see project",
            "project structure",
        ]

        similarity = self._get_semantic_similarity(message, explore_references)
        if similarity > 0.4:  # Threshold tuned for balance
            logger.debug("Intent tier2 match: explore_project (similarity=%.2f)", similarity)
            return ("explore_project", {"type": "tool", "name": "bash"})

        # TIER 3: Let Claude decide (general query)
        logger.debug("Intent tier3: general")
        return ("general", None)

    def _prepare_tool_input(
        self, tool_name: str, tool_input: Dict[str, Any]
    ) -> tuple[Dict[str, Any], Optional[str], List[str]]:
        """Validate and normalize tool input before execution.

        Uses CommandValidator chain (Chain of Responsibility Pattern) for:
        - Blocking unsupported commands
        - Transforming Unix syntax to PowerShell
        - Fixing claude.ai virtual paths

        Args:
            tool_name: Name of the tool being called
            tool_input: Original tool input from Claude

        Returns:
            Tuple of (fixed tool input, validation_error, warnings)
        """
        # Only normalize bash tool inputs
        if tool_name != "bash" and tool_name != "bash_tool":
            return tool_input, None, []

        fixed_input = tool_input
        warnings: List[str] = []
        validation_error: Optional[str] = None

        # Validate and normalize command
        cmd = fixed_input.get("command", "")
        if cmd and self.command_validator:
            result = self.command_validator.validate(cmd)
            warnings.extend(result.warnings)

            if result.is_valid:
                if result.transformed_command and result.transformed_command != cmd:
                    logger.debug(
                        "CommandValidator transformed command. Before: %s | After: %s",
                        cmd,
                        result.transformed_command,
                    )
                    fixed_input = {**fixed_input, "command": result.transformed_command}
            else:
                logger.warning("Command blocked by validator: %s", result.error_message)
                validation_error = result.error_message

        # Normalize cwd if it uses claude.ai virtual paths
        cwd_value = fixed_input.get("cwd")
        if isinstance(cwd_value, str) and cwd_value:
            normalized_cwd = cwd_value
            if cwd_value.startswith("/home/claude"):
                suffix = cwd_value[len("/home/claude") :].lstrip("/\\")
                normalized_cwd = os.path.join(os.getcwd(), suffix)
                warnings.append("Rewrote cwd from /home/claude to local working directory")
            elif cwd_value.startswith("/mnt/user-data"):
                suffix = cwd_value[len("/mnt/user-data") :].lstrip("/\\")
                normalized_cwd = os.path.join(os.getcwd(), suffix)
                warnings.append("Rewrote cwd from /mnt/user-data to local working directory")

            if normalized_cwd != cwd_value:
                fixed_input = {**fixed_input, "cwd": normalized_cwd}

        return fixed_input, validation_error, warnings

    def chat(
        self,
        user_message: str,
        system: Optional[str] = None,
        tool_choice: Optional[Dict[str, Any]] = None,
    ) -> Iterator[Dict[str, Any]]:
        """Send a message and stream the response.

        Args:
            user_message: User's message
            system: Optional system prompt
            tool_choice: Optional pre-classified tool choice (to avoid re-classification)

        Yields:
            Events containing response chunks with type and data
        """
        # If tool_choice not provided, classify intent
        # (This happens when chat() is called directly, not via chat_with_tools())
        if tool_choice is None:
            logger.debug(
                "Classifying intent in chat() (direct call, not from chat_with_tools)"
            )
            intent, tool_choice = self._classify_query_intent(user_message)
        else:
            logger.debug("Using pre-classified tool_choice from chat_with_tools()")

        # Add user message to history (original, not preprocessed)
        self.add_message("user", user_message)

        # Use appropriate backend
        if self.backend_type == "oauth":
            # Use unified client (OAuth backend)
            logger.debug("OAuth path. Client type: %s", type(self.client).__name__)
            assistant_message = []

            for event in self.client.chat_streaming(
                messages=self.messages,
                system=system,
                tools=self.tools if self.tools else None,  # Pass tools to OAuth backend
                tool_choice=tool_choice,  # STATE OF THE ART: Force tool execution based on intent
            ):
                # Collect assistant message
                if event["type"] == "text":
                    assistant_message.append(event["content"])
                yield event

            # Add assistant response to history
            final_content = "".join(assistant_message)
            if final_content:
                self.add_message("assistant", final_content)

        else:
            # Use standard Anthropic client (API key backend)
            # Prepare request parameters
            request_params = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "messages": self.messages,
            }

            # Add system prompt if provided
            if system:
                request_params["system"] = system

            # Add extended thinking if enabled
            if self.thinking_enabled:
                request_params["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": self.thinking_budget,
                }

            # Add tools if available
            if self.tools:
                request_params["tools"] = self.tools

            # Stream the response
            assistant_message = []
            thinking_content = []
            tool_uses = []

            with self.client.messages.stream(**request_params) as stream:
                for event in stream:
                    event_data = self._process_event(event, assistant_message, thinking_content)
                    if event_data:
                        yield event_data

            # Add assistant response to history
            final_content = "".join(assistant_message)
            if final_content:
                self.add_message("assistant", final_content)

    def _process_event(
        self, event: MessageStreamEvent, assistant_message: List[str], thinking_content: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Process a streaming event.

        Returns:
            Event data dict or None if no data to yield
        """
        # Text delta (main response)
        if event.type == "content_block_delta":
            if hasattr(event.delta, "text"):
                text = event.delta.text
                assistant_message.append(text)
                return {"type": "text", "content": text}
            # Thinking delta
            elif hasattr(event.delta, "thinking"):
                thinking_text = event.delta.thinking
                thinking_content.append(thinking_text)
                return {"type": "thinking", "content": thinking_text}

        # Content block start (for thinking blocks and tool use)
        elif event.type == "content_block_start":
            if hasattr(event.content_block, "type"):
                if event.content_block.type == "thinking":
                    return {"type": "thinking_start", "content": ""}
                elif event.content_block.type == "text":
                    return {"type": "text_start", "content": ""}
                elif event.content_block.type == "tool_use":
                    # Tool use started
                    return {
                        "type": "tool_use_start",
                        "content": "",
                        "tool_name": getattr(event.content_block, "name", "unknown"),
                        "tool_id": getattr(event.content_block, "id", ""),
                    }

        # Content block stop
        elif event.type == "content_block_stop":
            return {"type": "block_stop", "content": ""}

        # Message complete
        elif event.type == "message_stop":
            return {"type": "message_done", "content": ""}

        return None

    def chat_with_tools(
        self, user_message: str, system: Optional[str] = None
    ) -> Iterator[Dict[str, Any]]:
        """Send a message with tool support (multi-turn if tools are used).

        Args:
            user_message: User's message
            system: Optional system prompt

        Yields:
            Events containing response chunks and tool execution info
        """
        logger.debug(
            "chat_with_tools called. backend_type=%s, has_tools=%s",
            self.backend_type,
            bool(self.tools),
        )

        # STATE OF THE ART: Pre-execution based on intent (Strategy Pattern)
        # Classify intent and potentially pre-execute tools before calling Claude
        intent, tool_choice = self._classify_query_intent(user_message)
        message_to_send = user_message  # Default: use original message
        intent_result = None

        # If intent router available, try to handle intent via pre-execution
        if self.intent_router and intent != "general":
            # Pass conversation history for context-aware handlers (e.g., AnalyzeChangesHandler)
            intent_result = self.intent_router.route(intent, user_message, self.messages)

            if intent_result:
                # NEW: Check if handler returned tool_results (best practice!)
                if intent_result.tool_results:
                    logger.debug(
                        "Got %d pre-executed tool results",
                        len(intent_result.tool_results),
                    )

                    # Inject tool results as fake tool_use + tool_result messages
                    # This follows Anthropic API format - zero redundancy!
                    for i, tool_res in enumerate(intent_result.tool_results):
                        # Check if it's an error
                        is_error = tool_res.get("is_error", False)

                        # Fake assistant tool call (Anthropic API format - content is list of blocks)
                        self.messages.append(
                            {
                                "role": "assistant",
                                "content": [
                                    {
                                        "type": "tool_use",
                                        "id": f"pre-exec-{i}",
                                        "name": tool_res["tool_name"],
                                        "input": tool_res["tool_input"],
                                    }
                                ],
                            }
                        )

                        # Fake user tool result (Anthropic API format)
                        tool_content = tool_res["tool_output"]
                        if is_error and not str(tool_content).lower().startswith("error"):
                            tool_content = f"Error: {tool_content}"

                        self.messages.append(
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": f"pre-exec-{i}",
                                        "content": tool_content,
                                    }
                                ],
                            }
                        )

                    # If handler says skip LLM, return result directly
                    if intent_result.skip_llm:
                        logger.debug("Handler requests skip_llm - formatting tool results")

                        if intent in ("explore_project", "list_files") and intent_result.tool_results:
                            listing_output = intent_result.tool_results[0].get("tool_output", "")
                            output_text = format_listing_output(
                                listing_output, user_message, platform=sys.platform
                            )
                        else:
                            # Format tool results as text response
                            output_text = "\n\n".join(
                                f"```\n{tr['tool_output']}\n```" for tr in intent_result.tool_results
                            )

                        yield {"type": "text", "content": output_text}
                        yield {"type": "message_done", "content": ""}
                        return

                    # Continue to LLM with original user message (not enriched!)
                    message_to_send = user_message  # ← CLEAN! No redundancy!

                    # Check if handler provided analysis instructions (e.g., AnalyzeChangesHandler)
                    if intent_result.metadata.get("analysis_instructions"):
                        # Append instructions to system prompt
                        instructions = intent_result.metadata["analysis_instructions"]
                        system = f"{system}\n\n{instructions}" if system else instructions
                        logger.debug("Added analysis instructions to system prompt")

                # DEPRECATED: Old enriched_message approach (for backwards compatibility)
                elif intent_result.enriched_message:
                    message_to_send = intent_result.enriched_message
                    logger.debug(
                        "Message enriched with pre-executed tool results (deprecated approach)"
                    )

                    # If handler says skip LLM, return result directly
                    if intent_result.skip_llm:
                        logger.debug("Handler requests skip_llm - returning result directly")
                        yield {"type": "text", "content": intent_result.enriched_message}
                        yield {"type": "message_done", "content": ""}
                        return

        # Fallback: direct local execution for simple listing intents
        if intent in ("explore_project", "list_files") and self.tool_registry:
            # If no handler produced tool results, execute directly to avoid LLM guesswork
            if not intent_result or not intent_result.tool_results:
                is_windows = sys.platform.startswith("win")
                list_cmd = "dir" if is_windows else "ls"
                result = self.tool_registry.execute_tool("bash", command=list_cmd)

                if result.status.value == "success":
                    output_text = format_listing_output(
                        result.output, user_message, platform=sys.platform
                    )
                else:
                    output_text = f"Error: {result.error or 'Unknown error'}"

                # Record in history to keep context
                self.add_message("user", user_message)
                self.add_message("assistant", output_text)

                yield {"type": "text", "content": output_text}
                yield {"type": "message_done", "content": ""}
                return

        # OAuth backend - tool support with local execution
        if self.backend_type == "oauth":
            logger.debug("Entering OAuth tool execution loop")
            # Multi-turn tool calling loop
            max_tool_rounds = 5
            tool_round = 0

            while tool_round < max_tool_rounds:
                # Stream response and collect tool calls
                tool_blocks = []
                assistant_text = []  # Track assistant response for all rounds

                # First round: use chat() which adds user message to history
                # Subsequent rounds: use client directly with existing messages (including tool results)
                if tool_round == 0:
                    # Add user message via chat() (use enriched message if available)
                    # PASS tool_choice to avoid re-classification! ✅
                    events = self.chat(message_to_send, system, tool_choice=tool_choice)
                else:
                    # Use client directly with messages that already include tool results
                    events = self.client.chat_streaming(
                        messages=self.messages,
                        system=system,
                        tools=self.tools if self.tools else None,
                    )

                for event in events:
                    # Collect tool blocks (EXTEND instead of overwrite!)
                    if event.get("type") == "tool_calls_complete":
                        tool_blocks.extend(event.get("tool_blocks", []))

                    # Collect ALL assistant text (for paste detection + history)
                    if event.get("type") == "text":
                        assistant_text.append(event.get("content", ""))

                    # Yield event to user
                    yield event

                # Add assistant response to history (for ALL rounds if not added by chat())
                # Round 0: chat() already added to history
                # Round 1+: we need to add manually
                if tool_round > 0 and assistant_text:
                    self.add_message("assistant", "".join(assistant_text))

                # AUTO-EXECUTION: Check if Claude asked user to paste command output
                # This is STATE OF THE ART - automatically execute instead of asking user
                if self.response_analyzer and self.auto_executor and assistant_text:
                    full_response = "".join(assistant_text)
                    paste_request = self.response_analyzer.analyze(full_response)

                    if paste_request.detected and paste_request.command:
                        logger.debug(
                            "AutoExecutor detected paste request for: %s",
                            paste_request.command,
                        )

                        # Check if safe to auto-execute
                        if self.auto_executor.should_auto_execute(paste_request.command):
                            # Execute command automatically
                            exec_result = self.auto_executor.execute(paste_request.command)

                            # Create follow-up message with result
                            followup = self.auto_executor.create_followup_message(
                                paste_request.command, exec_result
                            )

                            # Add to messages as if user sent it
                            self.add_message("user", followup)

                            # Continue loop - Claude will see the result and respond
                            logger.debug("AutoExecutor continuing conversation with command result")
                            tool_round -= 1  # Don't count this as a tool round
                            continue
                        else:
                            logger.warning(
                                "AutoExecutor blocked dangerous command: %s",
                                paste_request.command,
                            )

                # Check if Claude requested tools
                if not tool_blocks:
                    # DEBUG: Show assistant_text content
                    logger.debug("assistant_text length: %d", len(assistant_text))

                    # No tools requested, check if Claude actually responded with text
                    if not assistant_text and tool_round > 0:
                        # Claude only sent thinking, no text response!
                        # This is a claude.ai bug - force a text response
                        logger.warning(
                            "No text response in round %d, forcing text response", tool_round
                        )

                        # Send a VERY explicit follow-up to force text
                        self.add_message(
                            "user",
                            "Please provide your complete answer in text (not just thinking).",
                        )

                        # Continue loop to get text response
                        tool_round += 1
                        if tool_round >= max_tool_rounds:
                            logger.error("Max rounds reached, giving up")
                            break
                        continue

                    # No tools and we have text, done
                    logger.debug("No tools in round %d, exiting loop", tool_round)
                    break

                # Execute tools locally
                tool_round += 1
                logger.debug(
                    "Starting tool round %d with %d tools", tool_round, len(tool_blocks)
                )

                yield {"type": "tool_round_start", "content": f"Tool execution round {tool_round}"}

                tool_results = []
                executed_tool_uses = []
                tool_execution_records = []
                for tool_block in tool_blocks:
                    tool_name = tool_block.get("name", "")
                    tool_id = tool_block.get("id", "")
                    tool_input = tool_block.get("input", {})

                    logger.debug(
                        "Executing tool: %s with input keys: %s",
                        tool_name,
                        list(tool_input.keys()),
                    )

                    # Validate and normalize tool input before execution
                    tool_input, validation_error, warnings = self._prepare_tool_input(
                        tool_name, tool_input
                    )

                    executed_tool_uses.append(
                        {
                            "type": "tool_use",
                            "id": tool_id,
                            "name": tool_name,
                            "input": tool_input,
                        }
                    )

                    # Execute tool locally (registry handles alias mapping)
                    if validation_error:
                        result = ToolResult(
                            status=ToolStatus.ERROR,
                            output="",
                            error=validation_error,
                        )
                    elif self.tool_registry:
                        result = self.tool_registry.execute_tool(tool_name, **tool_input)
                    else:
                        result = ToolResult(
                            status=ToolStatus.ERROR,
                            output="",
                            error="Tool registry not available",
                        )

                    logger.debug(
                        "Tool result: status=%s, output_len=%d",
                        result.status.value,
                        len(result.output) if result.output else 0,
                    )

                    # Yield execution event
                    yield {
                        "type": "tool_execute",
                        "tool_name": tool_name,
                        "tool_input": tool_input,
                        "result": result,
                        "content": "",
                    }

                    tool_execution_records.append(
                        {
                            "tool_name": tool_name,
                            "tool_id": tool_id,
                            "tool_input": tool_input,
                            "result": result,
                            "warnings": warnings,
                        }
                    )

                    # Format result for claude.ai
                    if result.status.value == "success":
                        tool_content = result.output
                    else:
                        error_text = result.error or "Unknown error"
                        if result.output and result.output != "(no output)":
                            tool_content = f"Error: {error_text}\n{result.output}"
                        else:
                            tool_content = f"Error: {error_text}"

                    if warnings:
                        warning_text = "Note: " + " | ".join(warnings)
                        tool_content = f"{warning_text}\n{tool_content}"

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": tool_content,
                        }
                    )

                # If all tools failed, return a direct error response (no hallucinations)
                failed_tools = [
                    record
                    for record in tool_execution_records
                    if record["result"].status == ToolStatus.ERROR
                ]
                if failed_tools and len(failed_tools) == len(tool_execution_records):
                    error_lines = [
                        f"- {record['tool_name']}: {record['result'].error or 'Unknown error'}"
                        for record in failed_tools
                    ]
                    error_text = (
                        "Tool execution failed:\n"
                        + "\n".join(error_lines)
                        + "\n\nPlease adjust the request or paths and try again."
                    )
                    self.add_message("assistant", error_text)
                    yield {"type": "text", "content": error_text}
                    yield {"type": "message_done", "content": ""}
                    return

                # Add assistant message with tool_use to history (use executed inputs)
                self.messages.append({"role": "assistant", "content": executed_tool_uses})

                # Add tool results as user message with a concise follow-up prompt
                tool_results_with_prompt = tool_results.copy()

                if failed_tools:
                    error_summary = "\n".join(
                        f"- {record['tool_name']}: {record['result'].error or 'Unknown error'}"
                        for record in failed_tools
                    )
                    tool_results_with_prompt.append(
                        {
                            "type": "text",
                            "text": (
                                "One or more tools failed:\n"
                                f"{error_summary}\n"
                                "Acknowledge the errors and ask for the next step."
                            ),
                        }
                    )

                tool_results_with_prompt.append(
                    {
                        "type": "text",
                        "text": (
                            "Tool results are provided above. "
                            "Please answer the original question in plain text. "
                            "If any result contains an error, acknowledge it and ask for the next step."
                        ),
                    }
                )
                self.messages.append({"role": "user", "content": tool_results_with_prompt})

                yield {
                    "type": "tool_round_complete",
                    "content": f"Completed {len(tool_results)} tool(s)",
                }

                # Continue loop - next iteration will send tool results to Claude
                user_message = ""  # Don't send user message again

            if tool_round >= max_tool_rounds:
                yield {
                    "type": "error",
                    "content": f"Maximum tool rounds ({max_tool_rounds}) reached",
                }

            return

        # API key backend - full tool support
        # Lazy import to avoid circular dependency
        from .tool_executor import ToolExecutor

        # Create tool executor if we have tools
        if self.tool_registry and self.tools:
            # Add user message for tool executor path
            self.add_message("user", user_message)

            if not self._tool_executor:
                self._tool_executor = ToolExecutor(self.tool_registry, self.client)

            # Use tool executor for full loop
            for event in self._tool_executor.chat_with_tools(
                messages=self.messages,
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system,
                tools=self.tools,
                thinking_enabled=self.thinking_enabled,
                thinking_budget=self.thinking_budget,
            ):
                yield event

            # Tool executor handles message history internally
            # We don't update self.messages here as it's complex
        else:
            # No tools, use regular chat (it will add message to history)
            for event in self.chat(user_message, system):
                yield event

    def chat_simple(self, user_message: str, system: Optional[str] = None) -> str:
        """Send a message and get complete response (non-streaming).

        Args:
            user_message: User's message
            system: Optional system prompt

        Returns:
            Complete assistant response
        """
        response_parts = []

        for event in self.chat(user_message, system):
            if event["type"] == "text":
                response_parts.append(event["content"])

        return "".join(response_parts)
