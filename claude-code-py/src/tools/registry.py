"""Tool registry for managing available tools."""

from typing import Dict, List, Optional, Any
from core.logging import get_logger

logger = get_logger(__name__)
from .base import BaseTool, ToolResult, ToolStatus


class ToolRegistry:
    """Registry for managing and executing tools."""

    def __init__(self):
        """Initialize tool registry."""
        self._tools: Dict[str, BaseTool] = {}
        self._aliases: Dict[str, str] = {}  # alias -> canonical_name mapping

    def register(self, tool: BaseTool) -> None:
        """Register a tool and its aliases.

        Args:
            tool: Tool instance to register
        """
        # Register by canonical name
        self._tools[tool.name] = tool

        # Register all aliases
        for alias in tool.aliases:
            self._aliases[alias] = tool.name
            logger.debug("Registered alias: %s -> %s", alias, tool.name)

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
        """Get a tool by name or alias.

        Args:
            tool_name: Name or alias of tool to get

        Returns:
            Tool instance or None if not found
        """
        # Try direct name lookup first
        if tool_name in self._tools:
            return self._tools[tool_name]

        # Try alias lookup
        if tool_name in self._aliases:
            canonical_name = self._aliases[tool_name]
            return self._tools.get(canonical_name)

        return None

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
                status=ToolStatus.ERROR, output="", error=f"Tool not found: {tool_name}"
            )

        # Map claude.ai parameter names to our local parameter names
        # claude.ai create_file uses: path, file_text, description
        # Our write_file uses: file_path, content
        mapped_params = kwargs.copy()
        if tool_name in ["create_file", "write_file", "Write"]:
            if "path" in mapped_params:
                path = mapped_params.pop("path")
                # Strip claude.ai virtual paths and use just filename in CWD
                if path.startswith("/mnt/user-data/outputs/"):
                    path = path.replace("/mnt/user-data/outputs/", "")
                mapped_params["file_path"] = path
            if "file_text" in mapped_params:
                mapped_params["content"] = mapped_params.pop("file_text")
            # Remove claude.ai-specific params
            mapped_params.pop("description", None)

        # Validate parameters (skip validation for now - claude.ai params differ)
        # is_valid, error = tool.validate_parameters(**mapped_params)
        # if not is_valid:
        #     return ToolResult(
        #         status=ToolStatus.ERROR,
        #         output="",
        #         error=f"Invalid parameters: {error}"
        #     )

        # Execute tool
        try:
            return tool.execute(**mapped_params)
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR, output="", error=f"Tool execution failed: {str(e)}"
            )

    def __len__(self) -> int:
        """Get number of registered tools."""
        return len(self._tools)

    def __contains__(self, tool_name: str) -> bool:
        """Check if tool is registered."""
        return tool_name in self._tools
