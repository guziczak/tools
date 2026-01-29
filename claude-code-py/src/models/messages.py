"""Message type definitions replacing Dict[str, Any] throughout the codebase."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


@dataclass(frozen=True)
class ToolCall:
    """A tool invocation request from the assistant.

    Attributes:
        id: Unique tool use ID (e.g., "toolu_01abc...")
        name: Tool name (e.g., "bash", "read_file")
        input: Tool parameters
    """

    id: str
    name: str
    input: Dict[str, Any] = field(default_factory=dict)

    def to_api_dict(self) -> Dict[str, Any]:
        """Convert to Anthropic API format."""
        return {
            "type": "tool_use",
            "id": self.id,
            "name": self.name,
            "input": self.input,
        }


@dataclass(frozen=True)
class ToolResultMessage:
    """A tool execution result sent back to the API.

    Attributes:
        tool_use_id: ID of the tool_use this is a result for
        content: Tool output (text)
        is_error: Whether the tool execution failed
    """

    tool_use_id: str
    content: str
    is_error: bool = False

    def to_api_dict(self) -> Dict[str, Any]:
        """Convert to Anthropic API format."""
        result: Dict[str, Any] = {
            "type": "tool_result",
            "tool_use_id": self.tool_use_id,
            "content": self.content,
        }
        if self.is_error:
            result["is_error"] = True
        return result


@dataclass
class Message:
    """A conversation message (user or assistant).

    Attributes:
        role: "user" or "assistant"
        content: Message content - string or list of content blocks
    """

    role: str
    content: Union[str, List[Dict[str, Any]]]

    def to_api_dict(self) -> Dict[str, Any]:
        """Convert to Anthropic API format."""
        return {"role": self.role, "content": self.content}

    @classmethod
    def user(cls, content: str) -> Message:
        """Create a user message."""
        return cls(role="user", content=content)

    @classmethod
    def assistant(cls, content: str) -> Message:
        """Create an assistant message."""
        return cls(role="assistant", content=content)

    @classmethod
    def tool_use(cls, tool_calls: List[ToolCall]) -> Message:
        """Create an assistant message with tool use blocks."""
        return cls(
            role="assistant",
            content=[tc.to_api_dict() for tc in tool_calls],
        )

    @classmethod
    def tool_result(cls, results: List[ToolResultMessage]) -> Message:
        """Create a user message with tool results."""
        return cls(
            role="user",
            content=[r.to_api_dict() for r in results],
        )
