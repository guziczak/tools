#!/usr/bin/env python3
"""Claude Code Python - Main entry point."""

import os
import sys
from pathlib import Path
from typing import Optional

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from core.api_client import ClaudeAPIClient
from core.auth import AuthManager, AuthenticationError
from ui.terminal import TerminalUI
from tools import create_default_registry, ToolRegistry
from agents import AgentRegistry, AgentRouter
from agents.prebuilt import create_default_agents
from agents.thinking import detect_thinking_level
from utils import check_and_setup, automatic_claude_max_setup


class ClaudeCodePy:
    """Main application class."""

    def __init__(self):
        """Initialize the application."""
        # Ensure .env exists with sensible defaults
        self._ensure_env_file()

        # Load environment variables
        load_dotenv()

        # Initialize UI
        self.ui = TerminalUI()

        # Initialize auth manager
        self.auth_manager = AuthManager()

        # Initialize tool registry
        self.tool_registry: Optional[ToolRegistry] = None

        # Initialize agent registry
        self.agent_registry: Optional[AgentRegistry] = None
        self.agent_router: Optional[AgentRouter] = None

        # Load configuration from environment
        self.config = {
            "api_key": os.getenv("ANTHROPIC_API_KEY"),
            "model": os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514"),
            "max_tokens": int(os.getenv("CLAUDE_MAX_TOKENS", "8000")),
            "temperature": float(os.getenv("CLAUDE_TEMPERATURE", "1.0")),
            "thinking_enabled": os.getenv("CLAUDE_THINKING_ENABLED", "true").lower() == "true",
            "thinking_budget": int(os.getenv("CLAUDE_THINKING_BUDGET", "10000")),
            "use_oauth": os.getenv("CLAUDE_USE_OAUTH", "false").lower() == "true",  # Default: false (OAuth doesn't work for third-party)
            "tools_enabled": os.getenv("CLAUDE_TOOLS_ENABLED", "true").lower() == "true",
            "agents_enabled": os.getenv("CLAUDE_AGENTS_ENABLED", "true").lower() == "true",
        }

        # System prompt
        self.system_prompt = """You are Claude, a helpful AI assistant. You are running in Claude Code Python, a terminal-based chat interface.

You have access to:
1. **Tools** for file operations, running commands, and searching files
2. **Specialized Agents** for complex tasks:
   - Test Writer: For writing comprehensive tests
   - Code Reviewer: For reviewing code quality and security
   - Bug Fixer: For debugging and fixing issues
   - Refactorer: For improving code structure

When the user needs specialized help (tests, reviews, debugging, refactoring), delegate to the appropriate agent using the delegate_to_* tools. For simple file operations or commands, use regular tools directly.

Be concise, helpful, and friendly. When writing code, use proper syntax highlighting."""

        # Initialize API client (will be done in run())
        self.client: Optional[ClaudeAPIClient] = None

    def _ensure_env_file(self) -> None:
        """Ensure .env file exists with OAuth enabled by default."""
        env_path = Path(".env")
        env_example = Path(".env.example")

        if not env_path.exists():
            # Create .env from .env.example if it exists
            if env_example.exists():
                import shutil
                shutil.copy(env_example, env_path)
            else:
                # Create minimal .env with OAuth enabled
                with open(env_path, 'w') as f:
                    f.write("# Claude Code Python Configuration\n")
                    f.write("# Auto-generated - feel free to edit!\n\n")
                    f.write("# OAuth Configuration (like official Claude Code)\n")
                    f.write("CLAUDE_USE_OAUTH=true\n\n")
                    f.write("# API Key (leave empty to use OAuth)\n")
                    f.write("ANTHROPIC_API_KEY=\n\n")
                    f.write("# Model Configuration\n")
                    f.write("CLAUDE_MODEL=claude-sonnet-4-20250514\n")
                    f.write("CLAUDE_MAX_TOKENS=8000\n")
                    f.write("CLAUDE_TEMPERATURE=1.0\n\n")
                    f.write("# Extended Thinking\n")
                    f.write("CLAUDE_THINKING_ENABLED=true\n")
                    f.write("CLAUDE_THINKING_BUDGET=10000\n\n")
                    f.write("# Tools & Agents\n")
                    f.write("CLAUDE_TOOLS_ENABLED=true\n")
                    f.write("CLAUDE_AGENTS_ENABLED=true\n")

    def _clear_oauth_token_from_env(self) -> None:
        """Clear OAuth token from .env file."""
        env_path = Path(".env")

        if not env_path.exists():
            return

        try:
            # Read existing .env
            with open(env_path, 'r') as f:
                lines = f.readlines()

            # Clear OAuth token and API key lines
            new_lines = []
            for line in lines:
                if line.startswith('CLAUDE_CODE_OAUTH_TOKEN='):
                    new_lines.append('CLAUDE_CODE_OAUTH_TOKEN=\n')
                elif line.startswith('ANTHROPIC_API_KEY='):
                    new_lines.append('ANTHROPIC_API_KEY=\n')
                else:
                    new_lines.append(line)

            # Write back
            with open(env_path, 'w') as f:
                f.writelines(new_lines)

            # Reload environment
            load_dotenv(override=True)

        except Exception as e:
            self.ui.print_error(f"Failed to clear token from .env: {e}")

    def ensure_authentication(self) -> Optional[str]:
        """Ensure user is authenticated and return API key/token.

        Returns:
            API key/token or None if authentication failed
        """
        # Check for API keys OR OAuth tokens (both now work!)

        # Priority 1: Check for manual API key in environment
        if self.config["api_key"]:
            if self.config["api_key"].startswith("sk-ant-oat"):
                self.ui.print_info("✅ OAuth token detected!")
                self.ui.print_info("   Using OAuth Bearer authentication with /v1/messages")
            else:
                self.ui.print_info("Using API key from environment")
            return self.config["api_key"]

        # Priority 2: Check for CLAUDE_CODE_OAUTH_TOKEN
        oauth_token = os.getenv("CLAUDE_CODE_OAUTH_TOKEN")
        if oauth_token and oauth_token.strip():
            self.ui.print_info("✅ OAuth token detected!")
            self.ui.print_info("   Using OAuth Bearer authentication with /v1/messages")
            return oauth_token

        # Priority 3: Check ~/.claude/.credentials.json (new format)
        try:
            creds_path = Path.home() / ".claude" / ".credentials.json"
            if creds_path.exists():
                import json
                with open(creds_path) as f:
                    creds = json.load(f)
                    oauth_data = creds.get("claudeAiOauth", {})
                    access_token = oauth_data.get("accessToken")
                    if access_token:
                        self.ui.print_info("✅ Using OAuth token from ~/.claude/.credentials.json")
                        self.ui.print_info("   (Authenticated with official Claude Code)")
                        return access_token
        except Exception as e:
            # Debug: show error but continue
            import traceback
            self.ui.print_error(f"Error reading credentials: {e}")
            traceback.print_exc()
            pass  # Ignore errors reading credentials

        # Priority 4: Show setup options (both work!)
        self.ui.print_info("No authentication found!")
        self.ui.print_info("")
        self.ui.print_info("="*70)
        self.ui.print_info("  🔐 Authentication Setup")
        self.ui.print_info("="*70)
        self.ui.print_info("")
        self.ui.print_info("  💎 OPTION 1: Claude Max/Pro (If you have it)")
        self.ui.print_info("")
        self.ui.print_info("     ✅ OAuth tokens NOW WORK!")
        self.ui.print_info("     Uses Bearer auth with /v1/messages endpoint")
        self.ui.print_info("")
        self.ui.print_info("     Run: claude setup-token")
        self.ui.print_info("     (Token saved to ~/.claude/.credentials.json)")
        self.ui.print_info("     Then run this app again - auto-detected!")
        self.ui.print_info("")
        self.ui.print_info("  ---")
        self.ui.print_info("")
        self.ui.print_info("  💳 OPTION 2: API Key (Recommended for most users)")
        self.ui.print_info("")
        self.ui.print_info("     Simple pay-as-you-go, FREE $5 credit!")
        self.ui.print_info("     Full features: tools, agents, thinking")
        self.ui.print_info("")
        self.ui.print_info("="*70)
        self.ui.print_info("")

        # Ask user to continue with API key setup
        try:
            input("  Press Enter to setup API key (or Ctrl+C to cancel): ")
        except (KeyboardInterrupt, EOFError):
            self.ui.print_info("\nSetup cancelled.")
            return None

        # Continue with API key setup
        self.ui.print_info("")
        self.ui.print_info("Starting API key setup...")
        api_key = check_and_setup()

        if api_key:
            # Update config with new key
            self.config["api_key"] = api_key
            self.config["use_oauth"] = False
            return api_key

        # Setup failed or cancelled
        self.ui.print_error("Setup failed or cancelled")
        return None

    def initialize_tools(self) -> None:
        """Initialize tool registry."""
        if self.config["tools_enabled"]:
            self.tool_registry = create_default_registry()
            self.ui.print_info(f"Tools enabled ({len(self.tool_registry)} tools)")
        else:
            self.tool_registry = None

    def initialize_agents(self) -> None:
        """Initialize agent registry."""
        if self.config["agents_enabled"]:
            self.agent_registry = AgentRegistry()

            # Register pre-built agents
            for agent in create_default_agents():
                self.agent_registry.register(agent)

            self.ui.print_info(f"Agents enabled ({len(self.agent_registry)} specialized agents)")

            # Show available agents
            agent_names = ", ".join(self.agent_registry.list_agents())
            self.ui.print_info(f"Available agents: {agent_names}")
        else:
            self.agent_registry = None

    def initialize_client(self) -> bool:
        """Initialize the API client.

        Returns:
            True if successful, False otherwise
        """
        # Get API key (via OAuth or manual)
        api_key = self.ensure_authentication()
        if not api_key:
            return False

        # Initialize tools and agents (OAuth now supports them!)
        self.initialize_tools()
        self.initialize_agents()

        # Get tool definitions for API
        tools = None
        if self.tool_registry:
            tools = self.tool_registry.get_anthropic_tools()

        # Add agents as tools (so Claude can choose them)
        if self.agent_registry:
            agent_tools = self.agent_registry.get_anthropic_tools()
            if tools:
                tools.extend(agent_tools)
            else:
                tools = agent_tools

            # Create agent router
            from anthropic import Anthropic
            self.agent_router = AgentRouter(
                self.agent_registry,
                Anthropic(api_key=api_key)
            )

        try:
            self.client = ClaudeAPIClient(
                api_key=api_key,
                model=self.config["model"],
                max_tokens=self.config["max_tokens"],
                temperature=self.config["temperature"],
                thinking_enabled=self.config["thinking_enabled"],
                thinking_budget=self.config["thinking_budget"],
                tools=tools,
                tool_registry=self.tool_registry,
            )
            return True
        except Exception as e:
            self.ui.print_error(f"Failed to initialize client: {e}")
            return False

    def run(self):
        """Run the main chat loop."""
        # Print banner
        self.ui.print_banner()

        # Initialize client
        if not self.initialize_client():
            return

        # Show configuration
        self.ui.print_info(f"Model: {self.config['model']}")
        if self.config["thinking_enabled"]:
            self.ui.print_info(
                f"Extended Thinking: Enabled (budget: {self.config['thinking_budget']} tokens)"
            )

        self.ui.print_separator()

        # Main chat loop
        while True:
            try:
                # Get user input
                user_input = self.ui.get_user_input()

                # Check for exit commands
                if not user_input:
                    continue

                if user_input.lower() in ["exit", "quit", "q"]:
                    self.ui.print_goodbye()
                    break

                # Handle special commands
                if user_input.startswith("/"):
                    self.handle_command(user_input)
                    continue

                # Send to Claude and stream response
                self.ui.print_separator()
                try:
                    # Detect thinking level
                    thinking_level, explicit = detect_thinking_level(user_input)
                    if explicit:
                        self.ui.print_info(f"Thinking level: {thinking_level.name} ({thinking_level.budget:,} tokens)")

                    # Use chat_with_tools if tools/agents are enabled
                    if self.tool_registry or self.agent_registry:
                        events = self.client.chat_with_tools(user_input, system=self.system_prompt)
                    else:
                        events = self.client.chat(user_input, system=self.system_prompt)

                    self.ui.stream_response_with_tools(events, self.tool_registry)
                except Exception as e:
                    self.ui.print_error(f"API error: {e}")

                self.ui.print_separator()

            except KeyboardInterrupt:
                self.ui.print_goodbye()
                break
            except Exception as e:
                self.ui.print_error(f"Unexpected error: {e}")

    def handle_command(self, command: str):
        """Handle special commands.

        Args:
            command: Command string starting with /
        """
        cmd = command.lower().strip()

        if cmd == "/clear":
            self.ui.clear_screen()
            self.ui.print_banner()
            self.ui.print_success("Screen cleared")

        elif cmd == "/reset":
            if self.client:
                self.client.clear_history()
            self.ui.print_success("Conversation history cleared")

        elif cmd == "/help":
            self.show_help()

        elif cmd == "/agents":
            self.show_agents()

        elif cmd == "/login":
            self.handle_login()

        elif cmd == "/logout":
            self.handle_logout()

        else:
            self.ui.print_error(f"Unknown command: {command}")
            self.ui.print_info("Type /help for available commands")

    def handle_login(self):
        """Handle login command."""
        try:
            self.ui.print_info("Starting authentication flow...")
            api_key = self.auth_manager.get_access_token(force_reauth=True)
            self.ui.print_success("Authentication successful!")

            # Reinitialize client with new token
            if self.initialize_client():
                self.ui.print_success("Client reinitialized")
        except AuthenticationError as e:
            self.ui.print_error(f"Authentication failed: {e}")
        except Exception as e:
            self.ui.print_error(f"Error during login: {e}")

    def handle_logout(self):
        """Handle logout command."""
        self.auth_manager.logout()
        self.ui.print_success("Logged out successfully")
        self.ui.print_info("Your saved authentication has been cleared")

    def show_agents(self):
        """Show available agents."""
        if not self.agent_registry:
            self.ui.print_info("Agents are not enabled")
            return

        self.ui.console.print("\n[bold cyan]Available Specialized Agents:[/bold cyan]\n")

        for agent in self.agent_registry._agents.values():
            self.ui.console.print(f"  [bold yellow]{agent.name}[/bold yellow] ({agent.role.value})")
            self.ui.console.print(f"    {agent.description}")
            self.ui.console.print(f"    Keywords: {', '.join(agent.keywords[:5])}")
            self.ui.console.print()

        self.ui.console.print("[dim]Claude will automatically choose the right agent for your task![/dim]\n")

    def show_help(self):
        """Show help message."""
        help_text = """
[bold cyan]Available Commands:[/bold cyan]

  /help     - Show this help message
  /agents   - Show available specialized agents
  /clear    - Clear the screen
  /reset    - Reset conversation history
  /login    - Re-authenticate (OAuth device flow)
  /logout   - Clear saved authentication
  exit/quit - Exit the application

[bold cyan]Thinking Levels:[/bold cyan]

  think         - Basic thinking (4K tokens)
  think hard    - Standard thinking (10K tokens)
  think harder  - Deep thinking (20K tokens)
  ultrathink    - Maximum thinking (32K tokens)

[bold cyan]Tips:[/bold cyan]

  • Extended thinking is enabled - Claude will show reasoning process
  • Specialized agents available for tests, reviews, debugging, refactoring
  • All messages are kept in conversation history
  • Use Ctrl+C to interrupt at any time
  • First run will open browser for authentication
        """
        self.ui.console.print(help_text)


def main():
    """Main entry point."""
    app = ClaudeCodePy()
    app.run()


if __name__ == "__main__":
    main()
