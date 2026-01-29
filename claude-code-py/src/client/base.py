"""LLM client protocol - common interface for API key and OAuth backends."""

from __future__ import annotations

from typing import Any, Dict, Iterator, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class LLMClient(Protocol):
    """Protocol for LLM backends (API key or OAuth).

    Both ``AnthropicKeyClient`` and ``OAuthClient`` must satisfy this interface.
    """

    def chat_streaming(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Dict[str, Any]] = None,
    ) -> Iterator[Dict[str, Any]]:
        """Stream a chat response.

        Yields:
            Event dicts with at least ``{"type": ..., "content": ...}``.
        """
        ...
