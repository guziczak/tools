"""Query normalization for intent classification.

This module provides text normalization utilities for making intent matching
more robust to variations in word order, inflection, and typos.

Best Practices:
- Single Responsibility: Only does text normalization
- Pure functions: No side effects
- Testable: Easy to unit test
"""

from typing import List, Set
import re


class QueryNormalizer:
    """Normalizes user queries for intent matching.

    This makes intent matching word-order invariant and more flexible.
    Uses linguistic techniques like tokenization and stemming.
    """

    # Common Polish stop words that don't carry intent meaning
    POLISH_STOP_WORDS = {
        "czy",
        "to",
        "jest",
        "są",
        "było",
        "będzie",
        "w",
        "na",
        "do",
        "z",
        "ze",
        "o",
        "po",
        "dla",
        "od",
        "przez",
        "przy",
    }

    # Common English stop words
    ENGLISH_STOP_WORDS = {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "from",
    }

    STOP_WORDS = POLISH_STOP_WORDS | ENGLISH_STOP_WORDS

    @staticmethod
    def tokenize(text: str) -> List[str]:
        """Tokenize text into words.

        Args:
            text: Input text

        Returns:
            List of lowercase tokens
        """
        # Lowercase and split on whitespace/punctuation
        text = text.lower()
        # Remove punctuation except hyphens (for git-related terms)
        text = re.sub(r"[^\w\s-]", " ", text)
        tokens = text.split()
        return tokens

    @staticmethod
    def remove_stop_words(tokens: List[str]) -> List[str]:
        """Remove common stop words that don't carry intent.

        Args:
            tokens: List of tokens

        Returns:
            Filtered list without stop words
        """
        return [t for t in tokens if t not in QueryNormalizer.STOP_WORDS]

    @staticmethod
    def simple_stem(word: str) -> str:
        """Simple stemming for common Polish/English inflections.

        This is not a full stemmer, just handles common cases:
        - Polish: commita/commitów/ostatniego → commit/ostatni
        - English: commits/committed → commit

        Args:
            word: Word to stem

        Returns:
            Stemmed word
        """
        # Polish genitive/accusative endings (order matters - longest first!)
        # "ostatniego" → "ostatni" (remove "ego")
        # "commita" → "commit" (remove "a")
        for ending in ["ego", "ów", "em", "ach", "ie", "a", "u"]:
            if word.endswith(ending) and len(word) > len(ending) + 2:
                return word[: -len(ending)]

        # English plural/past tense
        for ending in ["ing", "ed", "s"]:  # order matters - longest first!
            if word.endswith(ending) and len(word) > len(ending) + 2:
                return word[: -len(ending)]

        return word

    @staticmethod
    def normalize(text: str, remove_stops: bool = True, stem: bool = True) -> Set[str]:
        """Normalize text to canonical token set.

        This makes matching word-order invariant:
        - "widzisz commita ostatniego" → {widzisz, commit, ostatni}
        - "ostatni commit widzisz" → {widzisz, commit, ostatni}
        Both produce the same set!

        Args:
            text: Input query
            remove_stops: Whether to remove stop words
            stem: Whether to apply simple stemming

        Returns:
            Set of normalized tokens
        """
        tokens = QueryNormalizer.tokenize(text)

        if remove_stops:
            tokens = QueryNormalizer.remove_stop_words(tokens)

        if stem:
            tokens = [QueryNormalizer.simple_stem(t) for t in tokens]

        return set(tokens)

    @staticmethod
    def contains_keywords(text: str, keywords: List[str]) -> bool:
        """Check if text contains all keywords (word-order invariant).

        Example:
            contains_keywords("widzisz commita ostatniego", ["ostatni", "commit"])
            → True (order doesn't matter!)

        Args:
            text: Input text
            keywords: List of required keywords

        Returns:
            True if all keywords present (any order)
        """
        normalized = QueryNormalizer.normalize(text)
        normalized_keywords = {QueryNormalizer.simple_stem(k.lower()) for k in keywords}

        return normalized_keywords.issubset(normalized)
