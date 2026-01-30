#!/usr/bin/env python3
"""Claude Code Python - Main entry point."""

import os
import sys
import threading
from pathlib import Path
from typing import Optional

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from core.auth import AuthManager, AuthenticationError
from core.logging import get_logger
from ui.terminal import TerminalUI
from config.app_config import AppConfig
from app import Application
from agents.thinking import detect_thinking_level
from utils import check_and_setup, automatic_claude_max_setup

logger = get_logger(__name__)


def _build_system_prompt() -> str:
    """Build the system prompt with current working directory."""
    cwd = os.getcwd()
    return f"""You are helping a developer via a terminal CLI called "Claude Code Python".
The CLI runs on their Windows machine in: {cwd}

The developer's CLI has local tools (bash, read_file, write_file, edit_file) that
run commands on their machine. When you want to explore files, run commands, or
check anything, please output your request as a tool_call block like this:

```tool_call
{{"tool": "bash", "parameters": {{"command": "dir"}}}}
```

The CLI will execute it locally and show you the result. Please use tool_call blocks
instead of the analysis tool, since the developer wants commands to run on THEIR
machine, not in a sandbox.

Working directory: {cwd}
Platform: Windows"""


class CommandHandler:
    """Handles slash commands."""

    def __init__(self, ui: TerminalUI, app: Application, auth_manager: AuthManager):
        self._ui = ui
        self._app = app
        self._auth = auth_manager

    def handle(self, command: str) -> None:
        cmd = command.lower().strip()

        if cmd == "/clear":
            self._ui.clear_screen()
            self._ui.print_banner()
            self._ui.print_success("Screen cleared")
        elif cmd == "/reset":
            self._app.conversation.clear()
            self._ui.print_success("Conversation history cleared")
        elif cmd == "/help":
            self._show_help()
        elif cmd == "/thinking":
            self._ui.toggle_thinking_visibility()
        elif cmd == "/agents":
            self._show_agents()
        elif cmd == "/login":
            self._handle_login()
        elif cmd == "/logout":
            self._handle_logout()
        else:
            self._ui.print_error(f"Unknown command: {command}")
            self._ui.print_info("Type /help for available commands")

    def _handle_login(self) -> None:
        try:
            self._ui.print_info("Starting authentication flow...")
            self._auth.get_access_token(force_reauth=True)
            self._ui.print_success("Authentication successful!")
        except AuthenticationError as e:
            self._ui.print_error(f"Authentication failed: {e}")
        except Exception as e:
            self._ui.print_error(f"Error during login: {e}")

    def _handle_logout(self) -> None:
        self._auth.logout()
        self._ui.print_success("Logged out successfully")
        self._ui.print_info("Your saved authentication has been cleared")

    def _show_agents(self) -> None:
        if not self._app.agent_registry:
            self._ui.print_info("Agents are not enabled")
            return

        self._ui.console.print("\n[bold cyan]Available Specialized Agents:[/bold cyan]\n")
        for agent in self._app.agent_registry._agents.values():
            self._ui.console.print(f"  [bold yellow]{agent.name}[/bold yellow] ({agent.role.value})")
            self._ui.console.print(f"    {agent.description}")
            self._ui.console.print(f"    Keywords: {', '.join(agent.keywords[:5])}")
            self._ui.console.print()
        self._ui.console.print(
            "[dim]Claude will automatically choose the right agent for your task![/dim]\n"
        )

    def _show_help(self) -> None:
        self._ui.console.print("""
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

  - Extended thinking is enabled with real-time token counter
  - Use /thinking to show/hide thinking process after each response
  - Specialized agents available for tests, reviews, debugging, refactoring
  - All messages are kept in conversation history
  - Use Ctrl+C to interrupt at any time
  - First run will open browser for authentication
        """)


