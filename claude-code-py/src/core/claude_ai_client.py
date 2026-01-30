"""Claude.ai API client for OAuth tokens (like official Claude Code)."""

from typing import Iterator, Optional, Dict, Any, List
from anthropic import Anthropic
from anthropic.types import MessageStreamEvent


class ClaudeAIClient:
    """Client for OAuth tokens - simplified approach.

    Attempts to use OAuth token with standard Anthropic API.
    This is the simplest possible approach.
    """

    def __init__(self, oauth_token: str):
        """Initialize client with OAuth token.

        Args:
            oauth_token: OAuth token from claude setup-token (sk-ant-oat01-*)
        """
        self.oauth_token = oauth_token

        # Try using OAuth token directly with Anthropic library
        # Even though it's an OAuth token, maybe it works as API key?
        self.client = Anthropic(api_key=oauth_token)

    def chat_streaming(
        self,
        messages: List[Dict[str, str]],
        model: str = "claude-sonnet-4-5-20241022",
        max_tokens: int = 8000,
        temperature: float = 1.0,
        system: Optional[str] = None,
        thinking_enabled: bool = True,
        thinking_budget: int = 10000,
    ) -> Iterator[Dict[str, Any]]:
        """Send chat message and stream response.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            system: Optional system prompt
            thinking_enabled: Enable extended thinking
            thinking_budget: Token budget for thinking

        Yields:
            Event dicts with streaming response
        """
        # Prepare request parameters
        request_params = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }

        # Add system prompt if provided
        if system:
            request_params["system"] = system

        # Add thinking parameters if enabled
        if thinking_enabled:
            request_params["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}

        # Stream the response using official library
        with self.client.messages.stream(**request_params) as stream:
            for event in stream:
                converted_event = self._convert_event(event)
                if converted_event:
                    yield converted_event

    def _convert_event(self, event: MessageStreamEvent) -> Optional[Dict[str, Any]]:
        """Convert Anthropic event to standard format.

        Args:
            event: Event from Anthropic API

        Returns:
            Converted event or None
        """
        # Text delta (main response)
        if event.type == "content_block_delta":
            if hasattr(event.delta, "text"):
                return {"type": "text", "content": event.delta.text}
            # Thinking delta
            elif hasattr(event.delta, "thinking"):
                return {"type": "thinking", "content": event.delta.thinking}

        # Content block start
        elif event.type == "content_block_start":
            if hasattr(event.content_block, "type"):
                if event.content_block.type == "thinking":
                    return {"type": "thinking_start", "content": ""}
                elif event.content_block.type == "text":
                    return {"type": "text_start", "content": ""}

        # Content block stop
        elif event.type == "content_block_stop":
            return {"type": "block_stop", "content": ""}

        # Message complete
        elif event.type == "message_stop":
            return {"type": "message_done", "content": ""}

        return None


def is_oauth_token(token: str) -> bool:
    """Check if token is an OAuth token (not API key).

    Args:
        token: Token to check

    Returns:
        True if OAuth token, False if API key
    """
    return token.startswith("sk-ant-oat")
