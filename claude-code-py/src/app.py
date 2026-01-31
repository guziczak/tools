"""Application orchestrator with dependency injection.

Wires together all components. ``ClaudeCodePy`` in ``main.py``
delegates initialization here.
"""

from __future__ import annotations

from typing import Optional

from core.logging import get_logger
from config.app_config import AppConfig
from core.conversation import ConversationManager

logger = get_logger(__name__)


class Application:
    """Wires together all components via constructor injection."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.conversation = ConversationManager()

        self.tool_registry = None
        self.agent_registry = None
        self.agent_router = None
        self._api_client = None

    def initialize(self, api_key: str) -> bool:
        """Initialize tools, agents, proxy, and API client.

        Returns True on success.
        """
        from tools import create_default_registry
        from agents import AgentRegistry, AgentRouter
        from agents.prebuilt import create_default_agents

        # Tools
        if self.config.tools_enabled:
            self.tool_registry = create_default_registry(self.config.platform)
            logger.info("Tools enabled (%d tools)", len(self.tool_registry))

        # Agents
        if self.config.agents_enabled:
            self.agent_registry = AgentRegistry()
            for agent in create_default_agents():
                self.agent_registry.register(agent)
            logger.info("Agents enabled (%d agents)", len(self.agent_registry))

        # Tool definitions for API
        tools = None
        if self.tool_registry:
            tools = self.tool_registry.get_anthropic_tools()
        if self.agent_registry:
            agent_tools = self.agent_registry.get_anthropic_tools()
            tools = (tools or []) + agent_tools

        # Proxy
        from auth.proxy_manager import start_proxy_if_needed
        start_proxy_if_needed(api_key)

        # API client (internally creates ChatPipeline)
        try:
            from core.api_client import ClaudeAPIClient

            self._api_client = ClaudeAPIClient(
                api_key=api_key,
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                thinking_enabled=self.config.thinking_enabled,
                thinking_budget=self.config.thinking_budget,
                tools=tools,
                tool_registry=self.tool_registry,
            )
            # Share conversation manager
            self._api_client._conversation = self.conversation
        except Exception as exc:
            logger.error("Failed to initialize API client: %s", exc)
            return False

        return True

    @property
    def client(self):
        """The API client (thin facade over ChatPipeline)."""
        return self._api_client
