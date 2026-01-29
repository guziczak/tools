"""Conversation history manager with bounded sliding window."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.logging import get_logger

logger = get_logger(__name__)

MAX_HISTORY = 100


class ConversationManager:
    """Manages conversation history with a bounded sliding window.

    Prevents unbounded memory growth by keeping at most ``max_history``
    messages.  When the limit is exceeded the oldest messages are dropped.

    Attributes:
        max_history: Maximum number of messages to retain.
    """

    def __init__(self, max_history: int = MAX_HISTORY) -> None:
        self.max_history = max_history
        self._messages: List[Dict[str, Any]] = []

    # -- public API --

    @property
    def messages(self) -> List[Dict[str, Any]]:
        """Return the current message list (mutable reference for legacy compat)."""
        return self._messages

    def add(self, role: str, content: Any) -> None:
        """Append a message and enforce the sliding window."""
        self._messages.append({"role": role, "content": content})
        self._trim()

    def add_raw(self, message: Dict[str, Any]) -> None:
        """Append a pre-built message dict."""
        self._messages.append(message)
        self._trim()

    def clear(self) -> None:
        """Drop all messages."""
        self._messages.clear()
        logger.debug("Conversation history cleared")

    def __len__(self) -> int:
        return len(self._messages)

    # -- internals --

    def _trim(self) -> None:
        """Drop oldest messages if over limit."""
        overflow = len(self._messages) - self.max_history
        if overflow > 0:
            self._messages = self._messages[overflow:]
            logger.debug("Trimmed %d oldest messages (history capped at %d)", overflow, self.max_history)
