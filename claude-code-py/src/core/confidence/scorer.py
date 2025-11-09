"""Confidence scoring for responses.

Calculates how confident the system is in its answer based on:
- Data freshness (recently executed vs cached)
- Verification status (verified vs unverified)
- Intent match quality (exact vs fuzzy vs semantic)
- Tool execution success (all passed vs some failed)

This solves the "false confidence" problem where AI sounds certain
but is actually using stale/unverified data.

Best Practices:
- Strategy Pattern: Different scoring strategies per data type
- Composite Pattern: Combine multiple confidence factors
- Builder Pattern: Construct confidence score step by step
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


class ConfidenceLevel(Enum):
    """Confidence level categories."""
    VERY_HIGH = "very_high"    # 90-100%
    HIGH = "high"              # 75-89%
    MEDIUM = "medium"          # 50-74%
    LOW = "low"                # 25-49%
    VERY_LOW = "very_low"      # 0-24%


@dataclass
class ConfidenceScore:
    """Confidence score for a response.

    Attributes:
        score: Overall confidence (0.0-1.0)
        level: Confidence level category
        factors: Individual factors that contributed to score
        reasoning: Human-readable explanation
        warnings: Any warnings about data quality
    """
    score: float  # 0.0-1.0
    level: ConfidenceLevel
    factors: Dict[str, float]
    reasoning: str
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "score": self.score,
            "level": self.level.value,
            "factors": self.factors,
            "reasoning": self.reasoning,
            "warnings": self.warnings
        }


class ConfidenceScorer:
    """Calculates confidence scores for responses.

    Example:
        scorer = ConfidenceScorer()

        # Build confidence score
        score = (scorer
                 .add_data_freshness(age_seconds=5, verified=True)
                 .add_intent_match(match_type="exact")
                 .add_tool_success(success_rate=1.0)
                 .build())

        print(f"Confidence: {score.score:.0%} ({score.level.value})")
        print(f"Reasoning: {score.reasoning}")
    """

    def __init__(self):
        """Initialize scorer."""
        self.factors: Dict[str, float] = {}
        self.warnings: List[str] = []
        self.weights: Dict[str, float] = {
            "data_freshness": 0.4,   # Most important (prevents stale data)
            "verification": 0.3,      # Second most important
            "intent_match": 0.2,      # Important for correct handling
            "tool_success": 0.1       # Least important (usually succeeds)
        }

    def add_data_freshness(
        self,
        age_seconds: float,
        verified: bool = False,
        ttl_seconds: Optional[float] = None
    ) -> "ConfidenceScorer":
        """Add data freshness factor.

        Args:
            age_seconds: How old the data is
            verified: Whether data was verified fresh
            ttl_seconds: TTL threshold (optional)

        Returns:
            Self for chaining
        """
        # Base score: newer = higher confidence
        if age_seconds <= 5:
            freshness_score = 1.0  # < 5s = very fresh
        elif age_seconds <= 60:
            freshness_score = 0.9  # < 1min = fresh
        elif age_seconds <= 300:
            freshness_score = 0.7  # < 5min = acceptable
        elif age_seconds <= 3600:
            freshness_score = 0.5  # < 1h = getting old
        else:
            freshness_score = 0.2  # > 1h = stale

        # Boost if verified
        if verified:
            freshness_score = min(1.0, freshness_score + 0.1)
        else:
            self.warnings.append(f"Data not verified (age: {age_seconds:.0f}s)")

        # Warn if near/past TTL
        if ttl_seconds and age_seconds > ttl_seconds * 0.8:
            self.warnings.append(f"Data approaching TTL ({age_seconds:.0f}s / {ttl_seconds:.0f}s)")

        self.factors["data_freshness"] = freshness_score
        return self

    def add_verification_status(
        self,
        verified: bool,
        verification_method: Optional[str] = None
    ) -> "ConfidenceScorer":
        """Add verification status factor.

        Args:
            verified: Whether data was verified
            verification_method: How it was verified (optional)

        Returns:
            Self for chaining
        """
        if verified:
            # Different verification methods have different confidence
            if verification_method == "exact":
                score = 1.0  # Exact match = 100% confidence
            elif verification_method == "hash":
                score = 0.95  # Hash match = 95% confidence
            else:
                score = 0.9  # Unspecified verification = 90%
        else:
            score = 0.3  # No verification = low confidence
            self.warnings.append("Data not verified - may be stale")

        self.factors["verification"] = score
        return self

    def add_intent_match(
        self,
        match_type: str,
        confidence: Optional[float] = None
    ) -> "ConfidenceScorer":
        """Add intent matching factor.

        Args:
            match_type: Type of match ("exact", "fuzzy", "semantic", "general")
            confidence: Optional confidence from matcher (0-1)

        Returns:
            Self for chaining
        """
        # Map match type to confidence
        type_scores = {
            "exact": 1.0,      # Exact trigger match
            "fuzzy": 0.85,     # Fuzzy match (caught typo)
            "keyword": 0.80,   # Keyword match (word-order invariant)
            "semantic": 0.70,  # Semantic similarity
            "general": 0.50    # Let Claude decide
        }

        score = type_scores.get(match_type, 0.50)

        # Override with explicit confidence if provided
        if confidence is not None:
            score = confidence

        if match_type == "general":
            self.warnings.append("Intent unclear - Claude may misinterpret")

        self.factors["intent_match"] = score
        return self

    def add_tool_success(
        self,
        success_rate: float,
        failures: Optional[List[str]] = None
    ) -> "ConfidenceScorer":
        """Add tool execution success factor.

        Args:
            success_rate: Ratio of successful tool calls (0-1)
            failures: List of failed tool names (optional)

        Returns:
            Self for chaining
        """
        self.factors["tool_success"] = success_rate

        if success_rate < 1.0:
            if failures:
                self.warnings.append(f"Some tools failed: {', '.join(failures)}")
            else:
                self.warnings.append(f"Tool success rate: {success_rate:.0%}")

        return self

    def build(self) -> ConfidenceScore:
        """Build final confidence score.

        Returns:
            ConfidenceScore with overall score and reasoning
        """
        # Calculate weighted average
        total_weight = 0.0
        weighted_sum = 0.0

        for factor_name, factor_score in self.factors.items():
            weight = self.weights.get(factor_name, 0.1)
            weighted_sum += factor_score * weight
            total_weight += weight

        # Normalize if weights don't sum to 1.0
        if total_weight > 0:
            overall_score = weighted_sum / total_weight
        else:
            overall_score = 0.5  # Default: medium confidence

        # Determine level
        if overall_score >= 0.90:
            level = ConfidenceLevel.VERY_HIGH
        elif overall_score >= 0.75:
            level = ConfidenceLevel.HIGH
        elif overall_score >= 0.50:
            level = ConfidenceLevel.MEDIUM
        elif overall_score >= 0.25:
            level = ConfidenceLevel.LOW
        else:
            level = ConfidenceLevel.VERY_LOW

        # Build reasoning
        reasoning = self._build_reasoning(overall_score, level)

        return ConfidenceScore(
            score=overall_score,
            level=level,
            factors=self.factors.copy(),
            reasoning=reasoning,
            warnings=self.warnings.copy()
        )

    def _build_reasoning(self, score: float, level: ConfidenceLevel) -> str:
        """Build human-readable reasoning for score.

        Args:
            score: Overall score
            level: Confidence level

        Returns:
            Reasoning string
        """
        # Find strongest and weakest factors
        if self.factors:
            strongest = max(self.factors.items(), key=lambda x: x[1])
            weakest = min(self.factors.items(), key=lambda x: x[1])

            reasoning_parts = [
                f"Confidence: {score:.0%} ({level.value})",
                f"Strongest: {strongest[0]} ({strongest[1]:.0%})",
                f"Weakest: {weakest[0]} ({weakest[1]:.0%})"
            ]

            return " | ".join(reasoning_parts)
        else:
            return f"Confidence: {score:.0%} ({level.value}) - no factors evaluated"


def create_confidence_from_context(
    context_result: Optional[Dict[str, Any]] = None,
    intent_match: Optional[str] = None,
    tool_success_rate: float = 1.0
) -> ConfidenceScore:
    """Convenience function to create confidence score from context.

    Args:
        context_result: Result from ContextManager.get_verified()
        intent_match: Intent match type ("exact", "fuzzy", etc.)
        tool_success_rate: Tool execution success rate (0-1)

    Returns:
        ConfidenceScore
    """
    scorer = ConfidenceScorer()

    # Add data freshness if context provided
    if context_result:
        age = context_result.get("age_seconds", 0)
        verified = context_result.get("verified", False)
        status = context_result.get("status", "unknown")

        scorer.add_data_freshness(age, verified=verified)

        if status == "fresh":
            scorer.add_verification_status(True, verification_method="exact")
        elif status == "stale":
            scorer.add_verification_status(True, verification_method="exact")
            # Note: score already lower due to staleness warning
        else:
            scorer.add_verification_status(False)

    # Add intent match
    if intent_match:
        scorer.add_intent_match(intent_match)

    # Add tool success
    scorer.add_tool_success(tool_success_rate)

    return scorer.build()
