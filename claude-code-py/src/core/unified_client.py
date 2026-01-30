"""Unified API client supporting both API keys and OAuth tokens."""

from typing import Iterator, Optional, Dict, Any, List
from anthropic import Anthropic
from anthropic.types import MessageStreamEvent

from .oauth_anthropic_client import OAuthAnthropicClient, is_oauth_token
from .logging import get_logger
from client.event_converter import convert_anthropic_event

logger = get_logger(__name__)


class UnifiedClaudeClient:
    """Unified client that supports both API keys and OAuth tokens.

    Automatically detects token type and uses appropriate backend:
    - API keys (sk-ant-api03-*): Use official Anthropic Python library
    - OAuth tokens (sk-ant-oat01-*): Use custom Claude.ai client
    """

    def __init__(
        self,
        token: str,
        model: str = "claude-sonnet-4-5-20241022",
        max_tokens: int = 8000,
        temperature: float = 1.0,
        thinking_enabled: bool = True,
        thinking_budget: int = 10000,
    ):
        """Initialize unified client.

        Args:
            token: API key or OAuth token
            model: Model to use
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            thinking_enabled: Enable extended thinking
            thinking_budget: Token budget for thinking
        """
        self.token = token
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.thinking_enabled = thinking_enabled
        self.thinking_budget = thinking_budget

        # Detect token type
        self.is_oauth = is_oauth_token(token)

        # Initialize appropriate backend
        if self.is_oauth:
            # Use OAuth client (Bearer auth with /v1/messages)
            self.backend = OAuthAnthropicClient(token)
            self.backend_type = "oauth"
        else:
            # Use official Anthropic library for API keys
            self.backend = Anthropic(api_key=token)
            self.backend_type = "anthropic"

    def chat_streaming(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> Iterator[Dict[str, Any]]:
        """Send chat message and stream response.

        Args:
            messages: List of message dicts with 'role' and 'content'
            system: Optional system prompt
            tools: Optional tool definitions (Anthropic format)
            **kwargs: Additional parameters

        Yields:
            Event dicts with streaming response
        """
        logger.debug(
            "chat_streaming called. backend_type=%s, backend=%s",
            self.backend_type,
            type(self.backend).__name__,
        )

        # Extract tool_choice from kwargs (state-of-the-art intent classification)
        tool_choice = kwargs.get("tool_choice", None)

        if self.backend_type == "oauth":
            logger.debug("Using OAuth backend")
            # Use OAuth backend (Bearer auth with tools support)
            yield from self.backend.chat_streaming(
                messages=messages,
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system,
                thinking_enabled=self.thinking_enabled,
                thinking_budget=self.thinking_budget,
                tools=tools,  # Pass tools to OAuth backend
                tool_choice=tool_choice,  # Pass tool_choice for forced execution
            )
        else:
            # Use Anthropic backend (API key)
            yield from self._anthropic_chat_streaming(messages, system, tools=tools, **kwargs)

    def _anthropic_chat_streaming(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> Iterator[Dict[str, Any]]:
        """Chat using Anthropic backend.

        Args:
            messages: Messages list
            system: System prompt
            tools: Tool definitions
            **kwargs: Additional parameters

        Yields:
            Event dicts
        """
        # Prepare request parameters
        request_params = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": messages,
        }

        # Add system prompt if provided
        if system:
            request_params["system"] = system

        # Add extended thinking if enabled
        if self.thinking_enabled:
            request_params["thinking"] = {"type": "enabled", "budget_tokens": self.thinking_budget}

        # Add tools if provided
        if tools:
            request_params["tools"] = tools

        # Stream the response
        with self.backend.messages.stream(**request_params) as stream:
            for event in stream:
                ev = convert_anthropic_event(event)
                if ev:
                    yield ev

    def get_backend_info(self) -> Dict[str, str]:
        """Get information about active backend.

        Returns:
            Dict with backend info
        """
        return {
            "backend_type": self.backend_type,
            "token_type": "OAuth" if self.is_oauth else "API Key",
            "model": self.model,
        }
