"""Stream event types replacing Dict[str, Any] for streaming responses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class StreamEvent:
    """A streaming event from the chat pipeline.

    Replaces the Dict[str, Any] events used throughout the codebase.

    Attributes:
        type: Event type (e.g., "text", "thinking", "tool_use_start", "tool_execute",
              "tool_round_start", "tool_round_complete", "message_done", "error")
        content: Event content (text chunk, error message, etc.)
        tool_name: Tool name (for tool_use_start, tool_execute events)
        tool_id: Tool use ID (for tool_use_start events)
        tool_input: Tool input parameters (for tool_execute events)
        result: Tool execution result (for tool_execute events)
        tool_blocks: Tool blocks from OAuth response (for tool_calls_complete events)
        metadata: Additional event-specific data
    """

    type: str
    content: str = ""
    tool_name: Optional[str] = None
    tool_id: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    result: Any = None
    tool_blocks: Optional[list] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to legacy dict format for backward compatibility."""
        d: Dict[str, Any] = {"type": self.type, "content": self.content}
        if self.tool_name is not None:
            d["tool_name"] = self.tool_name
        if self.tool_id is not None:
            d["tool_id"] = self.tool_id
        if self.tool_input is not None:
            d["tool_input"] = self.tool_input
        if self.result is not None:
            d["result"] = self.result
        if self.tool_blocks is not None:
            d["tool_blocks"] = self.tool_blocks
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> StreamEvent:
        """Create from legacy dict format."""
        return cls(
            type=d.get("type", ""),
            content=d.get("content", ""),
            tool_name=d.get("tool_name"),
            tool_id=d.get("tool_id"),
            tool_input=d.get("tool_input"),
            result=d.get("result"),
            tool_blocks=d.get("tool_blocks"),
        )
