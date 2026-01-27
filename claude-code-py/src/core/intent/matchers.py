"""Concrete intent matcher implementations.

This module provides concrete implementations of MatcherStrategy interface:
- ExactMatcher: Fast O(1) exact string matching
- FuzzyMatcher: Typo-tolerant matching using fuzzywuzzy
- SemanticMatcher: Keyword-based semantic matching

Best Practices:
- Single Responsibility: Each matcher focuses on ONE matching technique
- Dependency Injection: Matchers receive configuration via constructor
- Immutability: Matchers are stateless and thread-safe
"""

from typing import Optional, List, Dict, Set, Union
from .strategies import MatcherStrategy, IntentMatch
from core.query_normalizer import QueryNormalizer
from core.logging import get_logger

logger = get_logger(__name__)


class ExactMatcher(MatcherStrategy):
    """Exact string matching (Tier 1 - fastest).

    Matches exact phrases like "widzisz projekt", "git log", etc.
    This is the fast path - O(1) lookup in dict.

    Example:
        matcher = ExactMatcher({
            "git_log": ["ostatni commit", "git log", "commit history"],
            "explore_project": ["widzisz projekt", "show project"]
        })
        result = matcher.match("git log")
        # => IntentMatch(intent="git_log", confidence=1.0)
    """

    def __init__(self, trigger_map: Dict[str, List[str]]):
        """Initialize with trigger phrases.

        Args:
            trigger_map: Dict mapping intent name to list of trigger phrases
                Example: {"git_log": ["ostatni commit", "git log"]}
        """
        self.trigger_map = trigger_map

    def match(self, query: str) -> Optional[IntentMatch]:
        """Try exact matching against triggers.

        Args:
            query: User's query

        Returns:
            IntentMatch if exact match found, None otherwise
        """
        query_lower = query.lower().strip()

        # Check each intent's triggers
        for intent, triggers in self.trigger_map.items():
            for trigger in triggers:
                if trigger.lower() in query_lower:
                    return IntentMatch(
                        intent=intent,
                        confidence=1.0,
                        metadata={"trigger": trigger, "method": "exact"},
                    )

        return None

    def get_name(self) -> str:
        return "ExactMatcher"


class FuzzyMatcher(MatcherStrategy):
    """Fuzzy string matching (Tier 1.5 - typo tolerant).

    Uses fuzzywuzzy for Levenshtein distance-based matching.
    Catches typos like "widziszi" -> "widzisz", "commita" -> "commit".

    This is MUCH better than manual Levenshtein implementation:
    - Optimized C implementation (faster)
    - Proper Unicode handling
    - Battle-tested library

    Example:
        matcher = FuzzyMatcher(
            trigger_map={"git_log": ["ostatni commit"]},
            threshold=85
        )
        result = matcher.match("ostatniego commita")  # Typo!
        # => IntentMatch(intent="git_log", confidence=0.92)
    """

    def __init__(self, trigger_map: Dict[str, List[str]], threshold: int = 85):
        """Initialize fuzzy matcher.

        Args:
            trigger_map: Dict mapping intent to triggers
            threshold: Minimum similarity score (0-100) to consider a match
        """
        self.trigger_map = trigger_map
        self.threshold = threshold

        # Try to import fuzzywuzzy
        try:
            from fuzzywuzzy import fuzz

            self.fuzz = fuzz
            self.available = True
        except ImportError:
            self.available = False
            logger.debug(
                "FuzzyMatcher unavailable (missing fuzzywuzzy). "
                "Install with: pip install fuzzywuzzy python-Levenshtein"
            )

    def match(self, query: str) -> Optional[IntentMatch]:
        """Try fuzzy matching against triggers.

        Args:
            query: User's query

        Returns:
            IntentMatch if fuzzy match found, None otherwise
        """
        if not self.available:
            return None

        query_lower = query.lower().strip()
        best_match = None
        best_score = 0

        # Check each intent's triggers
        for intent, triggers in self.trigger_map.items():
            for trigger in triggers:
                # Calculate similarity score (0-100)
                score = self.fuzz.partial_ratio(query_lower, trigger.lower())

                if score >= self.threshold and score > best_score:
                    best_match = IntentMatch(
                        intent=intent,
                        confidence=score / 100.0,  # Normalize to 0-1
                        metadata={"trigger": trigger, "score": score, "method": "fuzzy"},
                    )
                    best_score = score

        return best_match

    def get_name(self) -> str:
        return "FuzzyMatcher"


