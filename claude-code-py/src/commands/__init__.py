"""Command system for Claude Code Python.

Provides a framework for registering, managing, and executing commands
similar to the original TypeScript implementation.
"""

from .registry import CommandRegistry, ArgType, CommandDef, CommandArg
from .registry import command_registry

__all__ = [
    "CommandRegistry",
    "ArgType",
    "CommandDef",
    "CommandArg",
    "command_registry",
]
