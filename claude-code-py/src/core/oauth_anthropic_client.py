"""Anthropic API client that uses OAuth Bearer tokens instead of API keys."""

from typing import Iterator, Optional, Dict, Any, List
import os
import httpx
from anthropic import Anthropic, AnthropicBedrock
from anthropic.types import MessageStreamEvent


class OAuthAnthropicClient:
    """Anthropic API client using OAuth Bearer authentication.

    This client uses the same /v1/messages endpoint as regular API,
    but authenticates with Bearer token instead of x-api-key header.
    """

    def __init__(self, oauth_token: str):
        """Initialize client with OAuth token.

        Args:
            oauth_token: OAuth token (sk-ant-oat01-*)
        """
        self.oauth_token = oauth_token
        self._http_client = None  # Lazy initialization

        # Use ANTHROPIC_BASE_URL if set (for proxy support), otherwise default
        self.api_base = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")

    def _get_client(self):
        """Get or create HTTP client (lazy initialization)."""
        if self._http_client is None:
            print(f"🔧 [OAuth Client] Initializing with base_url: {self.api_base}")
            self._http_client = httpx.Client(
                base_url=self.api_base,
                headers={
                    "Authorization": f"Bearer {self.oauth_token[:20]}...",
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01",
                },
                timeout=httpx.Timeout(timeout=600.0),
            )
        return self._http_client

    def chat_streaming(
        self,
        messages: List[Dict[str, str]],
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 8000,
        temperature: float = 1.0,
        system: Optional[str] = None,
        thinking_enabled: bool = True,
        thinking_budget: int = 10000,
        tools: Optional[List[Dict[str, Any]]] = None,
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
            tools: Optional tool definitions (Anthropic format)

        Yields:
            Event dicts with streaming response
        """
        print(f"🚀 [OAuth Client] chat_streaming() CALLED! messages={len(messages)}, tools={'YES' if tools else 'NO'}")

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

        # Add tools if provided
        if tools:
            payload["tools"] = tools

        # Make streaming request
        print(f"📡 [OAuth Client] Sending POST to {self.api_base}/v1/messages")
        print(f"📦 [OAuth Client] Payload: {list(payload.keys())}")

        with self._get_client().stream("POST", "/v1/messages", json=payload) as response:
            print(f"📊 [OAuth Client] Response status: {response.status_code}")
            response.raise_for_status()

            # Track tool uses for building complete blocks
            current_tool_blocks = []
            all_content_blocks = []

            # Parse SSE stream
            line_count = 0
            for line in response.iter_lines():
                line_count += 1
                if line_count == 1:
                    print(f"🔬 [OAuth Client] First line received: {line[:50]}...")

                if not line or not line.startswith("data: "):
                    continue

                data_str = line[6:]  # Remove "data: " prefix

                # Handle [DONE] marker
                if data_str.strip() == "[DONE]":
                    # Yield collected tool blocks before finishing
                    if current_tool_blocks:
                        print(f"🎯 [OAuth Client] Collected {len(current_tool_blocks)} tool blocks")
                        for idx, block in enumerate(current_tool_blocks):
                            print(f"   Tool {idx+1}: {block['name']} - input keys: {list(block.get('input', {}).keys())}")

                        yield {
                            "type": "tool_calls_complete",
                            "tool_blocks": current_tool_blocks,
                            "content": ""
                        }
                    else:
                        print("ℹ️  [OAuth Client] No tool blocks collected")

                    yield {
                        "type": "message_done",
                        "content": ""
                    }
                    break

                # Parse JSON event
                try:
                    import json
                    event = json.loads(data_str)

                    # Track content blocks for tool execution
                    event_type = event.get("type", "")

                    # DEBUG: Log ONLY tool_use events (removed excessive logging)

                    # Collect tool_use blocks
                    if event_type == "content_block_start":
                        content_block = event.get("content_block", {})
                        block_type = content_block.get("type", "")

                        # DEBUG: Always log content_block_start to see what we get
                        print(f"🔎 [OAuth Client] content_block_start: type={block_type}")

                        if block_type == "tool_use":
                            tool_name = content_block.get("name", "")
                            tool_id = content_block.get("id", "")
                            print(f"🔍 [OAuth Client] Tool use detected: {tool_name} (id: {tool_id})")

                            # Start new tool block
                            current_tool_blocks.append({
                                "type": "tool_use",
                                "id": tool_id,
                                "name": tool_name,
                                "input": {}
                            })

                    elif event_type == "content_block_delta":
                        delta = event.get("delta", {})
                        if delta.get("type") == "input_json_delta" and current_tool_blocks:
                            # Accumulate tool input (it's streamed as JSON chunks)
                            # We'll parse the complete JSON later
                            if "input_json" not in current_tool_blocks[-1]:
                                current_tool_blocks[-1]["input_json"] = ""
                            current_tool_blocks[-1]["input_json"] += delta.get("partial_json", "")

                    elif event_type == "content_block_stop":
                        # Complete the current tool block if any
                        if current_tool_blocks and "input_json" in current_tool_blocks[-1]:
                            try:
                                # Parse complete JSON input
                                input_json = current_tool_blocks[-1].pop("input_json")
                                current_tool_blocks[-1]["input"] = json.loads(input_json)
                            except json.JSONDecodeError:
                                # If parsing fails, keep empty input
                                pass

                    # Convert to our standard format and yield
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
            elif block_type == "tool_use":
                # Tool use block started
                return {
                    "type": "tool_use_start",
                    "content": "",
                    "tool_name": content_block.get("name", "unknown"),
                    "tool_id": content_block.get("id", "")
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
    """Check if token is an OAuth token or sessionKey (not API key).

    Args:
        token: Token to check

    Returns:
        True if OAuth token or sessionKey, False if API key
    """
    # OAuth token (from Anthropic API)
    if token.startswith("sk-ant-oat"):
        return True

    # sessionKey (from claude.ai)
    if token.startswith("sk-ant-sid01-"):
        return True

    # Not an OAuth token
    return False