class KeywordMatcher(MatcherStrategy):
    """Keyword-based semantic matching (Tier 2).

    Matches queries containing specific keywords, regardless of order.
    This is word-order invariant:
    - "widzisz ostatniego commita?" -> {widzisz, ostatni, commit} ✅
    - "ostatni commit widzisz?" -> {widzisz, ostatni, commit} ✅

    Example:
        matcher = KeywordMatcher({
            "git_log": [["ostatni", "commit"], ["git", "log"]],
            "explore_project": [["widzisz", "projekt"]]
        })
        result = matcher.match("ostatni commit widzisz?")  # Order doesn't matter!
        # => IntentMatch(intent="git_log", confidence=0.8)
    """

    def __init__(self, keyword_map: Dict[str, List[List[str]]]):
        """Initialize keyword matcher.

        Args:
            keyword_map: Dict mapping intent to list of keyword sets
                Example: {"git_log": [["ostatni", "commit"], ["git", "log"]]}
                A match requires ALL keywords in at least one set to be present
        """
        self.keyword_map = keyword_map

    def match(self, query: str) -> Optional[IntentMatch]:
        """Try keyword matching.

        Args:
            query: User's query

        Returns:
            IntentMatch if keywords found, None otherwise
        """
        # Tokenize query (simple word splitting)
        words = set(query.lower().split())

        # Check each intent's keyword sets
        for intent, keyword_sets in self.keyword_map.items():
            for keyword_set in keyword_sets:
                # Check if ALL keywords in this set are present
                keywords_lower = [kw.lower() for kw in keyword_set]

                if all(any(kw in word for word in words) for kw in keywords_lower):
                    # All keywords found - match!
                    return IntentMatch(
                        intent=intent,
                        confidence=0.8,  # Medium confidence
                        metadata={"keywords": keyword_set, "method": "keyword"},
                    )

        return None

    def get_name(self) -> str:
        return "KeywordMatcher"


class SemanticMatcher(MatcherStrategy):
    """Semantic similarity matching using Jaccard similarity (Tier 2.5).

    Calculates word overlap between query and reference queries.
    This is lightweight and doesn't require embeddings.

    For production, you'd use actual embeddings (OpenAI, Anthropic),
    but this is good enough for MVP.

    Example:
        matcher = SemanticMatcher(
            reference_map={
                "explore_project": [
                    "show project files",
                    "what is in this project"
                ]
            },
            threshold=0.4
        )
        result = matcher.match("show me project")
        # => IntentMatch(intent="explore_project", confidence=0.67)
    """

    def __init__(self, reference_map: Dict[str, List[str]], threshold: float = 0.4):
        """Initialize semantic matcher.

        Args:
            reference_map: Dict mapping intent to reference queries
            threshold: Minimum Jaccard similarity (0-1) to consider a match
        """
        self.reference_map = reference_map
        self.threshold = threshold

    def match(self, query: str) -> Optional[IntentMatch]:
        """Try semantic matching using word overlap.

        Args:
            query: User's query

        Returns:
            IntentMatch if semantically similar, None otherwise
        """
        query_words = set(query.lower().split())
        best_match = None
        best_similarity = 0.0

        # Check each intent's reference queries
        for intent, references in self.reference_map.items():
            for reference in references:
                ref_words = set(reference.lower().split())

                if not ref_words:
                    continue

                # Calculate Jaccard similarity: |A ∩ B| / |A ∪ B|
                intersection = len(query_words & ref_words)
                union = len(query_words | ref_words)
                similarity = intersection / union if union > 0 else 0

                if similarity >= self.threshold and similarity > best_similarity:
                    best_match = IntentMatch(
                        intent=intent,
                        confidence=similarity,
                        metadata={
                            "reference": reference,
                            "similarity": similarity,
                            "method": "semantic",
                        },
                    )
                    best_similarity = similarity

        return best_match

    def get_name(self) -> str:
        return "SemanticMatcher"


class NormalizedKeywordMatcher(MatcherStrategy):
    """Keyword matcher using QueryNormalizer (accent-stripping + stemming).

    Supports keyword sets with alternative groups, e.g.:
      ["zawartosc", ["folder", "katalog", "dir"]]
    which means zawartosc AND (folder OR katalog OR dir).
    """

    def __init__(self, keyword_map: Dict[str, List[List[Union[str, List[str]]]]]):
        self.keyword_map = keyword_map

    def _normalize_token(self, token: str) -> str:
        stripped = QueryNormalizer.strip_accents(token.lower())
        return QueryNormalizer.simple_stem(stripped)

    def _matches_set(self, normalized: Set[str], keyword_set: List[Union[str, List[str]]]) -> bool:
        for kw in keyword_set:
            if isinstance(kw, list):
                if not any(self._normalize_token(item) in normalized for item in kw):
                    return False
            else:
                if self._normalize_token(kw) not in normalized:
                    return False
        return True

    def match(self, query: str) -> Optional[IntentMatch]:
        normalized = QueryNormalizer.normalize(query)

        for intent, keyword_sets in self.keyword_map.items():
            for keyword_set in keyword_sets:
                if self._matches_set(normalized, keyword_set):
                    return IntentMatch(
                        intent=intent,
                        confidence=0.85,
                        metadata={"keywords": keyword_set, "method": "normalized_keyword"},
                    )

        return None

    def get_name(self) -> str:
        return "NormalizedKeywordMatcher"
