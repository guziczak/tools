"""Tests for Confidence Scoring system.

Tests transparency features that show how confident the system is.
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.confidence import (
    ConfidenceScorer,
    ConfidenceLevel,
    create_confidence_from_context
)


class TestConfidenceScorer:
    """Tests for ConfidenceScorer."""

    def test_very_high_confidence(self):
        """Should give very high confidence for fresh verified data."""
        scorer = ConfidenceScorer()
        score = (scorer
                 .add_data_freshness(age_seconds=2, verified=True)
                 .add_verification_status(True, verification_method="exact")
                 .add_intent_match("exact")
                 .add_tool_success(1.0)
                 .build())

        assert score.level == ConfidenceLevel.VERY_HIGH
        assert score.score >= 0.90
        assert len(score.warnings) == 0  # No warnings for perfect data

    def test_low_confidence_stale_data(self):
        """Should give low confidence for old unverified data."""
        scorer = ConfidenceScorer()
        score = (scorer
                 .add_data_freshness(age_seconds=7200, verified=False)  # 2 hours old
                 .add_verification_status(False)
                 .add_intent_match("general")
                 .add_tool_success(0.5)  # Half tools failed
                 .build())

        assert score.level in [ConfidenceLevel.LOW, ConfidenceLevel.VERY_LOW]
        assert score.score < 0.50
        assert len(score.warnings) > 0  # Should have warnings

    def test_data_freshness_scoring(self):
        """Should score freshness correctly."""
        # Very fresh (< 5s)
        score1 = ConfidenceScorer().add_data_freshness(age_seconds=2).build()
        assert score1.factors["data_freshness"] >= 0.90

        # Fresh (< 1min)
        score2 = ConfidenceScorer().add_data_freshness(age_seconds=30).build()
        assert score2.factors["data_freshness"] >= 0.80

        # Old (> 1hour)
        score3 = ConfidenceScorer().add_data_freshness(age_seconds=7200).build()
        assert score3.factors["data_freshness"] < 0.30

    def test_verification_boost(self):
        """Should boost score when data is verified."""
        # Without verification
        score1 = ConfidenceScorer().add_data_freshness(age_seconds=100, verified=False).build()

        # With verification
        score2 = ConfidenceScorer().add_data_freshness(age_seconds=100, verified=True).build()

        # Verified should have higher confidence
        assert score2.score > score1.score

    def test_intent_match_types(self):
        """Should score different match types correctly."""
        # Exact match = highest
        exact = ConfidenceScorer().add_intent_match("exact").build()
        assert exact.factors["intent_match"] == 1.0

        # Fuzzy = high but not perfect
        fuzzy = ConfidenceScorer().add_intent_match("fuzzy").build()
        assert 0.80 <= fuzzy.factors["intent_match"] < 1.0

        # Semantic = medium
        semantic = ConfidenceScorer().add_intent_match("semantic").build()
        assert 0.60 <= semantic.factors["intent_match"] < 0.80

        # General = low
        general = ConfidenceScorer().add_intent_match("general").build()
        assert general.factors["intent_match"] <= 0.60

    def test_tool_success_rate(self):
        """Should score tool success correctly."""
        # All tools succeed
        perfect = ConfidenceScorer().add_tool_success(1.0).build()
        assert perfect.factors["tool_success"] == 1.0
        assert len(perfect.warnings) == 0

        # Half tools fail
        partial = ConfidenceScorer().add_tool_success(0.5, failures=["git", "ls"]).build()
        assert partial.factors["tool_success"] == 0.5
        assert len(partial.warnings) > 0

    def test_warnings_accumulation(self):
        """Should accumulate warnings from multiple factors."""
        scorer = ConfidenceScorer()
        score = (scorer
                 .add_data_freshness(age_seconds=1000, verified=False)  # Warning: old + unverified
                 .add_verification_status(False)  # Warning: not verified
                 .add_intent_match("general")  # Warning: unclear intent
                 .add_tool_success(0.7, failures=["tool1"])  # Warning: some failed
                 .build())

        # Should have multiple warnings
        assert len(score.warnings) >= 3

    def test_chaining(self):
        """Should support method chaining (Builder pattern)."""
        scorer = ConfidenceScorer()

        # Should be able to chain methods
        result = (scorer
                  .add_data_freshness(age_seconds=5)
                  .add_verification_status(True)
                  .add_intent_match("exact")
                  .add_tool_success(1.0)
                  .build())

        assert isinstance(result.score, float)
        assert 0.0 <= result.score <= 1.0

    def test_to_dict(self):
        """Should convert to dict format."""
        scorer = ConfidenceScorer()
        score = scorer.add_data_freshness(age_seconds=10).build()

        result = score.to_dict()

        assert "score" in result
        assert "level" in result
        assert "factors" in result
        assert "reasoning" in result
        assert "warnings" in result


class TestConfidenceFromContext:
    """Tests for convenience function."""

    def test_create_from_fresh_context(self):
        """Should create confidence from fresh context."""
        context_result = {
            "status": "fresh",
            "age_seconds": 5.0,
            "verified": True
        }

        score = create_confidence_from_context(
            context_result=context_result,
            intent_match="exact",
            tool_success_rate=1.0
        )

        # Should be very high confidence
        assert score.level in [ConfidenceLevel.VERY_HIGH, ConfidenceLevel.HIGH]
        assert score.score > 0.80

    def test_create_from_stale_context(self):
        """Should create confidence from stale context."""
        context_result = {
            "status": "stale",
            "age_seconds": 300.0,
            "verified": True,
            "cached_value": "old",
            "live_value": "new"
        }

        score = create_confidence_from_context(
            context_result=context_result,
            intent_match="exact",
            tool_success_rate=1.0
        )

        # Should have warnings about staleness
        # But score should still be decent because it's verified
        assert score.score >= 0.50  # At least medium

    def test_create_without_context(self):
        """Should handle missing context gracefully."""
        score = create_confidence_from_context(
            context_result=None,
            intent_match="fuzzy",
            tool_success_rate=0.9
        )

        # Should still produce a score
        assert 0.0 <= score.score <= 1.0


class TestRealWorldScenarios:
    """Integration tests for real scenarios."""

    def test_scenario_fresh_verified_commit(self):
        """Scenario: Show last commit (just executed git log)."""
        scorer = ConfidenceScorer()
        score = (scorer
                 .add_data_freshness(age_seconds=2, verified=True)
                 .add_verification_status(True, verification_method="exact")
                 .add_intent_match("exact")
                 .add_tool_success(1.0)
                 .build())

        # Should be very high confidence
        assert score.level == ConfidenceLevel.VERY_HIGH
        assert score.score >= 0.90
        print(f"\nScenario 1: {score.reasoning}")
        print(f"  Warnings: {score.warnings or ['None']}")

    def test_scenario_cached_but_verified(self):
        """Scenario: Show cached commit (verified fresh 30s ago)."""
        scorer = ConfidenceScorer()
        score = (scorer
                 .add_data_freshness(age_seconds=30, verified=True)
                 .add_verification_status(True, verification_method="exact")
                 .add_intent_match("exact")
                 .add_tool_success(1.0)
                 .build())

        # Should be high confidence (slightly lower than fresh)
        assert score.level in [ConfidenceLevel.VERY_HIGH, ConfidenceLevel.HIGH]
        assert score.score >= 0.85
        print(f"\nScenario 2: {score.reasoning}")

    def test_scenario_stale_detected(self):
        """Scenario: Cached commit changed (verification detected staleness)."""
        scorer = ConfidenceScorer()
        score = (scorer
                 .add_data_freshness(age_seconds=200, verified=True)  # Old but verified
                 .add_verification_status(True, verification_method="exact")
                 .add_intent_match("exact")
                 .add_tool_success(1.0)
                 .build())

        # Should be high (verified even if old = still trustworthy!)
        assert score.level in [ConfidenceLevel.VERY_HIGH, ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM]
        assert score.score >= 0.75  # At least HIGH
        print(f"\nScenario 3: {score.reasoning}")

    def test_scenario_unverified_old_data(self):
        """Scenario: Claude Desktop style (old data, no verification)."""
        scorer = ConfidenceScorer()
        score = (scorer
                 .add_data_freshness(age_seconds=86400, verified=False)  # 24h old!
                 .add_verification_status(False)
                 .add_intent_match("general")  # Unclear intent
                 .add_tool_success(1.0)
                 .build())

        # Should be low confidence
        assert score.level in [ConfidenceLevel.LOW, ConfidenceLevel.VERY_LOW]
        assert len(score.warnings) >= 2  # Multiple warnings
        print(f"\nScenario 4 (Claude Desktop): {score.reasoning}")
        print(f"  Warnings: {score.warnings}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])  # -s shows print statements
