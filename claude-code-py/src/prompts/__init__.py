"""Prompt templates system for Claude Code Python.

Provides reusable prompt templates for common tasks.
"""

from .templates import (
    PromptTemplate,
    TEMPLATES,
    format_prompt,
    use_template,
    CODE_ASSISTANT_SYSTEM_PROMPT,
    CODE_GENERATION_SYSTEM_PROMPT,
    CODE_REVIEW_SYSTEM_PROMPT,
    CODE_EXPLANATION_SYSTEM_PROMPT,
)

__all__ = [
    "PromptTemplate",
    "TEMPLATES",
    "format_prompt",
    "use_template",
    "CODE_ASSISTANT_SYSTEM_PROMPT",
    "CODE_GENERATION_SYSTEM_PROMPT",
    "CODE_REVIEW_SYSTEM_PROMPT",
    "CODE_EXPLANATION_SYSTEM_PROMPT",
]
