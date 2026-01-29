"""ChatPipeline - single entry point for all chat interactions.

Replaces the dual ``chat()`` / ``chat_with_tools()`` methods in ``ClaudeAPIClient``
with a single ``ChatPipeline.chat()`` that orchestrates:

1. Intent classification
2. Pre-execution via IntentRouter
3. LLM streaming
4. Tool execution loop
5. Post-response auto-execution
"""

from __future__ import annotations

import sys
from typing import Any, Dict, Iterator, List, Optional, TYPE_CHECKING

from core.logging import get_logger
from core.intent.classifier import ConfigDrivenClassifier
from core.conversation import ConversationManager
from core.listing_formatter import format_listing_output
from .tool_loop import run_tool_loop

if TYPE_CHECKING:
    from tools import ToolRegistry
    from core.intent_handlers import IntentRouter
    from core.command_validator import CommandValidatorChain
    from core.response_analyzer import ResponseAnalyzer
    from core.auto_executor import AutoExecutor

logger = get_logger(__name__)


class ChatPipeline:
    """Orchestrates the full chat flow: classify -> pre-exec -> LLM -> tool loop.

    This replaces ``ClaudeAPIClient.chat_with_tools()`` and ``ClaudeAPIClient.chat()``.
    """

    def __init__(
        self,
        *,
        stream_fn,
        conversation: ConversationManager,
        classifier: ConfigDrivenClassifier,
        tool_registry: Optional["ToolRegistry"] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        intent_router: Optional["IntentRouter"] = None,
        command_validator: Optional[Any] = None,
        response_analyzer: Optional["ResponseAnalyzer"] = None,
        auto_executor: Optional["AutoExecutor"] = None,
    ) -> None:
        """
        Args:
            stream_fn: Callable ``(messages, system, tools, tool_choice) -> Iterator[event]``.
            conversation: Conversation history manager.
            classifier: Intent classifier.
            tool_registry: Registry for executing tools.
            tools: Tool definitions for the API.
            intent_router: Routes intents to pre-execution handlers.
            command_validator: Validates/transforms commands.
            response_analyzer: Detects paste-request patterns.
            auto_executor: Auto-executes safe commands.
        """
        self._stream_fn = stream_fn
        self._conversation = conversation
        self._classifier = classifier
        self._tool_registry = tool_registry
        self._tools = tools or []
        self._intent_router = intent_router
        self._command_validator = command_validator
        self._response_analyzer = response_analyzer
        self._auto_executor = auto_executor

    def chat(
        self,
        user_message: str,
        system: Optional[str] = None,
    ) -> Iterator[Dict[str, Any]]:
        """Run the full chat pipeline.

        Args:
            user_message: User's message.
            system: Optional system prompt.

        Yields:
            Stream events.
        """
        # 1. Classify intent
        intent, tool_choice = self._classifier.classify(user_message)
        message_to_send = user_message

        # 2. Pre-execution via IntentRouter
        if self._intent_router and intent != "general":
            pre_result = self._intent_router.route(
                intent, user_message, self._conversation.messages
            )
            if pre_result:
                result = self._handle_pre_execution(
                    pre_result, intent, user_message, system
                )
                if result is not None:
                    yield from result
                    return
                # If result is None, continue to LLM with pre-exec data injected

                # Check for analysis instructions
                if pre_result.metadata.get("analysis_instructions"):
                    instructions = pre_result.metadata["analysis_instructions"]
                    system = f"{system}\n\n{instructions}" if system else instructions

        # 3. Direct local execution for listing intents without pre-exec results
        if intent in ("explore_project", "list_files") and self._tool_registry:
            direct_result = self._direct_listing(user_message)
            if direct_result is not None:
                yield from direct_result
                return

        # 4. Stream from LLM with tool loop
        if self._tool_registry and self._tools:
            yield from self._stream_with_tools(message_to_send, system, tool_choice)
        else:
            yield from self._stream_simple(message_to_send, system, tool_choice)

    def _handle_pre_execution(self, intent_result, intent, user_message, system):
        """Handle pre-executed intent results. Returns iterator or None."""
        if intent_result.tool_results:
            # Inject tool results into conversation
            for i, tool_res in enumerate(intent_result.tool_results):
                is_error = tool_res.get("is_error", False)
                self._conversation.add_raw({
                    "role": "assistant",
                    "content": [{
                        "type": "tool_use",
                        "id": f"pre-exec-{i}",
                        "name": tool_res["tool_name"],
                        "input": tool_res["tool_input"],
                    }],
                })
                tool_content = tool_res["tool_output"]
                if is_error and not str(tool_content).lower().startswith("error"):
                    tool_content = f"Error: {tool_content}"
                self._conversation.add_raw({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": f"pre-exec-{i}",
                        "content": tool_content,
                    }],
                })

            if intent_result.skip_llm:
                return self._format_skip_llm(intent_result, intent, user_message)

        elif intent_result.enriched_message:
            if intent_result.skip_llm:
                def _gen():
                    yield {"type": "text", "content": intent_result.enriched_message}
                    yield {"type": "message_done", "content": ""}
                return _gen()

        return None

    def _format_skip_llm(self, intent_result, intent, user_message):
        """Format skip-LLM response."""
        if intent in ("explore_project", "list_files") and intent_result.tool_results:
            listing_output = intent_result.tool_results[0].get("tool_output", "")
            output_text = format_listing_output(
                listing_output, user_message, platform=sys.platform
            )
        else:
            output_text = "\n\n".join(
                f"```\n{tr['tool_output']}\n```" for tr in intent_result.tool_results
            )

        def _gen():
            yield {"type": "text", "content": output_text}
            yield {"type": "message_done", "content": ""}
        return _gen()

    def _direct_listing(self, user_message):
        """Execute listing directly without LLM."""
        is_windows = sys.platform.startswith("win")
        list_cmd = "dir" if is_windows else "ls"
        result = self._tool_registry.execute_tool("bash", command=list_cmd)

        if result.status.value == "success":
            output_text = format_listing_output(
                result.output, user_message, platform=sys.platform
            )
        else:
            output_text = f"Error: {result.error or 'Unknown error'}"

        self._conversation.add("user", user_message)
        self._conversation.add("assistant", output_text)

        def _gen():
            yield {"type": "text", "content": output_text}
            yield {"type": "message_done", "content": ""}
        return _gen()

    def _stream_simple(self, user_message, system, tool_choice):
        """Stream without tool support."""
        self._conversation.add("user", user_message)
        assistant_parts = []

        for event in self._stream_fn(
            self._conversation.messages, system, None, tool_choice
        ):
            if event.get("type") == "text":
                assistant_parts.append(event["content"])
            yield event

        final = "".join(assistant_parts)
        if final:
            self._conversation.add("assistant", final)

    def _stream_with_tools(self, user_message, system, tool_choice):
        """Stream with tool execution loop."""
        self._conversation.add("user", user_message)

        first_round_done = False

        def _stream_round(round_num):
            nonlocal first_round_done
            if round_num == 0:
                first_round_done = True
                return self._stream_fn(
                    self._conversation.messages, system, self._tools, tool_choice
                )
            return self._stream_fn(
                self._conversation.messages, system, self._tools, None
            )

        yield from run_tool_loop(
            stream_fn=_stream_round,
            messages=self._conversation.messages,
            tool_registry=self._tool_registry,
            command_validator=self._command_validator,
            response_analyzer=self._response_analyzer,
            auto_executor=self._auto_executor,
            add_message=self._conversation.add,
        )
