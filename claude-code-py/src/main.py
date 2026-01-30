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
    platform = "Windows" if os.name == "nt" else "Linux/Mac"
    return (
        f"You are helping a developer via a terminal CLI called 'Claude Code Python'.\n"
        f"Working directory: {cwd}\n"
        f"Platform: {platform}\n"
        f"You have tools available to execute commands, read/write files, and search. "
        f"Use them directly when needed — do not describe tool calls in text."
    )


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

        self._ui.print_output("\nAvailable Specialized Agents:\n\n")
        for agent in self._app.agent_registry._agents.values():
            self._ui.print_output(f"  {agent.name} ({agent.role.value})\n")
            self._ui.print_output(f"    {agent.description}\n")
            self._ui.print_output(f"    Keywords: {', '.join(agent.keywords[:5])}\n\n")
        self._ui.print_output("Claude will automatically choose the right agent for your task!\n")

    def _show_help(self) -> None:
        self._ui.print_output("""
Available Commands:

  /help      - Show this help message
  /thinking  - Toggle thinking process visibility
  /agents    - Show available specialized agents
  /clear     - Clear the screen
  /reset     - Reset conversation history
  /login     - Re-authenticate (OAuth device flow)
  /logout    - Clear saved authentication
  exit/quit  - Exit the application

Thinking Levels:

  think         - Basic thinking (4K tokens)
  think hard    - Standard thinking (10K tokens)
  think harder  - Deep thinking (20K tokens)
  ultrathink    - Maximum thinking (32K tokens)

Tips:

  - Extended thinking is enabled with real-time token counter
  - Use /thinking to show/hide thinking process after each response
  - Specialized agents available for tests, reviews, debugging, refactoring
  - All messages are kept in conversation history
  - Use Ctrl+C to interrupt streaming
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
                "CLAUDE_MODEL=claude-sonnet-4-5-20241022\n"
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

        # Priority 2: Interactive setup (before Textual UI — use print())
        print()
        print("=" * 70)
        print("  Authentication Setup")
        print("=" * 70)
        print()
        print("  [1] Claude Max/Pro (recommended)")
        print("      Opens browser -> login to claude.ai ->")
        print("      auto-extracts sessionKey -> ready to go!")
        print("      Requires: Claude Max/Pro subscription")
        print()
        print("  [2] API Key (manual)")
        print("      Paste your sk-ant-api... key from")
        print("      console.anthropic.com")
        print("      Requires: Pay-as-you-go Anthropic account")
        print()
        print("=" * 70)

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
        return True

    def run(self):
        """Run the main chat loop.

        Initialization that prints to UI happens inside _on_ui_mount
        (after Textual app is running). ui.run() blocks until exit.
        """
        if not self.initialize():
            return

        # Track current streaming state
        self._cancel_event = threading.Event()
        self._stream_thread = None

        # Wire up UI callbacks
        self.ui.set_submit_callback(self._on_user_submit)
        self.ui.set_cancel_callback(self._on_cancel)
        self.ui._on_mount_callback = self._on_ui_mount

        # Run the TUI (blocking)
        self.ui.run()

    def _on_ui_mount(self):
        """Called after Textual app is mounted — safe to write to UI."""
        self.ui.print_banner()
        self.ui.print_info(f"Model: {self.config.model}")
        if self.config.thinking_enabled:
            self.ui.print_info(
                f"Extended Thinking: Enabled (budget: {self.config.thinking_budget} tokens)"
            )
        if self._app and self._app.tool_registry:
            self.ui.print_info(f"Tools enabled ({len(self._app.tool_registry)} tools)")
        if self._app and self._app.agent_registry:
            self.ui.print_info(f"Agents enabled ({len(self._app.agent_registry)} agents)")
        self.ui.print_separator()

    def _on_user_submit(self, user_input: str):
        """Called by UI when user submits input (from main thread).

        Slash commands run synchronously (fast).
        Chat messages start a new streaming thread. Previous stream
        is already finished (run() waits via _stream_done).
        """
        if user_input.startswith("/"):
            self._cmd_handler.handle(user_input)
            return

        self.ui.print_separator()

        # Block prompt BEFORE starting thread to avoid race with _wait_for_stream
        self.ui.mark_streaming()

        # Start streaming in background
        self._cancel_event = threading.Event()
        self._stream_thread = threading.Thread(
            target=self._stream_in_background,
            args=(user_input, self._cancel_event),
            daemon=True,
        )
        self._stream_thread.start()

    def _on_cancel(self) -> bool:
        """Called when user presses Ctrl+C during streaming."""
        if self._stream_thread and self._stream_thread.is_alive():
            self._cancel_event.set()
            self.ui.print_info("Interrupted")
            return True
        return False

    def _stream_in_background(self, user_input: str, cancel_event: threading.Event):
        """Run streaming in a background thread.

        mark_streaming() was called before this thread started,
        so _stream_done MUST be set in all exit paths.
        """
        try:
            thinking_level, explicit = detect_thinking_level(user_input)
            if explicit:
                self.ui.print_info(
                    f"Thinking level: {thinking_level.name} ({thinking_level.budget:,} tokens)"
                )

            events = self._app.client.chat_with_tools(
                user_input, system=self.system_prompt
            )

            def _on_stream_complete():
                if not cancel_event.is_set():
                    self.ui.print_separator()

            self.ui.stream_response_with_tools(
                events, self._app.tool_registry,
                cancel_event=cancel_event,
                on_complete=_on_stream_complete,
            )
        except Exception as e:
            if not cancel_event.is_set():
                if isinstance(e, AttributeError) and "output_tokens" in str(e):
                    pass
                else:
                    self.ui.print_error(f"API error: {e}")
            # stream_response_with_tools was never called or threw before
            # its own finally — ensure prompt is unblocked
            self.ui._stream_done.set()


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
