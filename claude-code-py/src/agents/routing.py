"""Agent routing logic - delegates tasks to specialized agents."""

from typing import Optional, Dict, Any, Iterator
from anthropic import Anthropic

from .base import BaseAgent, AgentResult
from .registry import AgentRegistry
from .thinking import detect_thinking_level, ThinkingLevel


class AgentRouter:
    """Routes tasks to appropriate specialized agents."""

    def __init__(self, agent_registry: AgentRegistry, client: Anthropic):
        """Initialize agent router.

        Args:
            agent_registry: Registry of available agents
            client: Anthropic API client
        """
        self.agent_registry = agent_registry
        self.client = client

    def route_to_agent(
        self,
        task: str,
        context: Optional[str],
        agent_name: str,
        model: str = "claude-sonnet-4-5-20241022",
        max_tokens: int = 8000,
    ) -> Iterator[Dict[str, Any]]:
        """Route task to specific agent.

        Args:
            task: Task description
            context: Optional context
            agent_name: Name of agent to use
            model: Model to use
            max_tokens: Maximum tokens

        Yields:
            Events from agent execution
        """
        # Get agent
        agent = self.agent_registry.get_agent(agent_name)
        if not agent:
            yield {"type": "error", "content": f"Agent not found: {agent_name}"}
            return

        # Detect thinking level from task
        thinking_level, explicit = detect_thinking_level(task)

        # Override with agent's thinking budget if higher
        thinking_budget = max(thinking_level.budget, agent.thinking_budget)

        # Yield agent selection info
        yield {
            "type": "agent_selected",
            "agent_name": agent.name,
            "agent_role": agent.role.value,
            "thinking_level": thinking_level.name,
            "thinking_budget": thinking_budget,
            "content": f"Delegating to {agent.name}",
        }

        # Build enhanced system prompt
        system_prompt = agent.get_enhanced_system_prompt(task, context)

        # Create user message
        user_message = task
        if context:
            user_message = f"{task}\n\nContext: {context}"

        # Call Claude with agent's configuration
        try:
            with self.client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                temperature=agent.config.temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
                thinking={"type": "enabled", "budget_tokens": thinking_budget},
            ) as stream:
                # Stream thinking
                for event in stream:
                    if event.type == "content_block_start":
                        if hasattr(event, "content_block"):
                            if event.content_block.type == "thinking":
                                yield {"type": "thinking_start", "content": ""}
                            elif event.content_block.type == "text":
                                yield {"type": "text_start", "content": ""}

                    elif event.type == "content_block_delta":
                        if hasattr(event, "delta"):
                            delta = event.delta
                            if hasattr(delta, "type"):
                                if delta.type == "text_delta":
                                    yield {"type": "text", "content": getattr(delta, "text", "")}
                                elif delta.type == "thinking_delta":
                                    yield {
                                        "type": "thinking",
                                        "content": getattr(delta, "thinking", ""),
                                    }

                    elif event.type == "message_stop":
                        yield {"type": "agent_complete", "content": ""}

        except Exception as e:
            yield {"type": "error", "content": f"Agent execution failed: {str(e)}"}

    def detect_agent_from_delegation(self, tool_name: str) -> Optional[BaseAgent]:
        """Detect agent from delegation tool call.

        Args:
            tool_name: Tool name (e.g., "delegate_to_test_writer")

        Returns:
            Agent instance or None
        """
        # Tool names are formatted as: delegate_to_{role}
        if not tool_name.startswith("delegate_to_"):
            return None

        role_name = tool_name.replace("delegate_to_", "")

        # Find agent by role
        for agent in self.agent_registry._agents.values():
            if agent.role.value == role_name:
                return agent

        return None
