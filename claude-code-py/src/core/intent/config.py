"""Load intent patterns from JSON config and build a classifier."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import json
import os

from core.logging import get_logger
from .strategies import IntentClassifier
from .matchers import ExactMatcher, FuzzyMatcher, SemanticMatcher, NormalizedKeywordMatcher

logger = get_logger(__name__)


def _default_config_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "intent_patterns.json"


def load_intent_config(path: Optional[Path] = None) -> Dict[str, Any]:
    """Load intent configuration from JSON.

    Returns empty dict if file is missing or invalid.
    """
    env_path = os.getenv("CLAUDE_INTENT_CONFIG")
    config_path = Path(env_path) if env_path else (path or _default_config_path())

    if not config_path.exists():
        return {}

    try:
        with config_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.warning("Failed to load intent config: %s", exc)
        return {}


def create_classifier_from_config() -> Tuple[Optional[IntentClassifier], float]:
    """Create IntentClassifier from config file.

    Returns (classifier, confidence_threshold). If config missing, returns (None, 0.5).
    """
    config = load_intent_config()
    if not config:
        return None, 0.5

    thresholds = config.get("thresholds", {})
    confidence_threshold = float(thresholds.get("confidence", 0.6))
    fuzzy_threshold = int(thresholds.get("fuzzy", 85))
    semantic_threshold = float(thresholds.get("semantic", 0.4))

    intents = config.get("intents", {})

    exact_map: Dict[str, list] = {}
    fuzzy_map: Dict[str, list] = {}
    keyword_map: Dict[str, list] = {}
    reference_map: Dict[str, list] = {}

    for intent_name, intent_cfg in intents.items():
        exact_triggers = intent_cfg.get("exact", [])
        if exact_triggers:
            exact_map[intent_name] = exact_triggers

        fuzzy_triggers = intent_cfg.get("fuzzy", [])
        if fuzzy_triggers:
            fuzzy_map[intent_name] = fuzzy_triggers

        keywords = intent_cfg.get("keywords", [])
        if keywords:
            keyword_map[intent_name] = keywords

        references = intent_cfg.get("references", [])
        if references:
            reference_map[intent_name] = references

    classifier = IntentClassifier()

    if exact_map:
        classifier.add_matcher(ExactMatcher(exact_map))
    if fuzzy_map:
        classifier.add_matcher(FuzzyMatcher(fuzzy_map, threshold=fuzzy_threshold))
    if keyword_map:
        classifier.add_matcher(NormalizedKeywordMatcher(keyword_map))
    if reference_map:
        classifier.add_matcher(SemanticMatcher(reference_map, threshold=semantic_threshold))

    return classifier, confidence_threshold


__all__ = ["load_intent_config", "create_classifier_from_config"]
