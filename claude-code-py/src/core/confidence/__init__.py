"""Confidence scoring system.

Provides transparency about how confident the system is in its answers:
- Data freshness scoring
- Verification status
- Intent match quality
- Tool execution success

Example:
    from core.confidence import ConfidenceScorer

    scorer = ConfidenceScorer()
    score = (scorer
             .add_data_freshness(age_seconds=5, verified=True)
             .add_intent_match("exact")
             .add_tool_success(1.0)
             .build())

    print(f"Confidence: {score.score:.0%}")
    if score.warnings:
        print(f"Warnings: {', '.join(score.warnings)}")
"""

from .scorer import (
    ConfidenceScorer,
    ConfidenceScore,
    ConfidenceLevel,
    create_confidence_from_context,
)

__all__ = [
    "ConfidenceScorer",
    "ConfidenceScore",
    "ConfidenceLevel",
    "create_confidence_from_context",
]
