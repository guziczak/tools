"""Anthropic API client that uses OAuth Bearer tokens instead of API keys."""

from typing import Iterator, Optional, Dict, Any, List
import os
import httpx
from anthropic import Anthropic, AnthropicBedrock
from anthropic.types import MessageStreamEvent

try:
    # Try relative import first (preferred)
    from .logging.logger import get_logger
except ImportError:
    # Fallback for direct script execution
    import sys  # noqa: E402
    from pathlib import Path  # noqa: E402

    sys.path.insert(0, str(Path(__file__).parent))
    from logging.logger import get_logger  # noqa: E402

logger = get_logger(__name__)


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
            logger.debug("Initializing with base_url: %s", self.api_base)
            self._http_client = httpx.Client(
                base_url=self.api_base,
                headers={
                    "Authorization": f"Bearer {self.oauth_token}",
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01",
                },
                timeout=httpx.Timeout(timeout=600.0),
            )
        return self._http_client

    def chat_streaming(
        self,
        messages: List[Dict[str, str]],
        model: str = "claude-sonnet-4-5-20241022",
        max_tokens: int = 8000,
        temperature: float = 1.0,
        system: Optional[str] = None,
        thinking_enabled: bool = True,
        thinking_budget: int = 10000,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Dict[str, Any]] = None,
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
            tool_choice: Optional tool choice config (forces specific tool usage)

        Yields:
            Event dicts with streaming response
        """
        logger.debug(
            "chat_streaming() CALLED! messages=%d, tools=%s",
            len(messages),
            "YES" if tools else "NO",
        )
        if tool_choice:
            logger.debug("tool_choice forced: %s", tool_choice)

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
            payload["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}

        # Add tools if provided
        if tools:
            payload["tools"] = tools

        # Add tool_choice if provided (forces specific tool execution)
        if tool_choice:
            payload["tool_choice"] = tool_choice

        # Make streaming request
        logger.debug("Sending POST to %s/v1/messages", self.api_base)
        logger.debug("Payload: %s", list(payload.keys()))

        with self._get_client().stream("POST", "/v1/messages", json=payload) as response:
            logger.debug("Response status: %d", response.status_code)
            response.raise_for_status()

            # Track tool uses for building complete blocks
            current_tool_blocks = []
            all_text_parts = []  # Buffer text for tool_call parsing (proxy path)
            buffered_events = []  # Buffer events when potential tool_call detected

            # Parse SSE stream
            line_count = 0
            for line in response.iter_lines():
                line_count += 1
                if line_count == 1:
                    logger.debug("First line received: %s...", line[:50])

                if not line or not line.startswith("data: "):
                    continue

                data_str = line[6:]  # Remove "data: " prefix

                # Handle [DONE] marker
                if data_str.strip() == "[DONE]":
                    # Check for text-based tool_call blocks (proxy/sessionKey path)
                    if not current_tool_blocks:
                        full_text = "".join(all_text_parts)
                        parsed_blocks = self._parse_tool_call_blocks(full_text)
                        if parsed_blocks:
                            current_tool_blocks = parsed_blocks
                            # Emit cleaned text (without tool_call blocks)
                            import re
                            clean = re.sub(
                                r'```tool_call\s*\n.*?\n```',
                                '',
                                full_text,
                                flags=re.DOTALL,
                            ).strip()
                            if clean:
                                yield {"type": "text", "content": clean}

                    if current_tool_blocks:
                        logger.debug("Collected %d tool blocks", len(current_tool_blocks))
                        for idx, block in enumerate(current_tool_blocks):
                            logger.debug(
                                "   Tool %d: %s - input keys: %s",
                                idx + 1,
                                block["name"],
                                list(block.get("input", {}).keys()),
                            )

                        yield {
                            "type": "tool_calls_complete",
                            "tool_blocks": current_tool_blocks,
                            "content": "",
                        }
                    else:
                        logger.debug("No tool blocks collected")

                    yield {"type": "message_done", "content": ""}
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
                        logger.debug("content_block_start: type=%s", block_type)

                        # Claude.ai has built-in tools and may return tool_result
                        # IGNORE tool_result completely - we execute tools locally
                        # Only collect tool_use blocks (requests for us to execute)
                        if block_type == "tool_result":
                            logger.debug(
                                "Claude.ai tool_result detected - ignoring (tools execute locally)"
                            )
                            # Don't stop streaming - continue to get text response
                            # Just skip this block type (don't collect it)
                            continue

                        # ONLY collect tool_use blocks (NOT tool_result, thinking, text, etc.)
                        if block_type == "tool_use":
                            tool_name = content_block.get("name", "")
                            tool_id = content_block.get("id", "")
                            logger.debug("Tool use detected: %s (id: %s)", tool_name, tool_id)

                            # Start new tool block
                            current_tool_blocks.append(
                                {
                                    "type": "tool_use",
                                    "id": tool_id,
                                    "name": tool_name,
                                    "input": {},
                                    "_collecting": True,  # Flag to track if we're still collecting this block
                                }
                            )

                    elif event_type == "content_block_delta":
                        delta = event.get("delta", {})
                        delta_type = delta.get("type", "")

                        # Track text for tool_call block parsing (proxy path)
                        if delta_type == "text_delta":
                            all_text_parts.append(delta.get("text", ""))

                        # ONLY collect input for tool_use blocks that are still being collected
                        if delta_type == "input_json_delta" and current_tool_blocks:
                            # Check if last block is a tool_use and still collecting
                            last_block = current_tool_blocks[-1]
                            if last_block.get("type") == "tool_use" and last_block.get(
                                "_collecting"
                            ):
                                partial = delta.get("partial_json", "")
                                if partial:
                                    if "input_json" not in last_block:
                                        last_block["input_json"] = ""
                                        logger.debug(
                                            "Starting to collect input JSON for %s",
                                            last_block["name"],
                                        )
                                    last_block["input_json"] += partial

                    elif event_type == "content_block_stop":
                        # Complete the current tool block if it's a tool_use being collected
                        if current_tool_blocks:
                            last_block = current_tool_blocks[-1]
                            if last_block.get("type") == "tool_use" and last_block.get(
                                "_collecting"
                            ):
                                # Mark as done collecting
                                last_block.pop("_collecting", None)

                                # Parse input JSON if we collected any
                                if "input_json" in last_block:
                                    try:
                                        input_json = last_block.pop("input_json")
                                        last_block["input"] = json.loads(input_json)
                                        logger.debug(
                                            "Parsed input for %s: %s",
                                            last_block["name"],
                                            list(last_block["input"].keys()),
                                        )
                                    except json.JSONDecodeError as e:
                                        logger.error("Failed to parse JSON: %s", e)
                                        pass

                                # DON'T yield immediately - wait for tool_result or [DONE]
                                # Otherwise we'll yield the same tool twice!
                                logger.debug(
                                    "Tool block complete, waiting for tool_result or [DONE]"
                                )

                    # Convert to our standard format and yield
                    # Suppress text events when tool_call block detected (proxy path)
                    converted_event = self._convert_event(event)
                    if converted_event:
                        full_so_far = "".join(all_text_parts)
                        if "```tool_call" in full_so_far:
                            # Confirmed tool_call — suppress all text events, discard buffer
                            buffered_events.clear()
                            if converted_event.get("type") not in ("text", "text_start"):
                                yield converted_event
                        elif full_so_far.rstrip().endswith("```") or full_so_far.rstrip().endswith("```t") or "```tool" in full_so_far:
                            # Might be start of ```tool_call — buffer this event
                            buffered_events.append(converted_event)
                        else:
                            # Not a tool_call — flush any buffered events
                            for buf in buffered_events:
                                yield buf
                            buffered_events.clear()
                            yield converted_event

                except json.JSONDecodeError:
                    # Skip malformed JSON
                    continue

    def _parse_tool_call_blocks(self, text: str) -> List[Dict[str, Any]]:
        """Parse ```tool_call JSON blocks from text response.

        Used when proxy injects tool definitions into the prompt and Claude
        outputs ```tool_call blocks instead of native tool_use.
        """
        import re
        import json as json_mod
        import uuid

        blocks = []
        pattern = r'```tool_call\s*\n(.*?)\n```'
        matches = re.findall(pattern, text, re.DOTALL)

        for match in matches:
            try:
                data = json_mod.loads(match.strip())
                tool_name = data.get("tool", "")
                params = data.get("parameters", {})
                if tool_name:
                    blocks.append({
                        "type": "tool_use",
                        "id": f"text-tool-{uuid.uuid4().hex[:8]}",
                        "name": tool_name,
                        "input": params,
                    })
                    logger.debug("Parsed text tool_call: %s(%s)", tool_name, list(params.keys()))
            except (json_mod.JSONDecodeError, KeyError) as e:
                logger.debug("Failed to parse tool_call block: %s", e)

        return blocks

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
                text_content = delta["text"]
                if text_content:  # Debug: log non-empty text
                    logger.debug("Text delta received: '%s...'", text_content[:50])
                return {"type": "text", "content": text_content}
            elif "thinking" in delta:
                return {"type": "thinking", "content": delta["thinking"]}

        # Content block start
        elif event_type == "content_block_start":
            content_block = event.get("content_block", {})
            block_type = content_block.get("type", "")

            if block_type == "thinking":
                return {"type": "thinking_start", "content": ""}
            elif block_type == "text":
                return {"type": "text_start", "content": ""}
            elif block_type == "tool_use":
                # Tool use block started
                return {
                    "type": "tool_use_start",
                    "content": "",
                    "tool_name": content_block.get("name", "unknown"),
                    "tool_id": content_block.get("id", ""),
                }

        # Content block stop
        elif event_type == "content_block_stop":
            return {"type": "block_stop", "content": ""}

        # message_stop / message_delta — do NOT emit message_done here.
        # The [DONE] handler emits it after processing tool_call blocks.

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
