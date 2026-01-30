"""Application configuration as a frozen dataclass."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    """Immutable application configuration.

    All settings are loaded once from environment variables via ``from_env()``.
    """

    api_key: str
    model: str = "claude-sonnet-4-5-20241022"
    max_tokens: int = 8000
    temperature: float = 1.0
    thinking_enabled: bool = True
    thinking_budget: int = 10000
    use_oauth: bool = False
    tools_enabled: bool = True
    agents_enabled: bool = True

    @classmethod
    def from_env(cls) -> AppConfig:
        """Build config from environment variables.

        Raises:
            ValueError: If ANTHROPIC_API_KEY is not set and no OAuth token found.
        """
        api_key = (
            os.getenv("ANTHROPIC_API_KEY", "")
            or os.getenv("CLAUDE_CODE_OAUTH_TOKEN", "")
        )

        return cls(
            api_key=api_key,
            model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5-20241022"),
            max_tokens=int(os.getenv("CLAUDE_MAX_TOKENS", "8000")),
            temperature=float(os.getenv("CLAUDE_TEMPERATURE", "1.0")),
            thinking_enabled=os.getenv("CLAUDE_THINKING_ENABLED", "true").lower() == "true",
            thinking_budget=int(os.getenv("CLAUDE_THINKING_BUDGET", "10000")),
            use_oauth=os.getenv("CLAUDE_USE_OAUTH", "false").lower() == "true",
            tools_enabled=os.getenv("CLAUDE_TOOLS_ENABLED", "true").lower() == "true",
            agents_enabled=os.getenv("CLAUDE_AGENTS_ENABLED", "true").lower() == "true",
        )
