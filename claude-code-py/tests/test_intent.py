"""Unit tests for intent classification.

Tests the intent classification system including:
- Exact matching
- Fuzzy matching (typo tolerance)
- Keyword matching (word-order invariance)
- Semantic matching
"""

import pytest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.intent import (
    IntentClassifier,
    ExactMatcher,
    FuzzyMatcher,
    KeywordMatcher,
    SemanticMatcher,
    ConfigDrivenClassifier,
)


class TestExactMatcher:
    """Tests for exact string matching."""

    def test_exact_match(self):
        """Should match exact trigger phrases."""
        matcher = ExactMatcher(
            {"git_log": ["ostatni commit", "git log"], "explore_project": ["widzisz projekt"]}
        )

        result = matcher.match("widzisz projekt")
        assert result is not None
        assert result.intent == "explore_project"
        assert result.confidence == 1.0

    def test_case_insensitive(self):
        """Should be case insensitive."""
        matcher = ExactMatcher({"git_log": ["git log"]})

        result = matcher.match("GIT LOG")
        assert result is not None
        assert result.intent == "git_log"

    def test_partial_match(self):
        """Should match trigger as substring."""
        matcher = ExactMatcher({"git_log": ["git log"]})

        # Trigger in longer query
        result = matcher.match("pokaz mi git log z ostatnich 10 commitów")
        assert result is not None
        assert result.intent == "git_log"

    def test_no_match(self):
        """Should return None if no match."""
        matcher = ExactMatcher({"git_log": ["git log"]})

        result = matcher.match("cos zupelnie innego")
        assert result is None


class TestFuzzyMatcher:
    """Tests for fuzzy matching (typo tolerance)."""

    def test_typo_tolerance(self):
        """Should catch typos."""
        matcher = FuzzyMatcher(trigger_map={"git_log": ["ostatni commit"]}, threshold=85)

        # Typo: "commita" instead of "commit"
        result = matcher.match("ostatniego commita")
        assert result is not None
        assert result.intent == "git_log"

    def test_similarity_threshold(self):
        """Should respect similarity threshold."""
        matcher = FuzzyMatcher(
            trigger_map={"git_log": ["ostatni commit"]}, threshold=90  # High threshold
        )

        # Very different - should not match
        result = matcher.match("pierwszy push")
        assert result is None

    def test_best_match_selection(self):
        """Should select best match when multiple possibilities."""
        matcher = FuzzyMatcher(
            trigger_map={"git_log": ["ostatni commit"], "git_push": ["ostatni push"]}, threshold=80
        )

        # Closer to "ostatni commit"
        result = matcher.match("ostatni comit")
        assert result is not None
        assert result.intent == "git_log"


class TestKeywordMatcher:
    """Tests for keyword-based matching."""

    def test_word_order_invariance(self):
        """Should match regardless of word order."""
        matcher = KeywordMatcher({"git_log": [["ostatni", "commit"]]})

        # Different word orders
        assert matcher.match("ostatni commit").intent == "git_log"
        assert matcher.match("commit ostatni").intent == "git_log"
        assert matcher.match("widzisz ostatni commit?").intent == "git_log"
        assert matcher.match("commit widzisz ostatni?").intent == "git_log"

    def test_all_keywords_required(self):
        """Should require ALL keywords in set."""
        matcher = KeywordMatcher({"git_log": [["ostatni", "commit"]]})

        # Missing "commit" - no match
        result = matcher.match("ostatni")
        assert result is None

        # Missing "ostatni" - no match
        result = matcher.match("commit")
        assert result is None

    def test_multiple_keyword_sets(self):
        """Should match any keyword set (OR logic between sets)."""
        matcher = KeywordMatcher(
            {"git_log": [["ostatni", "commit"], ["last", "commit"]]}  # Polish  # English
        )

        # Match Polish
        assert matcher.match("ostatni commit").intent == "git_log"

        # Match English
        assert matcher.match("last commit").intent == "git_log"

    def test_partial_word_matching(self):
        """Should match partial words (e.g., 'commita' contains 'commit')."""
        matcher = KeywordMatcher({"git_log": [["commit"]]})

        # "commita" contains "commit"
        result = matcher.match("ostatniego commita")
        assert result is not None
        assert result.intent == "git_log"


