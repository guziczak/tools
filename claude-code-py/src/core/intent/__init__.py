"""Intent classification module.

Uses LLM-based classification (Haiku) for intent detection.
"""

from .classifier import ConfigDrivenClassifier

__all__ = ["ConfigDrivenClassifier"]
