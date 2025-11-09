"""Tool execution coordinator for handling Claude's tool requests."""

from typing import Dict, Any, List, Optional, Iterator
from anthropic import Anthropic
from anthropic.types import Message, MessageStreamEvent, ToolUseBlock, TextBlock

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools import ToolRegistry


class ToolExecutor:
    """Handles tool execution and multi-turn tool calling with Claude."""

    def __init__(self, tool_registry: ToolRegistry, client: Anthropic):
        """Initialize tool executor.

        Args:
            tool_registry: Registry of available tools
            client: Anthropic API client
        """
        self.tool_registry = tool_registry
        self.client = client

    def execute_tools_from_message(self, message: Message) -> List[Dict[str, Any]]:
        """Execute all tool uses in a message.

        Args:
            message: Claude's message containing tool uses

        Returns:
            List of tool results in Anthropic format
        """
        tool_results = []

        for content_block in message.content:
            if content_block.type == "tool_use":
                # Execute this tool
                tool_name = content_block.name
                tool_input = content_block.input
                tool_id = content_block.id

                # Execute via registry
                result = self.tool_registry.execute_tool(tool_name, **tool_input)

                # Convert to Anthropic format
                tool_result = {
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": (
                        result.output
                        if result.status.value == "success"
                        else f"Error: {result.error}"
                    ),
                }

                # Add to results
                tool_results.append(
                    {
                        "tool_name": tool_name,
                        "tool_id": tool_id,
                        "input": tool_input,
                        "result": result,
                        "anthropic_result": tool_result,
                    }
                )

        return tool_results

    def has_tool_use(self, message: Message) -> bool:
        """Check if message contains tool use blocks.

        Args:
            message: Claude's message

        Returns:
            True if message contains tool uses
        """
        for content_block in message.content:
            if content_block.type == "tool_use":
                return True
        return False

    def chat_with_tools(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        max_tokens: int,
        temperature: float,
        system: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        thinking_enabled: bool = False,
        thinking_budget: int = 10000,
        max_tool_rounds: int = 5,
    ) -> Iterator[Dict[str, Any]]:
        """Chat with Claude with automatic tool execution.

        This handles the full tool calling loop:
        1. Send user message
        2. Claude responds (might include tool use)
        3. Execute tools
        4. Send results back to Claude
        5. Claude responds with final answer
        6. Repeat if Claude wants to use more tools

        Args:
            messages: Conversation history
            model: Model to use
            max_tokens: Max tokens for response
            temperature: Sampling temperature
            system: System prompt
            tools: Tool definitions
            thinking_enabled: Enable extended thinking
            thinking_budget: Thinking token budget
            max_tool_rounds: Maximum number of tool execution rounds

        Yields:
            Events with type and content
        """
        current_messages = messages.copy()
        tool_round = 0

        while tool_round < max_tool_rounds:
            # Prepare request
            request_params = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": current_messages,
            }

            if system:
                request_params["system"] = system

            if tools:
                request_params["tools"] = tools

            if thinking_enabled:
                request_params["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}

            # Stream the response and collect events
            message = None
            current_tool_uses = []

            with self.client.messages.stream(**request_params) as stream:
                for event in stream:
                    # Handle different event types
                    if event.type == "content_block_start":
                        if hasattr(event, "content_block"):
                            block = event.content_block
                            if block.type == "thinking":
                                yield {"type": "thinking_start", "content": ""}
                            elif block.type == "text":
                                yield {"type": "text_start", "content": ""}
                            elif block.type == "tool_use":
                                # Tool use detected
                                current_tool_uses.append(
                                    {
                                        "id": getattr(block, "id", ""),
                                        "name": getattr(block, "name", "unknown"),
                                        "input": {},
                                    }
                                )
                                yield {
                                    "type": "tool_use_detected",
                                    "tool_name": getattr(block, "name", "unknown"),
                                    "content": "",
                                }

                    elif event.type == "content_block_delta":
                        if hasattr(event, "delta"):
                            delta = event.delta
                            if hasattr(delta, "type"):
                                if delta.type == "text_delta":
                                    text = getattr(delta, "text", "")
                                    yield {"type": "text", "content": text}
                                elif delta.type == "thinking_delta":
                                    thinking = getattr(delta, "thinking", "")
                                    yield {"type": "thinking", "content": thinking}
                                elif delta.type == "input_json_delta":
                                    # Tool input being streamed (we'll get full input at end)
                                    pass

                    elif event.type == "content_block_stop":
                        yield {"type": "block_stop", "content": ""}

                    elif event.type == "message_stop":
                        # Get final message with complete tool_use blocks
                        message = stream.get_final_message()

            # Check if Claude wants to use tools
            if not message or not self.has_tool_use(message):
                # No tools requested, we're done
                yield {"type": "message_complete", "content": ""}
                break

            # Execute tools
            tool_round += 1
            yield {"type": "tool_round_start", "content": f"Tool execution round {tool_round}"}

            tool_results = self.execute_tools_from_message(message)

            # Yield tool execution events
            for tool_result in tool_results:
                yield {
                    "type": "tool_execute",
                    "tool_name": tool_result["tool_name"],
                    "tool_input": tool_result["input"],
                    "result": tool_result["result"],
                    "content": "",
                }

            # Add assistant message (with tool uses) to history
            current_messages.append({"role": "assistant", "content": message.content})

            # Add tool results to history
            current_messages.append(
                {"role": "user", "content": [tr["anthropic_result"] for tr in tool_results]}
            )

            yield {
                "type": "tool_round_complete",
                "content": f"Completed {len(tool_results)} tool(s)",
            }

            # Continue loop to get Claude's response to the tool results

        if tool_round >= max_tool_rounds:
            yield {"type": "error", "content": f"Maximum tool rounds ({max_tool_rounds}) reached"}
