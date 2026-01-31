"""Anthropic API client - thin facade over ChatPipeline.

This is kept for backward compatibility. New code should use
``ChatPipeline`` directly via ``Application``.
"""

import os
from typing import Iterator, Optional, Dict, Any, List, TYPE_CHECKING

from .logging import get_logger
from .conversation import ConversationManager
from .command_validator import create_default_validator_chain
from .response_analyzer import ResponseAnalyzer
from .auto_executor import AutoExecutor
from .pipeline.chat_pipeline import ChatPipeline

logger = get_logger(__name__)

if TYPE_CHECKING:
    from tools import ToolRegistry


class ClaudeAPIClient:
    """Thin facade that delegates to ChatPipeline.

    Supports both API keys and OAuth tokens automatically.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-5-20241022",
        max_tokens: int = 8000,
        temperature: float = 1.0,
        thinking_enabled: bool = True,
        thinking_budget: int = 10000,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_registry: Optional["ToolRegistry"] = None,
    ):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("API key or OAuth token not found")

        logger.debug("API key starts with: %s...", self.api_key[:8])

        # Create LLM client via factory (no more if/else branching)
        from client.factory import create_client, _is_oauth_token
        self.client = create_client(
            api_key=self.api_key,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            thinking_enabled=thinking_enabled,
            thinking_budget=thinking_budget,
        )
        self.backend_type = "oauth" if _is_oauth_token(self.api_key) else "api_key"
        logger.debug("backend_type=%s", self.backend_type)

        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.thinking_enabled = thinking_enabled
        self.thinking_budget = thinking_budget
        self.tools = tools or []
        self.tool_registry = tool_registry

        # Context manager
        from .memory import ContextManager
        self.context_manager = ContextManager(tool_registry)

        # Command validator
        self.command_validator = create_default_validator_chain()

        # Response analyzer
        self.response_analyzer = ResponseAnalyzer()

        # Auto executor
        self.auto_executor = AutoExecutor(tool_registry) if tool_registry else None

        # Conversation history
        self._conversation = ConversationManager()

        # Build pipeline
        self._pipeline = ChatPipeline(
            stream_fn=self._stream_fn,
            conversation=self._conversation,
            tool_registry=self.tool_registry,
            tools=self.tools,
            command_validator=self.command_validator,
            response_analyzer=self.response_analyzer,
            auto_executor=self.auto_executor,
        )

    def _stream_fn(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str],
        tools: Optional[List[Dict[str, Any]]],
        tool_choice: Optional[Dict[str, Any]],
    ) -> Iterator[Dict[str, Any]]:
        """Unified streaming function for both backends."""
        return self.client.chat_streaming(
            messages=messages,
            system=system,
            tools=tools,
            tool_choice=tool_choice,
        )

    # -- Public API (backward-compatible) --

    @property
    def messages(self) -> List[Dict[str, Any]]:
        return self._conversation.messages

    def add_message(self, role: str, content: str) -> None:
        self._conversation.add(role, content)

    def clear_history(self) -> None:
        self._conversation.clear()

    def chat(
        self,
        user_message: str,
        system: Optional[str] = None,
        tool_choice: Optional[Dict[str, Any]] = None,
    ) -> Iterator[Dict[str, Any]]:
        """Stream a response (no tool execution loop)."""
        # Add user message
        self._conversation.add("user", user_message)
        assistant_parts: List[str] = []

        for event in self._stream_fn(
            self._conversation.messages,
            system,
            self.tools if self.tools else None,
            tool_choice,
        ):
            if event.get("type") == "text":
                assistant_parts.append(event["content"])
            yield event

        final = "".join(assistant_parts)
        if final:
            self._conversation.add("assistant", final)

    def chat_with_tools(
        self, user_message: str, system: Optional[str] = None,
        max_tool_rounds: Optional[int] = None,
    ) -> Iterator[Dict[str, Any]]:
        """Stream with full tool execution loop - delegates to ChatPipeline."""
        yield from self._pipeline.chat(user_message, system, max_tool_rounds=max_tool_rounds)

    def chat_simple(self, user_message: str, system: Optional[str] = None) -> str:
        """Non-streaming chat."""
        parts = []
        for event in self.chat(user_message, system):
            if event.get("type") == "text":
                parts.append(event["content"])
        return "".join(parts)
