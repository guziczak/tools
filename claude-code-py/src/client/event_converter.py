"""Shared Anthropic SSE event converter.

Converts Anthropic MessageStreamEvent objects to the internal
event dict format used throughout the pipeline.
"""

from typing import Any, Dict, Optional


def convert_anthropic_event(event) -> Optional[Dict[str, Any]]:
    """Convert an Anthropic stream event to internal format.

    Args:
        event: An Anthropic MessageStreamEvent (has .type, .delta, etc.)

    Returns:
        Internal event dict or None if event should be skipped.
    """
    if event.type == "content_block_delta":
        if hasattr(event.delta, "text"):
            return {"type": "text", "content": event.delta.text}
        elif hasattr(event.delta, "thinking"):
            return {"type": "thinking", "content": event.delta.thinking}

    elif event.type == "content_block_start":
        if hasattr(event.content_block, "type"):
            t = event.content_block.type
            if t == "thinking":
                return {"type": "thinking_start", "content": ""}
            elif t == "text":
                return {"type": "text_start", "content": ""}
            elif t == "tool_use":
                return {
                    "type": "tool_use_start",
                    "content": "",
                    "tool_name": getattr(event.content_block, "name", "unknown"),
                    "tool_id": getattr(event.content_block, "id", ""),
                }

    elif event.type == "content_block_stop":
        return {"type": "block_stop", "content": ""}

    elif event.type == "message_stop":
        return {"type": "message_done", "content": ""}

    return None
