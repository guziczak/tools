"""ChatPipeline - single entry point for all chat interactions.

Sends every user message to claude.ai (Sonnet) with tools.
Claude decides what to do - no local intent classification.
"""

from __future__ import annotations

from typing import Any, Dict, Iterator, List, Optional, TYPE_CHECKING

from core.logging import get_logger
from core.conversation import ConversationManager
from .tool_loop import run_tool_loop

if TYPE_CHECKING:
    from tools import ToolRegistry
    from core.command_validator import CommandValidatorChain
    from core.response_analyzer import ResponseAnalyzer
    from core.auto_executor import AutoExecutor

logger = get_logger(__name__)


class ChatPipeline:
    """Orchestrates the full chat flow: LLM -> tool loop.

    Every message goes to claude.ai. No local intent classification.
    """

    def __init__(
        self,
        *,
        stream_fn,
        conversation: ConversationManager,
        tool_registry: Optional["ToolRegistry"] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        command_validator: Optional[Any] = None,
        response_analyzer: Optional["ResponseAnalyzer"] = None,
        auto_executor: Optional["AutoExecutor"] = None,
    ) -> None:
        self._stream_fn = stream_fn
        self._conversation = conversation
        self._tool_registry = tool_registry
        self._tools = tools or []
        self._command_validator = command_validator
        self._response_analyzer = response_analyzer
        self._auto_executor = auto_executor

    def chat(
        self,
        user_message: str,
        system: Optional[str] = None,
        max_tool_rounds: Optional[int] = None,
    ) -> Iterator[Dict[str, Any]]:
        """Run the full chat pipeline.

        Args:
            user_message: The user's message.
            system: System prompt.
            max_tool_rounds: Override for max tool execution rounds.

        Yields:
            Stream events.
        """
        if self._tool_registry and self._tools:
            yield from self._stream_with_tools(user_message, system, max_tool_rounds)
        else:
            yield from self._stream_simple(user_message, system)

    def _stream_simple(self, user_message, system):
        """Stream without tool support."""
        self._conversation.add("user", user_message)
        assistant_parts = []

        for event in self._stream_fn(
            self._conversation.messages, system, None, None
        ):
            if event.get("type") == "text":
                assistant_parts.append(event["content"])
            yield event

        final = "".join(assistant_parts)
        if final:
            self._conversation.add("assistant", final)

    def _stream_with_tools(self, user_message, system, max_tool_rounds=None):
        """Stream with tool execution loop."""
        self._conversation.add("user", user_message)

        def _stream_round(round_num):
            return self._stream_fn(
                self._conversation.messages, system, self._tools, None
            )

        def _stream_no_tools():
            return self._stream_fn(
                self._conversation.messages, system, None, None
            )

        kwargs = dict(
            stream_fn=_stream_round,
            stream_fn_no_tools=_stream_no_tools,
            messages=self._conversation.messages,
            tool_registry=self._tool_registry,
            command_validator=self._command_validator,
            response_analyzer=self._response_analyzer,
            auto_executor=self._auto_executor,
            add_message=self._conversation.add,
        )
        if max_tool_rounds is not None:
            kwargs["max_rounds"] = max_tool_rounds

        yield from run_tool_loop(**kwargs)
