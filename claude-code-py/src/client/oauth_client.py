"""OAuth backend wrapping UnifiedClaudeClient."""

from __future__ import annotations

from typing import Any, Dict, Iterator, List, Optional

from core.logging import get_logger

logger = get_logger(__name__)


class OAuthLLMClient:
    """LLM client backed by an OAuth token (claude.ai)."""

    def __init__(
        self,
        token: str,
        model: str,
        max_tokens: int = 8000,
        temperature: float = 1.0,
        thinking_enabled: bool = True,
        thinking_budget: int = 10000,
    ) -> None:
        from core.unified_client import UnifiedClaudeClient

        self._client = UnifiedClaudeClient(
            token=token,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            thinking_enabled=thinking_enabled,
            thinking_budget=thinking_budget,
        )

    def chat_streaming(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Dict[str, Any]] = None,
    ) -> Iterator[Dict[str, Any]]:
        yield from self._client.chat_streaming(
            messages=messages,
            system=system,
            tools=tools,
            tool_choice=tool_choice,
        )
