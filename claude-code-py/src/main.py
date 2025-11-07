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


class ClaudeCodePy:
    """Main application class."""

    def __init__(self):
        """Initialize the application."""
        # Load environment variables
        load_dotenv()

        # Initialize UI
        self.ui = TerminalUI()

        # Initialize auth manager
        self.auth_manager = AuthManager()

        # Initialize tool registry
        self.tool_registry: Optional[ToolRegistry] = None

        # Load configuration from environment
        self.config = {
            "api_key": os.getenv("ANTHROPIC_API_KEY"),
            "model": os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514"),
            "max_tokens": int(os.getenv("CLAUDE_MAX_TOKENS", "8000")),
            "temperature": float(os.getenv("CLAUDE_TEMPERATURE", "1.0")),
            "thinking_enabled": os.getenv("CLAUDE_THINKING_ENABLED", "true").lower() == "true",
            "thinking_budget": int(os.getenv("CLAUDE_THINKING_BUDGET", "10000")),
            "use_oauth": os.getenv("CLAUDE_USE_OAUTH", "true").lower() == "true",
            "tools_enabled": os.getenv("CLAUDE_TOOLS_ENABLED", "true").lower() == "true",
        }

        # System prompt
        self.system_prompt = """You are Claude, a helpful AI assistant. You are running in Claude Code Python, a terminal-based chat interface.

You have access to tools for file operations, running commands, and searching files. Use them when needed to help the user.

Be concise, helpful, and friendly. When writing code, use proper syntax highlighting."""

        # Initialize API client (will be done in run())
        self.client: Optional[ClaudeAPIClient] = None

    def ensure_authentication(self) -> Optional[str]:
        """Ensure user is authenticated and return API key.

        Returns:
            API key or None if authentication failed
        """
        # Check for manual API key first
        if self.config["api_key"]:
            self.ui.print_info("Using API key from environment")
            return self.config["api_key"]

        # Use OAuth if enabled
        if not self.config["use_oauth"]:
            self.ui.print_error("No API key found and OAuth disabled")
            self.ui.print_info("Set ANTHROPIC_API_KEY in .env or enable OAuth")
            return None

        # Check for existing OAuth token
        if self.auth_manager.is_authenticated():
            self.ui.print_info("Using saved authentication")
            return self.auth_manager.get_access_token()

        # Need to authenticate via OAuth
        self.ui.print_info("Authentication required - attempting OAuth...")
        try:
            api_key = self.auth_manager.get_access_token()
            self.ui.print_success("Authentication successful!")
            return api_key
        except AuthenticationError as e:
            error_msg = str(e)
            self.ui.print_error(f"OAuth failed: {error_msg}")

            # Check if it's a "not available" error - offer fallback
            if "not available" in error_msg.lower() or "404" in error_msg:
                self.ui.print_info("\n" + "="*50)
                self.ui.print_info("OAuth device flow is not available.")
                self.ui.print_info("Please use manual API key instead:")
                self.ui.print_info("  1. Create .env file: cp .env.example .env")
                self.ui.print_info("  2. Add your API key: ANTHROPIC_API_KEY=sk-ant-...")
                self.ui.print_info("  3. Disable OAuth: CLAUDE_USE_OAUTH=false")
                self.ui.print_info("="*50 + "\n")

            return None
        except Exception as e:
            self.ui.print_error(f"Unexpected error during authentication: {e}")
            return None

    def initialize_tools(self) -> None:
        """Initialize tool registry."""
        if self.config["tools_enabled"]:
            self.tool_registry = create_default_registry()
            self.ui.print_info(f"Tools enabled ({len(self.tool_registry)} tools)")
        else:
            self.tool_registry = None

    def initialize_client(self) -> bool:
        """Initialize the API client.

        Returns:
            True if successful, False otherwise
        """
        # Get API key (via OAuth or manual)
        api_key = self.ensure_authentication()
        if not api_key:
            return False

        # Initialize tools
        self.initialize_tools()

        # Get tool definitions for API
        tools = None
        if self.tool_registry:
            tools = self.tool_registry.get_anthropic_tools()

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
                    # Use chat_with_tools if tools are enabled
                    if self.tool_registry:
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

    def show_help(self):
        """Show help message."""
        help_text = """
[bold cyan]Available Commands:[/bold cyan]

  /help     - Show this help message
  /clear    - Clear the screen
  /reset    - Reset conversation history
  /login    - Re-authenticate (OAuth device flow)
  /logout   - Clear saved authentication
  exit/quit - Exit the application

[bold cyan]Tips:[/bold cyan]

  • Extended thinking is enabled - Claude will show reasoning process
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
