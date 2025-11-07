"""Tool system for Claude Code Python."""

from .base import BaseTool, ToolResult, ToolStatus
from .registry import ToolRegistry
from .file_ops import ReadTool, WriteTool, EditTool
from .bash import BashTool, BashInteractiveTool
from .search import GrepTool, GlobTool


def create_default_registry() -> ToolRegistry:
    """Create a tool registry with all default tools.

    Returns:
        ToolRegistry with all default tools registered
    """
    registry = ToolRegistry()

    # Register file operation tools
    registry.register(ReadTool())
    registry.register(WriteTool())
    registry.register(EditTool())

    # Register bash tool
    registry.register(BashTool())

    # Register search tools
    registry.register(GrepTool())
    registry.register(GlobTool())

    return registry


__all__ = [
    "BaseTool",
    "ToolResult",
    "ToolStatus",
    "ToolRegistry",
    "ReadTool",
    "WriteTool",
    "EditTool",
    "BashTool",
    "BashInteractiveTool",
    "GrepTool",
    "GlobTool",
    "create_default_registry",
]
