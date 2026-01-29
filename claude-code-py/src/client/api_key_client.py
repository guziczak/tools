"""API key backend wrapping the standard Anthropic SDK."""

from __future__ import annotations

from typing import Any, Dict, Iterator, List, Optional

from anthropic import Anthropic
from core.logging import get_logger
from .event_converter import convert_anthropic_event

logger = get_logger(__name__)


class AnthropicKeyClient:
    """LLM client backed by a standard Anthropic API key."""

    def __init__(
        self,
        api_key: str,
        model: str,
        max_tokens: int = 8000,
        temperature: float = 1.0,
        thinking_enabled: bool = True,
        thinking_budget: int = 10000,
    ) -> None:
        self._client = Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.thinking_enabled = thinking_enabled
        self.thinking_budget = thinking_budget

    @property
    def raw(self) -> Anthropic:
        """Return the underlying Anthropic SDK client."""
        return self._client

    def chat_streaming(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Dict[str, Any]] = None,
    ) -> Iterator[Dict[str, Any]]:
        params: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": messages,
        }
        if system:
            params["system"] = system
        if self.thinking_enabled:
            params["thinking"] = {
                "type": "enabled",
                "budget_tokens": self.thinking_budget,
            }
        if tools:
            params["tools"] = tools

        with self._client.messages.stream(**params) as stream:
            for event in stream:
                ev = convert_anthropic_event(event)
                if ev:
                    yield ev
