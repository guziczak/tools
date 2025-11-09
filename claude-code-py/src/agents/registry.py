"""Agent registry for managing specialized agents."""

from typing import Dict, List, Optional, Tuple
from .base import BaseAgent, AgentRole


class AgentRegistry:
    """Registry for managing agents."""

    def __init__(self):
        """Initialize agent registry."""
        self._agents: Dict[str, BaseAgent] = {}
        self._agents_by_role: Dict[AgentRole, List[BaseAgent]] = {}

    def register(self, agent: BaseAgent) -> None:
        """Register an agent.

        Args:
            agent: Agent to register
        """
        self._agents[agent.name] = agent

        # Also register by role
        if agent.role not in self._agents_by_role:
            self._agents_by_role[agent.role] = []
        self._agents_by_role[agent.role].append(agent)

    def unregister(self, agent_name: str) -> bool:
        """Unregister an agent.

        Args:
            agent_name: Name of agent to unregister

        Returns:
            True if agent was unregistered
        """
        if agent_name in self._agents:
            agent = self._agents[agent_name]
            del self._agents[agent_name]

            # Remove from role list
            if agent.role in self._agents_by_role:
                self._agents_by_role[agent.role] = [
                    a for a in self._agents_by_role[agent.role] if a.name != agent_name
                ]

            return True
        return False

    def get_agent(self, agent_name: str) -> Optional[BaseAgent]:
        """Get agent by name.

        Args:
            agent_name: Name of agent

        Returns:
            Agent instance or None
        """
        return self._agents.get(agent_name)

    def get_agents_by_role(self, role: AgentRole) -> List[BaseAgent]:
        """Get all agents with a specific role.

        Args:
            role: Agent role

        Returns:
            List of agents with that role
        """
        return self._agents_by_role.get(role, [])

    def list_agents(self) -> List[str]:
        """List all registered agent names.

        Returns:
            List of agent names
        """
        return list(self._agents.keys())

    def find_best_agent(self, task_description: str) -> Optional[Tuple[BaseAgent, float]]:
        """Find best agent for a task.

        Args:
            task_description: Description of the task

        Returns:
            Tuple of (agent, confidence) or None if no suitable agent
        """
        best_agent = None
        best_score = 0.0

        for agent in self._agents.values():
            score = agent.can_handle(task_description)
            if score > best_score:
                best_score = score
                best_agent = agent

        # Return agent only if confidence is above threshold
        if best_score >= 0.5:
            return (best_agent, best_score)

        return None

    def get_anthropic_tools(self) -> List[Dict]:
        """Get all agents as Anthropic tools.

        Returns:
            List of tool definitions
        """
        return [agent.to_anthropic_tool() for agent in self._agents.values()]

    def __len__(self) -> int:
        """Get number of registered agents."""
        return len(self._agents)

    def __contains__(self, agent_name: str) -> bool:
        """Check if agent is registered."""
        return agent_name in self._agents
