"""Thinking level detection and management."""

from enum import Enum
from typing import Tuple
import re


class ThinkingLevel(Enum):
    """Extended thinking levels."""

    NONE = (0, "No extended thinking")
    BASIC = (4000, "Basic thinking - quick analysis")
    STANDARD = (10000, "Standard thinking - thorough analysis")
    DEEP = (20000, "Deep thinking - comprehensive analysis")
    ULTRA = (32000, "Ultra thinking - maximum reasoning")

    def __init__(self, budget: int, description: str):
        self.budget = budget
        self.description = description


# Keywords that trigger different thinking levels
THINKING_KEYWORDS = {
    ThinkingLevel.ULTRA: [
        "ultrathink", "ultra think", "think ultra", "maximum thinking",
        "think harder", "think hardest", "megathink"
    ],
    ThinkingLevel.DEEP: [
        "think deep", "deep think", "think carefully", "think thoroughly",
        "analyze deeply", "deep analysis"
    ],
    ThinkingLevel.STANDARD: [
        "think hard", "think about", "consider carefully",
        "analyze this", "reason about"
    ],
    ThinkingLevel.BASIC: [
        "think", "consider", "analyze", "evaluate"
    ],
}


def detect_thinking_level(message: str) -> Tuple[ThinkingLevel, bool]:
    """Detect thinking level from user message.

    Args:
        message: User's message

    Returns:
        Tuple of (ThinkingLevel, was_explicitly_requested)
    """
    message_lower = message.lower()

    # Check for explicit thinking keywords in order of precedence
    for level, keywords in THINKING_KEYWORDS.items():
        for keyword in keywords:
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, message_lower):
                return (level, True)

    # Check if message suggests complex task (implicit thinking)
    complex_indicators = [
        r'\b(refactor|redesign|architect)\b',
        r'\b(complex|complicated|difficult)\b',
        r'\b(comprehensive|thorough|detailed)\b',
        r'\b(optimize|improve significantly)\b',
        r'\b(multiple|several) .*(files|components|modules)\b',
    ]

    for pattern in complex_indicators:
        if re.search(pattern, message_lower):
            return (ThinkingLevel.STANDARD, False)

    # Default: basic thinking for agent tasks, none for simple queries
    if len(message.split()) > 20 or '?' not in message:
        # Longer statements or commands suggest tasks
        return (ThinkingLevel.BASIC, False)

    return (ThinkingLevel.NONE, False)


def get_thinking_budget(level: ThinkingLevel) -> int:
    """Get token budget for thinking level.

    Args:
        level: Thinking level

    Returns:
        Token budget
    """
    return level.budget


def format_thinking_request(level: ThinkingLevel, explicit: bool) -> str:
    """Format thinking level info for display.

    Args:
        level: Thinking level
        explicit: Whether explicitly requested

    Returns:
        Formatted string
    """
    if level == ThinkingLevel.NONE:
        return "No extended thinking"

    mode = "Explicit" if explicit else "Auto-detected"
    return f"{mode}: {level.name} ({level.budget:,} tokens) - {level.description}"
