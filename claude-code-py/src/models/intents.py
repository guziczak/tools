"""Intent classification result types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class IntentMatch:
    """Result of intent classification.

    Attributes:
        intent: Matched intent name (e.g., "git_log", "explore_project", "general")
        confidence: Confidence score (0.0-1.0)
        tool_choice: Optional API tool_choice parameter dict
        metadata: Match details (trigger, method, etc.)
    """

    intent: str
    confidence: float
    tool_choice: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
