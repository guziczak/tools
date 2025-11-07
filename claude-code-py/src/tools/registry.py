"""Tool registry for managing available tools."""

from typing import Dict, List, Optional, Any
from .base import BaseTool, ToolResult, ToolStatus


class ToolRegistry:
    """Registry for managing and executing tools."""

    def __init__(self):
        """Initialize tool registry."""
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool.

        Args:
            tool: Tool instance to register
        """
        self._tools[tool.name] = tool

    def unregister(self, tool_name: str) -> bool:
        """Unregister a tool.

        Args:
            tool_name: Name of tool to unregister

        Returns:
            True if tool was unregistered, False if not found
        """
        if tool_name in self._tools:
            del self._tools[tool_name]
            return True
        return False

    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """Get a tool by name.

        Args:
            tool_name: Name of tool to get

        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(tool_name)

    def list_tools(self) -> List[str]:
        """List all registered tool names.

        Returns:
            List of tool names
        """
        return list(self._tools.keys())

    def get_anthropic_tools(self) -> List[Dict[str, Any]]:
        """Get all tools in Anthropic API format.

        Returns:
            List of tool definitions for Anthropic API
        """
        return [tool.to_anthropic_tool() for tool in self._tools.values()]

    def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """Execute a tool by name.

        Args:
            tool_name: Name of tool to execute
            **kwargs: Tool parameters

        Returns:
            ToolResult with execution result
        """
        tool = self.get_tool(tool_name)

        if not tool:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error=f"Tool not found: {tool_name}"
            )

        # Validate parameters
        is_valid, error = tool.validate_parameters(**kwargs)
        if not is_valid:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error=f"Invalid parameters: {error}"
            )

        # Execute tool
        try:
            return tool.execute(**kwargs)
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error=f"Tool execution failed: {str(e)}"
            )

    def __len__(self) -> int:
        """Get number of registered tools."""
        return len(self._tools)

    def __contains__(self, tool_name: str) -> bool:
        """Check if tool is registered."""
        return tool_name in self._tools
