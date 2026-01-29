"""Intent classification module.

Provides config-driven intent classification using multiple matching strategies:
- Exact matching (fast path)
- Fuzzy matching (typo-tolerant)
- Keyword matching (word-order invariant)
- Semantic matching (meaning-based)

All triggers are loaded from ``intent_patterns.json`` - zero hardcoded lists.

Example:
    from core.intent.classifier import ConfigDrivenClassifier

    classifier = ConfigDrivenClassifier()
    intent, tool_choice = classifier.classify("widzisz ostatniego commita?")
    # => ("git_log", None)
"""

from .strategies import IntentClassifier, IntentMatch, MatcherStrategy
from .matchers import (
    ExactMatcher,
    FuzzyMatcher,
    KeywordMatcher,
    SemanticMatcher,
    NormalizedKeywordMatcher,
)
from .config import load_intent_config, create_classifier_from_config
from .classifier import ConfigDrivenClassifier

__all__ = [
    "IntentClassifier",
    "IntentMatch",
    "MatcherStrategy",
    "ExactMatcher",
    "FuzzyMatcher",
    "KeywordMatcher",
    "SemanticMatcher",
    "NormalizedKeywordMatcher",
    "load_intent_config",
    "create_classifier_from_config",
    "ConfigDrivenClassifier",
]