class TestSemanticMatcher:
    """Tests for semantic similarity matching."""

    def test_word_overlap_similarity(self):
        """Should match based on word overlap."""
        matcher = SemanticMatcher(
            reference_map={"explore_project": ["show project files", "what is in this project"]},
            threshold=0.4,
        )

        # High overlap with "show project files"
        result = matcher.match("show me project")
        assert result is not None
        assert result.intent == "explore_project"

    def test_similarity_threshold(self):
        """Should respect similarity threshold."""
        matcher = SemanticMatcher(
            reference_map={"explore_project": ["show project files"]},
            threshold=0.8,  # High threshold
        )

        # Low similarity - no match
        result = matcher.match("git log")
        assert result is None


class TestIntentClassifier:
    """Integration tests for full classifier."""

    def test_tries_matchers_in_order(self):
        """Should try matchers in order and return first match."""
        classifier = IntentClassifier()

        # Fast exact matcher first
        classifier.add_matcher(ExactMatcher({"git_log": ["git log"]}))

        # Slower fuzzy matcher second
        classifier.add_matcher(FuzzyMatcher({"git_log": ["git log"]}, threshold=85))

        result = classifier.classify("git log")

        # Should match via ExactMatcher (first)
        assert result.intent == "git_log"
        assert result.metadata["method"] == "exact"

    def test_fallback_to_general(self):
        """Should return 'general' intent if no match."""
        classifier = IntentClassifier()
        classifier.add_matcher(ExactMatcher({"git_log": ["git log"]}))

        result = classifier.classify("completely different query")

        assert result.intent == "general"
        assert result.confidence == 1.0

    def test_confidence_threshold(self):
        """Should respect confidence threshold."""
        classifier = IntentClassifier()

        # Add matcher that returns low confidence
        classifier.add_matcher(
            SemanticMatcher(
                reference_map={"explore_project": ["show project"]},
                threshold=0.2,  # Low threshold - will match with low confidence
            )
        )

        # Query with very low similarity (but above matcher's threshold)
        result = classifier.classify("something else", confidence_threshold=0.8)

        # Should fallback to general (low confidence rejected)
        assert result.intent == "general"


class TestConfigDrivenClassifier:
    """Tests for config-driven classifier (intent_patterns.json)."""

    def test_handles_polish_queries(self):
        """Should handle Polish language queries."""
        classifier = ConfigDrivenClassifier()

        intent, _ = classifier.classify("widzisz projekt")
        assert intent == "explore_project"
        intent, _ = classifier.classify("ostatni commit")
        assert intent == "git_log"
        intent, _ = classifier.classify("jakie pliki")
        assert intent == "list_files"

    def test_handles_english_queries(self):
        """Should handle English language queries."""
        classifier = ConfigDrivenClassifier()

        intent, _ = classifier.classify("show me the project")
        assert intent == "explore_project"
        intent, _ = classifier.classify("last commit")
        assert intent == "git_log"
        intent, _ = classifier.classify("list files")
        assert intent == "list_files"

    def test_returns_tool_choice(self):
        """Should return tool_choice for file-listing intents."""
        classifier = ConfigDrivenClassifier()

        _, tc = classifier.classify("widzisz projekt")
        assert tc == {"type": "tool", "name": "bash"}

        _, tc = classifier.classify("git log")
        assert tc is None  # git_log has no tool_choice in config

    def test_word_order_invariance(self):
        """Should handle different word orders via keyword matcher."""
        classifier = ConfigDrivenClassifier()

        intent, _ = classifier.classify("ostatni commit")
        assert intent == "git_log"
        intent, _ = classifier.classify("commit ostatni")
        assert intent == "git_log"


# Pytest configuration
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
