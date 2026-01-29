"""Factory for creating the appropriate LLM client."""

from __future__ import annotations

from typing import Any

from core.logging import get_logger

logger = get_logger(__name__)


def _is_oauth_token(token: str) -> bool:
    """Check if token is an OAuth token or session key."""
    return token.startswith("sk-ant-oat") or token.startswith("sk-ant-sid01-")


def create_client(
    api_key: str,
    model: str,
    max_tokens: int = 8000,
    temperature: float = 1.0,
    thinking_enabled: bool = True,
    thinking_budget: int = 10000,
) -> Any:
    """Create the appropriate LLM client based on token type.

    Returns:
        Either ``AnthropicKeyClient`` or ``OAuthLLMClient``.
    """
    if _is_oauth_token(api_key):
        from .oauth_client import OAuthLLMClient

        logger.debug("Creating OAuth client")
        return OAuthLLMClient(
            token=api_key,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            thinking_enabled=thinking_enabled,
            thinking_budget=thinking_budget,
        )
    else:
        from .api_key_client import AnthropicKeyClient

        logger.debug("Creating API key client")
        return AnthropicKeyClient(
            api_key=api_key,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            thinking_enabled=thinking_enabled,
            thinking_budget=thinking_budget,
        )
