"""LLM-based intent classifier.

Single LLM call classifies intent. No keyword lists, no fuzzy matching,
no brittle algorithm that breaks on unexpected wording.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple

from core.logging import get_logger

logger = get_logger(__name__)

_CLASSIFY_PROMPT = """\
Classify this user message into exactly one intent. Reply with ONLY the intent name, nothing else.

Intents:
- explore_project: user wants to see the project structure or contents
- list_files: user wants to list files in current directory/folder
- git_log: user wants to see git commit history
- analyze_changes: user wants to analyze code changes or diffs
- general: anything else (greeting, question, coding task, conversation, etc.)

Message: {message}

Intent:"""

_VALID_INTENTS = {"explore_project", "list_files", "git_log", "analyze_changes", "general"}

_TOOL_CHOICES: Dict[str, Dict[str, str]] = {
    "explore_project": {"type": "tool", "name": "bash"},
    "list_files": {"type": "tool", "name": "bash"},
}


class ConfigDrivenClassifier:
    """LLM-based intent classifier.

    Creates its own lightweight Anthropic client. Uses ANTHROPIC_BASE_URL
    from env automatically (works through proxy).
    """

    def __init__(self) -> None:
        self._client = None
        self._init_done = False

    def _ensure_client(self):
        if self._init_done:
            return self._client
        self._init_done = True

        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            return None

        try:
            from anthropic import Anthropic
            self._client = Anthropic(api_key=api_key)
            return self._client
        except Exception:
            return None

    def classify(self, message: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Classify intent via LLM."""
        if len(message.split()) > 20:
            return ("general", None)

        client = self._ensure_client()
        if not client:
            return ("general", None)

        try:
            resp = client.messages.create(
                model="claude-haiku-4-5-20251016",
                max_tokens=20,
                temperature=0.0,
                messages=[{
                    "role": "user",
                    "content": _CLASSIFY_PROMPT.format(message=message),
                }],
            )
            intent = resp.content[0].text.strip().lower().replace(" ", "_")

            if intent not in _VALID_INTENTS:
                logger.debug("LLM returned unknown intent %r, falling back", intent)
                intent = "general"
            else:
                logger.debug("LLM classified %r -> %s", message[:40], intent)

            return (intent, _TOOL_CHOICES.get(intent))

        except Exception as exc:
            logger.debug("LLM classify failed: %s", exc)
            return ("general", None)
