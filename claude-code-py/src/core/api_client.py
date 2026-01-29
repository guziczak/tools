"""Anthropic API client with streaming and extended thinking support."""

import os
import sys
from typing import Iterator, Optional, Dict, Any, List, TYPE_CHECKING
from anthropic import Anthropic
from anthropic.types import MessageStreamEvent
from tools.base import ToolResult, ToolStatus

# Logging
from .logging import get_logger
from .listing_formatter import format_listing_output
from .intent.classifier import ConfigDrivenClassifier
from .conversation import ConversationManager

logger = get_logger(__name__)

from .unified_client import UnifiedClaudeClient
from .oauth_anthropic_client import is_oauth_token
from .intent_handlers import IntentRouter
from .command_validator import create_default_validator_chain
from .response_analyzer import ResponseAnalyzer
from .auto_executor import AutoExecutor

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
        self.is_oauth = is_oauth_token(self.api_key) if is_oauth_token else False
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

        # Context manager
        from .memory import ContextManager
        self.context_manager = ContextManager(tool_registry)

        # Intent router
        self.intent_router = IntentRouter(tool_registry, context_manager=self.context_manager) if tool_registry else None

        # Config-driven intent classifier (SINGLE source of truth: intent_patterns.json)
        self._config_classifier = ConfigDrivenClassifier()

        # Command validator
        self.command_validator = create_default_validator_chain()

        # Response analyzer
        self.response_analyzer = ResponseAnalyzer()

        # Auto executor
        self.auto_executor = AutoExecutor(tool_registry) if tool_registry else None

        # Conversation history (bounded sliding window)
        self._conversation = ConversationManager()

    @property
    def messages(self) -> List[Dict[str, Any]]:
        """Legacy accessor for conversation messages."""
        return self._conversation.messages

    def add_message(self, role: str, content: str) -> None:
        """Add a message to conversation history."""
        self._conversation.add(role, content)

    def clear_history(self) -> None:
        """Clear conversation history."""
        self._conversation.clear()

    def _classify_query_intent(self, message: str) -> tuple[str, Optional[Dict[str, Any]]]:
        """Classify user query intent using config-driven classifier.

        All triggers are defined in ``intent_patterns.json`` - zero hardcoded lists.

        Args:
            message: User's message

        Returns:
            Tuple of (intent, tool_choice_config)
        """
        return self._config_classifier.classify(message)

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

        # OAuth backend - tool support via unified tool loop
        if self.backend_type == "oauth":
            from .pipeline.tool_loop import run_tool_loop

            logger.debug("Entering OAuth tool execution loop")

            def _oauth_stream(round_num: int):
                if round_num == 0:
                    return self.chat(message_to_send, system, tool_choice=tool_choice)
                return self.client.chat_streaming(
                    messages=self.messages,
                    system=system,
                    tools=self.tools if self.tools else None,
                )

            yield from run_tool_loop(
                stream_fn=_oauth_stream,
                messages=self.messages,
                tool_registry=self.tool_registry,
                command_validator=self.command_validator,
                response_analyzer=self.response_analyzer,
                auto_executor=self.auto_executor,
                add_message=self.add_message,
            )
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
