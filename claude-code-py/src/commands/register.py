"""Command Registration.

Registers all available commands with the command registry.
Based on the TypeScript implementation.
"""

import logging
from pathlib import Path
from typing import Dict, Any

from .registry import command_registry, CommandDef, CommandArg, ArgType

logger = logging.getLogger(__name__)


def register_all_commands(
    ui,
    api_client,
    tool_registry=None,
    agent_registry=None,
    auth_manager=None,
) -> None:
    """Register all commands.

    Args:
        ui: Terminal UI instance
        api_client: Claude API client
        tool_registry: Optional tool registry
        agent_registry: Optional agent registry
        auth_manager: Optional auth manager
    """
    logger.debug("Registering commands")

    # Create context dict for handlers
    ctx = {
        "ui": ui,
        "api_client": api_client,
        "tool_registry": tool_registry,
        "agent_registry": agent_registry,
        "auth_manager": auth_manager,
    }

    # Register core commands
    _register_help_command(ctx)
    _register_clear_command(ctx)
    _register_reset_command(ctx)
    _register_thinking_command(ctx)
    _register_agents_command(ctx)
    _register_login_command(ctx)
    _register_logout_command(ctx)
    _register_exit_command(ctx)

    logger.info("Commands registered successfully")


def _register_help_command(ctx: Dict[str, Any]) -> None:
    """Register help command."""
    async def handler(args: Dict[str, Any]) -> None:
        ui = ctx["ui"]

        help_text = """
[bold cyan]Available Commands:[/bold cyan]

  /help      - Show this help message
  /thinking  - Toggle thinking process visibility
  /agents    - Show available specialized agents
  /clear     - Clear the screen
  /reset     - Reset conversation history
  /login     - Re-authenticate (OAuth device flow)
  /logout    - Clear saved authentication
  exit/quit  - Exit the application

[bold cyan]Thinking Levels:[/bold cyan]

  think         - Basic thinking (4K tokens)
  think hard    - Standard thinking (10K tokens)
  think harder  - Deep thinking (20K tokens)
  ultrathink    - Maximum thinking (32K tokens)

[bold cyan]Tips:[/bold cyan]

  • Extended thinking is enabled with real-time token counter
  • Use /thinking to show/hide thinking process after each response
  • Specialized agents available for tests, reviews, debugging, refactoring
  • All messages are kept in conversation history
  • Use Ctrl+C to interrupt at any time
        """
        ui.console.print(help_text)

    command = CommandDef(
        name="help",
        description="Show help information",
        handler=handler,
        category="System",
        examples=["help"],
    )

    command_registry.register(command)


def _register_clear_command(ctx: Dict[str, Any]) -> None:
    """Register clear command."""
    async def handler(args: Dict[str, Any]) -> None:
        ui = ctx["ui"]
        ui.clear_screen()
        ui.print_banner()
        ui.print_success("Screen cleared")

    command = CommandDef(
        name="clear",
        description="Clear the screen",
        handler=handler,
        category="System",
        examples=["clear"],
    )

    command_registry.register(command)


def _register_reset_command(ctx: Dict[str, Any]) -> None:
    """Register reset command."""
    async def handler(args: Dict[str, Any]) -> None:
        ui = ctx["ui"]
        api_client = ctx["api_client"]

        if api_client:
            api_client.clear_history()
        ui.print_success("Conversation history cleared")

    command = CommandDef(
        name="reset",
        description="Reset conversation history",
        handler=handler,
        category="System",
        examples=["reset"],
    )

    command_registry.register(command)


def _register_thinking_command(ctx: Dict[str, Any]) -> None:
    """Register thinking toggle command."""
    async def handler(args: Dict[str, Any]) -> None:
        ui = ctx["ui"]
        ui.toggle_thinking_visibility()

    command = CommandDef(
        name="thinking",
        description="Toggle thinking process visibility",
        handler=handler,
        category="System",
        examples=["thinking"],
    )

    command_registry.register(command)


def _register_agents_command(ctx: Dict[str, Any]) -> None:
    """Register agents command."""
    async def handler(args: Dict[str, Any]) -> None:
        ui = ctx["ui"]
        agent_registry = ctx.get("agent_registry")

        if not agent_registry:
            ui.print_info("Agents are not enabled")
            return

        ui.console.print("\n[bold cyan]Available Specialized Agents:[/bold cyan]\n")

        for agent in agent_registry._agents.values():
            ui.console.print(f"  [bold yellow]{agent.name}[/bold yellow] ({agent.role.value})")
            ui.console.print(f"    {agent.description}")
            ui.console.print(f"    Keywords: {', '.join(agent.keywords[:5])}")
            ui.console.print()

        ui.console.print(
            "[dim]Claude will automatically choose the right agent for your task![/dim]\n"
        )

    command = CommandDef(
        name="agents",
        description="Show available specialized agents",
        handler=handler,
        category="System",
        examples=["agents"],
    )

    command_registry.register(command)


def _register_login_command(ctx: Dict[str, Any]) -> None:
    """Register login command."""
    async def handler(args: Dict[str, Any]) -> None:
        ui = ctx["ui"]
        auth_manager = ctx.get("auth_manager")

        if not auth_manager:
            ui.print_error("Authentication manager not available")
            return

        try:
            ui.print_info("Starting authentication flow...")
            api_key = auth_manager.get_access_token(force_reauth=True)
            ui.print_success("Authentication successful!")
        except Exception as e:
            ui.print_error(f"Authentication failed: {e}")

    command = CommandDef(
        name="login",
        description="Re-authenticate (OAuth device flow)",
        handler=handler,
        category="Auth",
        examples=["login"],
    )

    command_registry.register(command)


def _register_logout_command(ctx: Dict[str, Any]) -> None:
    """Register logout command."""
    async def handler(args: Dict[str, Any]) -> None:
        ui = ctx["ui"]
        auth_manager = ctx.get("auth_manager")

        if not auth_manager:
            ui.print_error("Authentication manager not available")
            return

        auth_manager.logout()
        ui.print_success("Logged out successfully")
        ui.print_info("Your saved authentication has been cleared")

    command = CommandDef(
        name="logout",
        description="Clear saved authentication",
        handler=handler,
        category="Auth",
        examples=["logout"],
    )

    command_registry.register(command)


def _register_exit_command(ctx: Dict[str, Any]) -> None:
    """Register exit command."""
    async def handler(args: Dict[str, Any]) -> None:
        ui = ctx["ui"]
        ui.print_goodbye()
        import sys
        sys.exit(0)

    command = CommandDef(
        name="exit",
        description="Exit the application",
        handler=handler,
        aliases=["quit", "q"],
        category="System",
        examples=["exit", "quit"],
    )

    command_registry.register(command)
