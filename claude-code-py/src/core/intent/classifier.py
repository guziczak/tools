"""Hybrid intent classifier.

Fast keyword check for obvious intents, falls through to general otherwise.
No external LLM calls (they fail through proxy).
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

from core.logging import get_logger

logger = get_logger(__name__)

_TOOL_CHOICES: Dict[str, Dict[str, str]] = {
    "explore_project": {"type": "tool", "name": "bash"},
    "list_files": {"type": "tool", "name": "bash"},
}

# Word sets for keyword matching. Intent matches if ALL words in any set
# are found in the message (word order doesn't matter, partial match OK).
_INTENT_KEYWORDS: Dict[str, list] = {
    "list_files": [
        {"pliki"},
        {"files"},
        {"folder"},
        {"katalog"},
        {"directory"},
        {"zawartość"},
        {"zawartosc"},
        {"co", "tu"},
        {"co", "tutaj"},
        {"co", "masz"},
        {"co", "widzisz"},
        {"obczaj"},
        {"sprawdz"},
        {"sprawdź"},
        {"what", "here"},
    ],
    "explore_project": [
        {"projekt"},
        {"project"},
    ],
    "git_log": [
        {"commit"},
        {"git", "log"},
        {"git", "history"},
    ],
    "analyze_changes": [
        {"przeanalizuj"},
        {"analyze"},
        {"szczegoly"},
        {"szczegóły"},
    ],
}


class ConfigDrivenClassifier:
    """Fast keyword-based intent classifier.

    No LLM calls - works reliably through proxy/OAuth/API key.
    Matches if ALL keywords in any set are found as substrings in the message.
    """

    def __init__(self) -> None:
        pass

    def classify(self, message: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Classify intent via keyword matching."""
        msg = message.lower()
        # Remove punctuation for cleaner matching
        words = set(re.findall(r'\w+', msg))

        for intent, keyword_sets in _INTENT_KEYWORDS.items():
            for kw_set in keyword_sets:
                if all(
                    any(kw in word for word in words)
                    for kw in kw_set
                ):
                    logger.debug("Classified %r -> %s (keywords: %s)", message[:40], intent, kw_set)
                    return (intent, _TOOL_CHOICES.get(intent))

        return ("general", None)
