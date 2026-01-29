"""Config-driven intent classifier.

This is the SINGLE entry point for intent classification. All triggers
come from ``intent_patterns.json`` - zero hardcoded trigger lists.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from core.logging import get_logger
from .config import create_classifier_from_config, load_intent_config
from .strategies import IntentClassifier as _StrategyClassifier

logger = get_logger(__name__)


class ConfigDrivenClassifier:
    """Classifies user intent using ONLY config-driven matchers.

    Replaces the 250+ lines of hardcoded triggers in ``api_client.py``.

    Attributes:
        classifier: Underlying strategy-based classifier built from JSON config.
        confidence_threshold: Minimum confidence to accept a match.
        tool_choice_map: Per-intent tool_choice overrides from config.
    """

    def __init__(self) -> None:
        self.classifier, self.confidence_threshold = create_classifier_from_config()
        self.tool_choice_map: Dict[str, Optional[Dict[str, Any]]] = {}
        self._load_tool_choices()

    def _load_tool_choices(self) -> None:
        """Load per-intent tool_choice from JSON config."""
        config = load_intent_config()
        for intent_name, intent_cfg in config.get("intents", {}).items():
            tc = intent_cfg.get("tool_choice")
            if tc:
                self.tool_choice_map[intent_name] = tc

    def classify(self, message: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Classify user query intent.

        Returns:
            ``(intent_name, tool_choice)`` where tool_choice may be ``None``.
        """
        if not self.classifier:
            logger.debug("No classifier available, falling back to general")
            return ("general", None)

        match = self.classifier.classify(
            message, confidence_threshold=self.confidence_threshold
        )

        intent = match.intent if match else "general"
        tool_choice = self.tool_choice_map.get(intent)

        if intent != "general":
            logger.debug(
                "ConfigDrivenClassifier: intent=%s confidence=%.2f method=%s",
                intent,
                match.confidence if match else 0,
                (match.metadata or {}).get("method", "?") if match else "?",
            )

        return (intent, tool_choice)
