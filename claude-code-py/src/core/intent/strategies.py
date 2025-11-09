"""Intent matching strategies (Strategy Pattern).

This module defines abstract interfaces for intent matching strategies,
following the Strategy Pattern for maximum flexibility and testability.

Design Patterns:
- Strategy Pattern: Different matching algorithms as interchangeable strategies
- Open/Closed Principle: Open for extension (add new matchers), closed for modification

Best Practices:
- Dependency Inversion: Depend on abstractions (MatcherStrategy), not concrete classes
- Single Responsibility: Each matcher focuses on ONE matching approach
- Interface Segregation: Small, focused interfaces
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from dataclasses import dataclass


@dataclass
class IntentMatch:
    """Result of intent matching.

    Attributes:
        intent: Matched intent name (e.g., "git_log", "explore_project")
        confidence: Confidence score (0.0-1.0)
        metadata: Optional metadata about the match (trigger used, distance, etc.)
    """

    intent: str
    confidence: float
    metadata: Optional[dict] = None


class MatcherStrategy(ABC):
    """Abstract base class for intent matching strategies.

    This allows us to easily add new matching strategies without modifying
    existing code (Open/Closed Principle).
    """

    @abstractmethod
    def match(self, query: str) -> Optional[IntentMatch]:
        """Attempt to match query to an intent.

        Args:
            query: User's query text

        Returns:
            IntentMatch if matched, None otherwise
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get matcher name (for debugging/logging).

        Returns:
            Human-readable matcher name
        """
        pass


class IntentClassifier:
    """Classifies user intent using multiple matcher strategies.

    This is the Context in the Strategy Pattern - it delegates matching
    to concrete strategy implementations.

    Architecture:
    - Tries matchers in order (fast to slow)
    - Returns first match with confidence >= threshold
    - Falls back to "general" intent if no match

    Example:
        classifier = IntentClassifier()
        classifier.add_matcher(ExactMatcher(...))
        classifier.add_matcher(FuzzyMatcher(...))

        result = classifier.classify("widzisz ostatniego commita?")
        # => IntentMatch(intent="git_log", confidence=0.95)
    """

    def __init__(self, matchers: Optional[List[MatcherStrategy]] = None):
        """Initialize classifier with matchers.

        Args:
            matchers: List of matcher strategies (ordered by priority)
        """
        self.matchers: List[MatcherStrategy] = matchers or []

    def add_matcher(self, matcher: MatcherStrategy) -> None:
        """Add a matcher strategy.

        Matchers are tried in order, so add fastest matchers first.

        Args:
            matcher: Matcher strategy to add
        """
        self.matchers.append(matcher)

    def classify(self, query: str, confidence_threshold: float = 0.5) -> IntentMatch:
        """Classify user query intent.

        Tries matchers in order and returns first match with sufficient confidence.

        Args:
            query: User's query text
            confidence_threshold: Minimum confidence to accept match

        Returns:
            IntentMatch with classified intent
        """
        # Try each matcher in order
        for matcher in self.matchers:
            result = matcher.match(query)

            if result and result.confidence >= confidence_threshold:
                # Found match with sufficient confidence
                return result

        # No match found - return general intent
        return IntentMatch(
            intent="general", confidence=1.0, metadata={"reason": "no_matcher_found"}
        )
