"""Anthropic API client that uses OAuth Bearer tokens instead of API keys."""

from typing import Iterator, Optional, Dict, Any, List
import httpx
from anthropic import Anthropic, AnthropicBedrock
from anthropic.types import MessageStreamEvent


class OAuthAnthropicClient:
    """Anthropic API client using OAuth Bearer authentication.

    This client uses the same /v1/messages endpoint as regular API,
    but authenticates with Bearer token instead of x-api-key header.
    """

    API_BASE = "https://api.anthropic.com"

    def __init__(self, oauth_token: str):
        """Initialize client with OAuth token.

        Args:
            oauth_token: OAuth token (sk-ant-oat01-*)
        """
        self.oauth_token = oauth_token
        self.http_client = httpx.Client(
            base_url=self.API_BASE,
            headers={
                "Authorization": f"Bearer {oauth_token}",
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01",
            },
            timeout=httpx.Timeout(timeout=600.0),
        )

    def chat_streaming(
        self,
        messages: List[Dict[str, str]],
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 8000,
        temperature: float = 1.0,
        system: Optional[str] = None,
        thinking_enabled: bool = True,
        thinking_budget: int = 10000,
    ) -> Iterator[Dict[str, Any]]:
        """Send chat message and stream response using OAuth authentication.

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
        # Build request payload (same format as standard API)
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
            "stream": True,
        }

        # Add system prompt if provided
        if system:
            payload["system"] = system

        # Add thinking parameters if enabled
        if thinking_enabled:
            payload["thinking"] = {
                "type": "enabled",
                "budget_tokens": thinking_budget
            }

        # Make streaming request
        with self.http_client.stream("POST", "/v1/messages", json=payload) as response:
            response.raise_for_status()

            # Parse SSE stream
            for line in response.iter_lines():
                if not line or not line.startswith("data: "):
                    continue

                data_str = line[6:]  # Remove "data: " prefix

                # Handle [DONE] marker
                if data_str.strip() == "[DONE]":
                    yield {
                        "type": "message_done",
                        "content": ""
                    }
                    break

                # Parse JSON event
                try:
                    import json
                    event = json.loads(data_str)

                    # Convert to our standard format
                    converted_event = self._convert_event(event)
                    if converted_event:
                        yield converted_event

                except json.JSONDecodeError:
                    # Skip malformed JSON
                    continue

    def _convert_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert Anthropic API event to standard format.

        Args:
            event: Event from Anthropic API

        Returns:
            Converted event or None
        """
        event_type = event.get("type", "")

        # Text delta
        if event_type == "content_block_delta":
            delta = event.get("delta", {})

            if "text" in delta:
                return {
                    "type": "text",
                    "content": delta["text"]
                }
            elif "thinking" in delta:
                return {
                    "type": "thinking",
                    "content": delta["thinking"]
                }

        # Content block start
        elif event_type == "content_block_start":
            content_block = event.get("content_block", {})
            block_type = content_block.get("type", "")

            if block_type == "thinking":
                return {
                    "type": "thinking_start",
                    "content": ""
                }
            elif block_type == "text":
                return {
                    "type": "text_start",
                    "content": ""
                }

        # Content block stop
        elif event_type == "content_block_stop":
            return {
                "type": "block_stop",
                "content": ""
            }

        # Message complete
        elif event_type == "message_stop" or event_type == "message_delta":
            return {
                "type": "message_done",
                "content": ""
            }

        return None


def is_oauth_token(token: str) -> bool:
    """Check if token is an OAuth token (not API key).

    Args:
        token: Token to check

    Returns:
        True if OAuth token, False if API key
    """
    return token.startswith("sk-ant-oat")
