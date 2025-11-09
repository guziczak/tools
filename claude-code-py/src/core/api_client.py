"""Anthropic API client with streaming and extended thinking support."""

import os
from typing import Iterator, Optional, Dict, Any, List, TYPE_CHECKING
from anthropic import Anthropic
from anthropic.types import (
    Message,
    MessageStreamEvent,
    ContentBlock,
    TextBlock,
)

# Import unified client for OAuth support
try:
    from .unified_client import UnifiedClaudeClient
    from .claude_ai_client import is_oauth_token
    OAUTH_SUPPORT = True
except ImportError:
    OAUTH_SUPPORT = False
    UnifiedClaudeClient = None
    is_oauth_token = None

if TYPE_CHECKING:
    from tools import ToolRegistry


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

        # Detect token type and initialize appropriate client
        self.is_oauth = OAUTH_SUPPORT and is_oauth_token and is_oauth_token(self.api_key)

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

        # Conversation history
        self.messages: List[Dict[str, Any]] = []

    def add_message(self, role: str, content: str) -> None:
        """Add a message to conversation history."""
        self.messages.append({"role": role, "content": content})

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.messages = []

    def chat(self, user_message: str, system: Optional[str] = None) -> Iterator[Dict[str, Any]]:
        """Send a message and stream the response.

        Args:
            user_message: User's message
            system: Optional system prompt

        Yields:
            Events containing response chunks with type and data
        """
        # Add user message to history
        self.add_message("user", user_message)

        # Use appropriate backend
        if self.backend_type == "oauth":
            # Use unified client (OAuth backend)
            assistant_message = []

            for event in self.client.chat_streaming(
                messages=self.messages,
                system=system,
                tools=self.tools if self.tools else None,  # Pass tools to OAuth backend
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
                    "budget_tokens": self.thinking_budget
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
        self,
        event: MessageStreamEvent,
        assistant_message: List[str],
        thinking_content: List[str]
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
                return {
                    "type": "text",
                    "content": text
                }
            # Thinking delta
            elif hasattr(event.delta, "thinking"):
                thinking_text = event.delta.thinking
                thinking_content.append(thinking_text)
                return {
                    "type": "thinking",
                    "content": thinking_text
                }

        # Content block start (for thinking blocks and tool use)
        elif event.type == "content_block_start":
            if hasattr(event.content_block, "type"):
                if event.content_block.type == "thinking":
                    return {
                        "type": "thinking_start",
                        "content": ""
                    }
                elif event.content_block.type == "text":
                    return {
                        "type": "text_start",
                        "content": ""
                    }
                elif event.content_block.type == "tool_use":
                    # Tool use started
                    return {
                        "type": "tool_use_start",
                        "content": "",
                        "tool_name": getattr(event.content_block, "name", "unknown"),
                        "tool_id": getattr(event.content_block, "id", "")
                    }

        # Content block stop
        elif event.type == "content_block_stop":
            return {
                "type": "block_stop",
                "content": ""
            }

        # Message complete
        elif event.type == "message_stop":
            return {
                "type": "message_done",
                "content": ""
            }

        return None

    def chat_with_tools(self, user_message: str, system: Optional[str] = None) -> Iterator[Dict[str, Any]]:
        """Send a message with tool support (multi-turn if tools are used).

        Args:
            user_message: User's message
            system: Optional system prompt

        Yields:
            Events containing response chunks and tool execution info
        """
        # OAuth backend - simplified tool support (experimental)
        if self.backend_type == "oauth":
            # For now, just use chat() which passes tools to claude.ai
            # Tool execution will be handled in a simplified way
            # TODO: Implement full multi-turn tool calling loop for OAuth
            for event in self.chat(user_message, system):
                # Detect tool use events
                if event.get("type") == "tool_use_start":
                    tool_name = event.get("tool_name", "unknown")
                    tool_id = event.get("tool_id", "")

                    # Notify user that tool was requested
                    yield {
                        "type": "tool_use_detected",
                        "tool_name": tool_name,
                        "content": f"Claude wants to use tool: {tool_name}"
                    }

                    # TODO: Execute tool locally and send results back
                    # For now, just pass through the event

                yield event
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
                thinking_budget=self.thinking_budget
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
