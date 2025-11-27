"""Command Registry System.

Manages command registration, argument parsing, and execution.
Based on the TypeScript implementation from claude-code-source-code-deobfuscation-main.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Awaitable
import logging

logger = logging.getLogger(__name__)


class ArgType(Enum):
    """Command argument types."""

    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"


@dataclass
class CommandArg:
    """Command argument definition."""

    name: str
    description: str
    type: ArgType
    required: bool = False
    default: Any = None
    choices: Optional[List[str]] = None
    position: Optional[int] = None
    short_flag: Optional[str] = None
    hidden: bool = False


@dataclass
class CommandDef:
    """Command definition."""

    name: str
    description: str
    handler: Callable[[Dict[str, Any]], Awaitable[Any]]
    args: List[CommandArg] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)
    category: Optional[str] = None
    requires_auth: bool = False
    interactive: bool = True
    hidden: bool = False


class CommandRegistry:
    """Registry for managing commands."""

    def __init__(self):
        """Initialize the command registry."""
        self._commands: Dict[str, CommandDef] = {}
        self._aliases: Dict[str, str] = {}

    def register(self, command: CommandDef) -> None:
        """Register a command.

        Args:
            command: Command definition to register

        Raises:
            ValueError: If command name is invalid or already registered
        """
        # Validate command
        if not command.name or not isinstance(command.name, str):
            raise ValueError("Command name is required and must be a string")

        if not command.description:
            raise ValueError(f"Command {command.name} requires a description")

        if not callable(command.handler):
            raise ValueError(f"Command {command.name} requires a callable handler")

        # Check for duplicates
        if command.name in self._commands or command.name in self._aliases:
            raise ValueError(f"Command or alias '{command.name}' is already registered")

        # Register command
        self._commands[command.name] = command
        logger.debug(f"Registered command: {command.name}")

        # Register aliases
        for alias in command.aliases:
            if alias in self._commands or alias in self._aliases:
                logger.warning(f"Skipping duplicate alias '{alias}' for command '{command.name}'")
                continue

            self._aliases[alias] = command.name
            logger.debug(f"Registered alias '{alias}' for command '{command.name}'")

    def get(self, name_or_alias: str) -> Optional[CommandDef]:
        """Get a command by name or alias.

        Args:
            name_or_alias: Command name or alias

        Returns:
            Command definition or None if not found
        """
        # Check direct command name
        if name_or_alias in self._commands:
            return self._commands[name_or_alias]

        # Check alias
        command_name = self._aliases.get(name_or_alias)
        if command_name:
            return self._commands.get(command_name)

        return None

    def exists(self, name_or_alias: str) -> bool:
        """Check if a command exists.

        Args:
            name_or_alias: Command name or alias

        Returns:
            True if command exists, False otherwise
        """
        return name_or_alias in self._commands or name_or_alias in self._aliases

    def list(self, include_hidden: bool = False) -> List[CommandDef]:
        """List all registered commands.

        Args:
            include_hidden: Whether to include hidden commands

        Returns:
            List of command definitions
        """
        commands = list(self._commands.values())

        if not include_hidden:
            commands = [cmd for cmd in commands if not cmd.hidden]

        return commands

    def get_categories(self) -> List[str]:
        """Get all command categories.

        Returns:
            Sorted list of unique categories
        """
        categories = {cmd.category for cmd in self._commands.values() if cmd.category}
        return sorted(categories)

    def get_by_category(self, category: str, include_hidden: bool = False) -> List[CommandDef]:
        """Get commands by category.

        Args:
            category: Category name
            include_hidden: Whether to include hidden commands

        Returns:
            List of commands in the category
        """
        commands = [
            cmd for cmd in self._commands.values()
            if cmd.category == category and (include_hidden or not cmd.hidden)
        ]
        return commands


def parse_args(args: List[str], command: CommandDef) -> Dict[str, Any]:
    """Parse command-line arguments.

    Args:
        args: List of argument strings
        command: Command definition

    Returns:
        Parsed arguments as a dictionary

    Raises:
        ValueError: If arguments are invalid
    """
    result: Dict[str, Any] = {}
    positional_args: List[str] = []
    flag_args: Dict[str, CommandArg] = {}
    errors: List[str] = []

    # Initialize defaults and build flag map
    for arg in command.args:
        if arg.default is not None:
            result[arg.name] = arg.default

        if arg.position is None:
            # Flag argument
            flag_args[f"--{arg.name}"] = arg
            if arg.short_flag:
                flag_args[f"-{arg.short_flag}"] = arg

    # Parse arguments
    i = 0
    while i < len(args):
        arg = args[i]

        if arg.startswith("--") or (arg.startswith("-") and len(arg) == 2):
            # Flag argument
            arg_def = flag_args.get(arg)

            if not arg_def:
                errors.append(f"Unknown argument: {arg}")
                i += 1
                continue

            if arg_def.type == ArgType.BOOLEAN:
                # Boolean flags don't need a value
                result[arg_def.name] = True
                i += 1
            else:
                # Other flags need a value
                if i + 1 >= len(args) or args[i + 1].startswith("-"):
                    errors.append(f"Missing value for argument: {arg}")
                    i += 1
                    continue

                value = args[i + 1]
                result[arg_def.name] = _convert_arg_value(value, arg_def)

                # Validate choices
                if arg_def.choices and str(result[arg_def.name]) not in arg_def.choices:
                    errors.append(
                        f"Invalid value for {arg_def.name}: {value}. "
                        f"Valid values are: {', '.join(arg_def.choices)}"
                    )

                i += 2
        else:
            # Positional argument
            positional_args.append(arg)
            i += 1

    # Process positional arguments
    positional_defs = [arg for arg in command.args if arg.position is not None]
    positional_defs.sort(key=lambda x: x.position or 0)

    for i, arg_def in enumerate(positional_defs):
        if i < len(positional_args):
            # Value provided
            result[arg_def.name] = _convert_arg_value(positional_args[i], arg_def)

            # Validate choices
            if arg_def.choices and str(result[arg_def.name]) not in arg_def.choices:
                errors.append(
                    f"Invalid value for {arg_def.name}: {positional_args[i]}. "
                    f"Valid values are: {', '.join(arg_def.choices)}"
                )
        elif arg_def.required:
            # Required value not provided
            errors.append(f"Missing required argument: {arg_def.name}")

    # Check for missing required flag args
    for arg in command.args:
        if arg.required and arg.name not in result:
            errors.append(f"Missing required argument: {arg.name}")

    # Raise if there are errors
    if errors:
        raise ValueError(f"Invalid arguments: {'; '.join(errors)}")

    return result


def _convert_arg_value(value: str, arg_def: CommandArg) -> Any:
    """Convert an argument value based on its type.

    Args:
        value: String value to convert
        arg_def: Argument definition

    Returns:
        Converted value

    Raises:
        ValueError: If conversion fails
    """
    if arg_def.type == ArgType.NUMBER:
        try:
            # Try integer first
            if "." not in value:
                return int(value)
            # Fall back to float
            return float(value)
        except ValueError:
            raise ValueError(f"Invalid number: {value}")

    elif arg_def.type == ArgType.BOOLEAN:
        return value.lower() in ("true", "1", "yes", "y")

    elif arg_def.type == ArgType.ARRAY:
        return [v.strip() for v in value.split(",")]

    else:  # STRING
        return value


def generate_command_help(command: CommandDef) -> str:
    """Generate help text for a command.

    Args:
        command: Command definition

    Returns:
        Formatted help text
    """
    lines = []

    # Header
    lines.append(f"\n{command.name} - {command.description}\n")

    # Usage
    lines.append("Usage:")
    usage = f"  /{command.name}"

    # Add positional args
    positional_args = [arg for arg in command.args if arg.position is not None]
    positional_args.sort(key=lambda x: x.position or 0)

    for arg in positional_args:
        arg_display = f"<{arg.name}>" if arg.required else f"[{arg.name}]"
        usage += f" {arg_display}"

    # Add flag options
    flag_args = [arg for arg in command.args if arg.position is None]
    if flag_args:
        usage += " [options]"

    lines.append(usage)
    lines.append("")

    # Arguments
    if positional_args:
        lines.append("Arguments:")
        for arg in positional_args:
            line = f"  {arg.name:<20} {arg.description}"
            if arg.default is not None:
                line += f" (default: {arg.default})"
            if arg.choices:
                line += f" (choices: {', '.join(arg.choices)})"
            lines.append(line)
        lines.append("")

    # Options
    if flag_args:
        lines.append("Options:")
        for arg in flag_args:
            flag = f"--{arg.name}"
            if arg.short_flag:
                flag = f"-{arg.short_flag}, {flag}"

            line = f"  {flag:<20} {arg.description}"
            if arg.default is not None:
                line += f" (default: {arg.default})"
            if arg.choices:
                line += f" (choices: {', '.join(arg.choices)})"
            lines.append(line)
        lines.append("")

    # Examples
    if command.examples:
        lines.append("Examples:")
        for example in command.examples:
            lines.append(f"  $ /{example}")
        lines.append("")

    # Aliases
    if command.aliases:
        lines.append(f"Aliases: {', '.join(command.aliases)}\n")

    return "\n".join(lines)


# Create singleton registry
command_registry = CommandRegistry()
