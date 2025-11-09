"""Base agent class and configuration."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from enum import Enum


class AgentRole(Enum):
    """Agent specialization roles."""

    TEST_WRITER = "test_writer"
    CODE_REVIEWER = "code_reviewer"
    BUG_FIXER = "bug_fixer"
    REFACTORER = "refactorer"
    DOCUMENTER = "documenter"
    SECURITY_AUDITOR = "security_auditor"
    PERFORMANCE_OPTIMIZER = "performance_optimizer"
    GENERAL = "general"


@dataclass
class AgentConfig:
    """Configuration for an agent."""

    name: str
    role: AgentRole
    description: str
    system_prompt: str
    thinking_budget: int = 10000
    temperature: float = 1.0
    max_tokens: int = 8000
    keywords: List[str] = None  # Keywords that trigger this agent

    def __post_init__(self):
        """Initialize keywords if not provided."""
        if self.keywords is None:
            self.keywords = []


@dataclass
class AgentResult:
    """Result from agent execution."""

    agent_name: str
    agent_role: str
    success: bool
    output: str
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_name": self.agent_name,
            "agent_role": self.agent_role,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "metadata": self.metadata or {},
        }


class BaseAgent(ABC):
    """Base class for all agents."""

    def __init__(self, config: AgentConfig):
        """Initialize agent with configuration.

        Args:
            config: Agent configuration
        """
        self.config = config
        self.name = config.name
        self.role = config.role
        self.description = config.description
        self.system_prompt = config.system_prompt
        self.thinking_budget = config.thinking_budget
        self.keywords = config.keywords

    @abstractmethod
    def can_handle(self, task_description: str) -> float:
        """Determine if this agent can handle the task.

        Args:
            task_description: Description of the task

        Returns:
            Confidence score (0.0 to 1.0)
        """
        pass

    def to_anthropic_tool(self) -> Dict[str, Any]:
        """Convert agent to Anthropic tool format.

        This allows Claude to "choose" an agent like it chooses a tool.

        Returns:
            Tool definition for Anthropic API
        """
        return {
            "name": f"delegate_to_{self.role.value}",
            "description": f"{self.description}\n\nUse this when: {', '.join(self.keywords)}",
            "input_schema": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "The specific task to delegate to this agent",
                    },
                    "context": {
                        "type": "string",
                        "description": "Additional context for the task (optional)",
                    },
                },
                "required": ["task"],
            },
        }

    def get_enhanced_system_prompt(self, task: str, context: Optional[str] = None) -> str:
        """Get system prompt with task context.

        Args:
            task: Task to perform
            context: Optional additional context

        Returns:
            Enhanced system prompt
        """
        prompt = self.system_prompt

        if task:
            prompt += f"\n\nCurrent Task: {task}"

        if context:
            prompt += f"\n\nAdditional Context: {context}"

        return prompt

    def __repr__(self) -> str:
        """String representation."""
        return f"<{self.__class__.__name__}(name='{self.name}', role='{self.role.value}')>"