class ClaudeCodePy:
    """Main application class - orchestrates UI, auth, and Application."""

    def __init__(self):
        self._ensure_env_file()
        load_dotenv()

        self.ui = TerminalUI()
        self.auth_manager = AuthManager()
        self.config = AppConfig.from_env()
        self.system_prompt = _build_system_prompt()

        self._app: Optional[Application] = None
        self._cmd_handler: Optional[CommandHandler] = None

    # -- kept for compat with existing code referencing self.client --
    @property
    def client(self):
        return self._app.client if self._app else None

    def _ensure_env_file(self) -> None:
        """Ensure .env file exists with sensible defaults."""
        env_path = Path(".env")
        if env_path.exists():
            return

        env_example = Path(".env.example")
        if env_example.exists():
            import shutil
            shutil.copy(env_example, env_path)
        else:
            env_path.write_text(
                "# Claude Code Python Configuration\n"
                "# Auto-generated - feel free to edit!\n\n"
                "# OAuth Configuration (like official Claude Code)\n"
                "CLAUDE_USE_OAUTH=true\n\n"
                "# API Key (leave empty to use OAuth)\n"
                "ANTHROPIC_API_KEY=\n\n"
                "# Model Configuration\n"
                "CLAUDE_MODEL=claude-sonnet-4-20250514\n"
                "CLAUDE_MAX_TOKENS=8000\n"
                "CLAUDE_TEMPERATURE=1.0\n\n"
                "# Extended Thinking\n"
                "CLAUDE_THINKING_ENABLED=true\n"
                "CLAUDE_THINKING_BUDGET=10000\n\n"
                "# Tools & Agents\n"
                "CLAUDE_TOOLS_ENABLED=true\n"
                "CLAUDE_AGENTS_ENABLED=true\n"
            )

    def ensure_authentication(self) -> Optional[str]:
        """Get API key/token from env or interactive setup."""
        # Priority 1: API key from config
        if self.config.api_key:
            key = self.config.api_key
            if key.startswith("sk-ant-sid01-"):
                self.ui.print_info("sessionKey detected - using proxy auth")
            elif key.startswith("sk-ant-oat"):
                self.ui.print_info("OAuth token detected")
            else:
                self.ui.print_info("Using API key from environment")
            return key

        # Priority 2: Interactive setup
        self.ui.print_info("=" * 70)
        self.ui.print_info("  Authentication Setup")
        self.ui.print_info("=" * 70)
        self.ui.print_info("")
        self.ui.print_info("  [1] Claude Max/Pro - AUTO (browser login)")
        self.ui.print_info("  [2] API Key - Manual")
        self.ui.print_info("")
        self.ui.print_info("=" * 70)

        try:
            choice = input("\n  Choose [1/2] (Enter=1): ").strip() or "1"
        except (KeyboardInterrupt, EOFError):
            self.ui.print_info("\nCancelled.")
            return None

        if choice == "1":
            self.ui.print_info("")
            self.ui.print_info("Starting Claude Max automation...")
            from utils.claude_max_setup import automatic_claude_max_setup
            oauth_token = automatic_claude_max_setup()
            if oauth_token:
                return oauth_token
            self.ui.print_info("\nOAuth failed - continuing with API key...")
            choice = "2"

        if choice == "2":
            self.ui.print_info("")
            self.ui.print_info("Starting API key setup...")
            api_key = check_and_setup()
            if api_key:
                return api_key

        self.ui.print_error("Setup failed or cancelled")
        return None

    def initialize(self) -> bool:
        """Authenticate + initialize Application."""
        api_key = self.ensure_authentication()
        if not api_key:
            return False

        # Reload config with the key we got
        # (ensure_authentication may have set env vars)
        import os
        os.environ.setdefault("ANTHROPIC_API_KEY", api_key)
        self.config = AppConfig.from_env()
        # Override api_key in case it came from interactive setup
        if not self.config.api_key:
            object.__setattr__(self.config, 'api_key', api_key)

        self._app = Application(self.config)
        if not self._app.initialize(api_key):
            return False

        self._cmd_handler = CommandHandler(self.ui, self._app, self.auth_manager)

        if self._app.tool_registry:
            self.ui.print_info(f"Tools enabled ({len(self._app.tool_registry)} tools)")
        if self._app.agent_registry:
            self.ui.print_info(f"Agents enabled ({len(self._app.agent_registry)} agents)")

        return True

    def run(self):
        """Run the main chat loop with non-blocking streaming.

        Streaming runs in a background thread so the user can type
        while Claude is still generating output.
        """
        self.ui.print_banner()

        if not self.initialize():
            return

        self.ui.print_info(f"Model: {self.config.model}")
        if self.config.thinking_enabled:
            self.ui.print_info(
                f"Extended Thinking: Enabled (budget: {self.config.thinking_budget} tokens)"
            )
        self.ui.print_separator()

        # Track current streaming state
        self._cancel_event = threading.Event()
        self._stream_thread = None
        self._streaming_lock = threading.Lock()

        try:
            from prompt_toolkit import PromptSession
            from prompt_toolkit.formatted_text import HTML
            session = PromptSession()
        except ImportError:
            session = None

        while True:
            try:
                # Wait for any active streaming to finish before showing prompt
                if self._stream_thread and self._stream_thread.is_alive():
                    self._stream_thread.join()

                if session:
                    try:
                        sys.stdout.write("\n")
                        sys.stdout.flush()
                        user_input = session.prompt(
                            HTML("<ansigreen><b>You</b></ansigreen>: ")
                        )
                        user_input = user_input.strip() if user_input else ""
                    except KeyboardInterrupt:
                        self.ui.print_goodbye()
                        break
                    except EOFError:
                        continue
                else:
                    user_input = self.ui.get_user_input()

                if not user_input:
                    continue
                if user_input.lower() in ("exit", "quit", "q"):
                    self._cancel_event.set()
                    self.ui.print_goodbye()
                    break

                if user_input.startswith("/"):
                    self._cmd_handler.handle(user_input)
                    continue

                self.ui.print_separator()

                # Cancel any previous streaming
                self._cancel_event.set()
                if self._stream_thread and self._stream_thread.is_alive():
                    self._stream_thread.join(timeout=2.0)

                # Start new streaming in background
                self._cancel_event = threading.Event()
                self._stream_thread = threading.Thread(
                    target=self._stream_in_background,
                    args=(user_input, self._cancel_event),
                    daemon=True,
                )
                self._stream_thread.start()

            except KeyboardInterrupt:
                self._cancel_event.set()
                self.ui.print_info("\nInterrupted")
                continue
            except Exception as e:
                logger.exception("Unexpected error")
                self.ui.print_error(f"Unexpected error: {e}")

    def _stream_in_background(self, user_input: str, cancel_event: threading.Event):
        """Run streaming in a background thread."""
        try:
            thinking_level, explicit = detect_thinking_level(user_input)
            if explicit:
                self.ui.print_info(
                    f"Thinking level: {thinking_level.name} ({thinking_level.budget:,} tokens)"
                )

            events = self._app.client.chat_with_tools(
                user_input, system=self.system_prompt
            )
            self.ui.stream_response_with_tools(
                events, self._app.tool_registry, cancel_event=cancel_event
            )
        except Exception as e:
            if not cancel_event.is_set():
                if isinstance(e, AttributeError) and "output_tokens" in str(e):
                    pass
                else:
                    self.ui.print_error(f"API error: {e}")

        if not cancel_event.is_set():
            self.ui.print_separator()


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        from cli_mode import run_cli_mode
        command = sys.argv[1]
        args = sys.argv[2:]
        sys.exit(run_cli_mode(command, args))
    else:
        app = ClaudeCodePy()
        app.run()


if __name__ == "__main__":
    main()
