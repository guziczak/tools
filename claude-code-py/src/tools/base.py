"""Base tool class and result type."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class ToolStatus(Enum):
    """Tool execution status."""
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"


@dataclass
class ToolResult:
    """Result of tool execution."""
    status: ToolStatus
    output: str
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API."""
        result = {
            "status": self.status.value,
            "output": self.output,
        }
        if self.error:
            result["error"] = self.error
        if self.metadata:
            result["metadata"] = self.metadata
        return result


class BaseTool(ABC):
    """Base class for all tools."""

    def __init__(self):
        """Initialize tool."""
        self.name = self.get_name()
        self.description = self.get_description()
        self.parameters = self.get_parameters()
        self.aliases = self.get_aliases()

    @abstractmethod
    def get_name(self) -> str:
        """Get tool name."""
        pass

    def get_aliases(self) -> List[str]:
        """Get tool name aliases (for compatibility with different APIs).

        Returns:
            List of alternative names for this tool
        """
        return []

    @abstractmethod
    def get_description(self) -> str:
        """Get tool description."""
        pass

    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """Get tool parameters schema (JSON Schema format)."""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool.

        Args:
            **kwargs: Tool parameters

        Returns:
            ToolResult with execution result
        """
        pass

    def to_anthropic_tool(self) -> Dict[str, Any]:
        """Convert to Anthropic tool format.

        Returns:
            Tool definition for Anthropic API
        """
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": self.parameters,
                "required": list(self.parameters.keys())
            }
        }

    def validate_parameters(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate tool parameters.

        Args:
            **kwargs: Parameters to validate

        Returns:
            (is_valid, error_message)
        """
        # Check required parameters
        for param_name, param_schema in self.parameters.items():
            if param_name not in kwargs:
                return False, f"Missing required parameter: {param_name}"

        return True, None
