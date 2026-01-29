#!/usr/bin/env python3
"""Claude Code Python - Main entry point."""

import os
import sys
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
    return f"""You are Claude, a helpful AI assistant running in Claude Code Python, a terminal-based LOCAL tool with direct system access.

**Environment:**
- Working Directory: {cwd}
- Platform: Windows LOCAL machine (NOT claude.ai Linux!)
- YOU HAVE DIRECT ACCESS to bash, files, and git repository

CRITICAL PATH RULES:
- NEVER use /home/claude or /mnt paths - those are claude.ai's Linux environment!
- ALWAYS use relative paths (wierszyk.txt) or Windows paths ({cwd})
- When searching files, use: bash("dir /s /b *.txt") NOT find command

**Available Tools:**
- **bash**: Execute ANY shell command (git, ls, cat, etc.)
- **read_file**: Read file contents
- **write_file**: Create/overwrite files
- **edit_file**: Edit existing files

**CRITICAL - NEVER ASK USER TO RUN COMMANDS:**

When user asks about code, commits, files, or system info:
1. IMMEDIATELY use bash/read_file tools
2. NEVER say "please run X and paste output"
3. NEVER say "you can run X to see Y"
4. When user asks "widzisz X?" or "do you see X?" -> IMMEDIATELY read_file("X") and show contents

**Few-Shot Examples (FOLLOW THESE EXACTLY):**

Example 1 - Git commit analysis:
```
User: "widzisz ostatniego commita?"
You: [immediately uses bash("git log -1")]
You: "Tak, ostatni commit to abc123..."

User: "przeanalizuj zmiany"
You: [YOU WILL RECEIVE FULL DIFF FROM git show IN YOUR CONTEXT]
You: "Analiza zmian w commicie abc123:

      Zmiany w pliku X (linie 10-20):
      - Dodano funkcje foo()
      - Usunieto stara implementacje

      Zmiany w pliku Y:
      - Refactor klasy Bar
      - Nowy modul security_validator.py

      Glowny cel: [cel zmian]
      Wplyw: [co sie zmienia dla uzytkownika]"

[CRITICAL: Focus on WHAT CHANGED, not meta-commentary about patterns!]
```

Example 2 - File exploration:
```
User: "jakie pliki sa w projekcie?"
You: [immediately uses bash("ls -la")]
You: "Projekt zawiera: ..."

User: "pokaz src/main.py"
You: [immediately uses read_file("src/main.py")]
You: "Plik zawiera: ..."
```

Example 3 - Follow-up questions:
```
User: "show me git log"
You: [uses bash("git log -10")]
You: "Here are the last 10 commits..."

User: "tell me more about commit abc123"
You: [uses bash("git show abc123")]
You: "That commit changed: ..."
```

**Key Pattern:**
- User mentions commit hash -> ALWAYS use bash("git show HASH")
- User says "przeanalizuj" / "analyze" / "show details" -> USE TOOLS
- User says "yes" / "tak" / "sure" after you suggest a command -> EXECUTE IT

**You are NOT claude.ai:**
- NO "Projects" feature - use bash to explore
- NO "uploaded files" - files are in {cwd}
- NO asking user to paste - YOU have tools!

Be direct, use tools proactively, and NEVER ask user to manually run commands."""


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
        """Run the main chat loop."""
        self.ui.print_banner()

        if not self.initialize():
            return

        self.ui.print_info(f"Model: {self.config.model}")
        if self.config.thinking_enabled:
            self.ui.print_info(
                f"Extended Thinking: Enabled (budget: {self.config.thinking_budget} tokens)"
            )
        self.ui.print_separator()

        while True:
            try:
                user_input = self.ui.get_user_input()
                if not user_input:
                    continue
                if user_input.lower() in ("exit", "quit", "q"):
                    self.ui.print_goodbye()
                    break

                if user_input.startswith("/"):
                    self._cmd_handler.handle(user_input)
                    continue

                self.ui.print_separator()
                try:
                    thinking_level, explicit = detect_thinking_level(user_input)
                    if explicit:
                        self.ui.print_info(
                            f"Thinking level: {thinking_level.name} ({thinking_level.budget:,} tokens)"
                        )

                    # Always use chat_with_tools (pipeline handles both paths)
                    events = self._app.client.chat_with_tools(
                        user_input, system=self.system_prompt
                    )
                    self.ui.stream_response_with_tools(events, self._app.tool_registry)
                except KeyboardInterrupt:
                    self.ui.print_info("\nInterrupted by user (Ctrl+C)")
                    raise
                except AttributeError as e:
                    if "output_tokens" not in str(e):
                        self.ui.print_error(f"API error: {e}")
                except Exception as e:
                    self.ui.print_error(f"API error: {e}")

                self.ui.print_separator()

            except KeyboardInterrupt:
                self.ui.print_goodbye()
                break
            except Exception as e:
                logger.exception("Unexpected error")
                self.ui.print_error(f"Unexpected error: {e}")


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
