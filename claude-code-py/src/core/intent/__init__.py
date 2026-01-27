"""Intent classification module.

Provides intelligent intent classification using multiple matching strategies:
- Exact matching (fast path)
- Fuzzy matching (typo-tolerant)
- Keyword matching (word-order invariant)
- Semantic matching (meaning-based)

Example:
    from core.intent import create_default_classifier

    classifier = create_default_classifier()
    result = classifier.classify("widzisz ostatniego commita?")
    # => IntentMatch(intent="git_log", confidence=0.95)
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


def create_default_classifier() -> IntentClassifier:
    """Create classifier with default matchers for common intents.

    This is a factory function that sets up a production-ready classifier
    with sensible defaults.

    Returns:
        Configured IntentClassifier
    """
    classifier = IntentClassifier()

    # Tier 1: Exact matching (fastest - try first)
    classifier.add_matcher(
        ExactMatcher(
            {
                "explore_project": [
                    "widzisz projekt",
                    "czy widzisz projekt",
                    "do you see project",
                    "show me the project",
                ],
                "list_files": ["jakie pliki", "list files", "show files"],
            }
        )
    )

    # Tier 1.5: Fuzzy matching (typo-tolerant)
    classifier.add_matcher(
        FuzzyMatcher(
            trigger_map={
                "explore_project": ["widzisz projekt"],
                "list_files": ["jakie pliki"],
            },
            threshold=85,
        )
    )

    # Tier 2: Keyword matching (word-order invariant)
    classifier.add_matcher(
        KeywordMatcher(
            {
                "git_log": [
                    ["ostatni", "commit"],  # Polish
                    ["last", "commit"],  # English
                    ["git", "log"],
                    ["git", "history"],
                ],
                "explore_project": [["widzisz", "projekt"]],
            }
        )
    )

    # Tier 2.5: Semantic matching (meaning-based)
    classifier.add_matcher(
        SemanticMatcher(
            reference_map={
                "explore_project": [
                    "show project files",
                    "what is in this project",
                    "list project contents",
                ]
            },
            threshold=0.4,
        )
    )

    return classifier


__all__ = [
    "IntentClassifier",
    "IntentMatch",
    "MatcherStrategy",
    "ExactMatcher",
    "FuzzyMatcher",
    "KeywordMatcher",
    "SemanticMatcher",
    "NormalizedKeywordMatcher",
    "create_default_classifier",
    "load_intent_config",
    "create_classifier_from_config",
]
