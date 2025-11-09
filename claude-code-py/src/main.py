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


def _ensure_proxy_dependencies():
    """Ensure Flask and cloudscraper are installed for proxy functionality."""
    missing = []

    # Check Flask
    try:
        import flask
    except ImportError:
        missing.append("flask")

    # Check cloudscraper
    try:
        import cloudscraper
    except ImportError:
        missing.append("cloudscraper")

    # Install missing packages
    if missing:
        import subprocess

        print(f"📦 Installing missing dependencies: {', '.join(missing)}...")
        print("   (This may take a moment...)")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "--user", *missing],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print(f"✅ Successfully installed: {', '.join(missing)}")
            return True
        except subprocess.CalledProcessError:
            # Try without --user flag
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", *missing],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                print(f"✅ Successfully installed: {', '.join(missing)}")
                return True
            except subprocess.CalledProcessError:
                print(f"⚠️  Failed to auto-install: {', '.join(missing)}")
                print(f"   Please run: pip install {' '.join(missing)}")
                return False

    return True


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
            "use_oauth": os.getenv("CLAUDE_USE_OAUTH", "false").lower()
            == "true",  # Default: false (OAuth doesn't work for third-party)
            "tools_enabled": os.getenv("CLAUDE_TOOLS_ENABLED", "true").lower() == "true",
            "agents_enabled": os.getenv("CLAUDE_AGENTS_ENABLED", "true").lower() == "true",
        }

        # System prompt - keep it simple, let the interceptor handle platform quirks
        cwd = os.getcwd()

        self.system_prompt = f"""You are Claude, a helpful AI assistant running in Claude Code Python, a terminal-based LOCAL tool with direct system access.

**Environment:**
- Working Directory: {cwd}
- Platform: Windows LOCAL machine (NOT claude.ai Linux!)
- YOU HAVE DIRECT ACCESS to bash, files, and git repository

🚨 CRITICAL PATH RULES:
- NEVER use /home/claude or /mnt paths - those are claude.ai's Linux environment!
- ALWAYS use relative paths (wierszyk.txt) or Windows paths ({cwd})
- When searching files, use: bash("dir /s /b *.txt") NOT find command

**Available Tools:**
- **bash**: Execute ANY shell command (git, ls, cat, etc.)
- **read_file**: Read file contents
- **write_file**: Create/overwrite files
- **edit_file**: Edit existing files

**🚨 CRITICAL - NEVER ASK USER TO RUN COMMANDS:**

When user asks about code, commits, files, or system info:
1. ✅ IMMEDIATELY use bash/read_file tools
2. ❌ NEVER say "please run X and paste output"
3. ❌ NEVER say "you can run X to see Y"
4. ✅ When user asks "widzisz X?" or "do you see X?" → IMMEDIATELY read_file("X") and show contents

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
      - Dodano funkcję foo()
      - Usunięto starą implementację

      Zmiany w pliku Y:
      - Refactor klasy Bar
      - Nowy moduł security_validator.py

      Główny cel: [cel zmian]
      Wpływ: [co się zmienia dla użytkownika]"

[CRITICAL: Focus on WHAT CHANGED, not meta-commentary about patterns!]
```

Example 2 - File exploration:
```
User: "jakie pliki są w projekcie?"
You: [immediately uses bash("ls -la")]
You: "Projekt zawiera: ..."

User: "pokaż src/main.py"
You: [immediately uses read_file("src/main.py")]
You: "Plik zawiera: ..."

User: "widzisz wierszyk?"
You: [immediately uses read_file("wierszyk.txt")]  ← Use relative path!
You: "Tak! Plik wierszyk.txt zawiera:
     [pokazuje pełną zawartość pliku]"

IMPORTANT:
- When user asks "widzisz X?" → use read_file("X") with RELATIVE PATH
- NEVER search in /home/claude - that's claude.ai's Linux, not your local machine!
- You are on Windows, use Windows paths or relative paths!
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
- User mentions commit hash → ALWAYS use bash("git show HASH")
- User says "przeanalizuj" / "analyze" / "show details" → USE TOOLS
- User says "yes" / "tak" / "sure" after you suggest a command → EXECUTE IT

**You are NOT claude.ai:**
- NO "Projects" feature - use bash to explore
- NO "uploaded files" - files are in {cwd}
- NO asking user to paste - YOU have tools!

Be direct, use tools proactively, and NEVER ask user to manually run commands."""

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
                with open(env_path, "w") as f:
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
            with open(env_path, "r") as f:
                lines = f.readlines()

            # Clear OAuth token and API key lines
            new_lines = []
            for line in lines:
                if line.startswith("CLAUDE_CODE_OAUTH_TOKEN="):
                    new_lines.append("CLAUDE_CODE_OAUTH_TOKEN=\n")
                elif line.startswith("ANTHROPIC_API_KEY="):
                    new_lines.append("ANTHROPIC_API_KEY=\n")
                else:
                    new_lines.append(line)

            # Write back
            with open(env_path, "w") as f:
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
            if self.config["api_key"].startswith("sk-ant-sid01-"):
                self.ui.print_info("✅ sessionKey detected!")
                self.ui.print_info("   Using claude.ai session authentication via proxy")
            elif self.config["api_key"].startswith("sk-ant-oat"):
                self.ui.print_info("✅ OAuth token detected!")
                self.ui.print_info("   Using OAuth Bearer authentication with /v1/messages")
            else:
                self.ui.print_info("Using API key from environment")
            return self.config["api_key"]

        # Priority 2: Check for CLAUDE_CODE_OAUTH_TOKEN (or sessionKey)
        oauth_token = os.getenv("CLAUDE_CODE_OAUTH_TOKEN")
        if oauth_token and oauth_token.strip():
            if oauth_token.startswith("sk-ant-sid01-"):
                self.ui.print_info("✅ sessionKey detected!")
                self.ui.print_info("   Using claude.ai session authentication via proxy")
            else:
                self.ui.print_info("✅ OAuth token detected!")
                self.ui.print_info("   Using OAuth Bearer authentication with /v1/messages")
            return oauth_token

        # Priority 3: Check ~/.claude/.credentials.json (DISABLED - OAuth doesn't work)
        # OAuth tokens don't work with public Anthropic API
        # Skipping this check to force API key setup
        pass

        # Priority 4: Show options
        self.ui.print_info("=" * 70)
        self.ui.print_info("  🔐 Authentication Setup")
        self.ui.print_info("=" * 70)
        self.ui.print_info("")
        self.ui.print_info("  💎 [1] Claude Max/Pro - FULL AUTO!")
        self.ui.print_info("      → Browser → Sign in → DONE!")
        self.ui.print_info("      → Uses local proxy + CloudScraper")
        self.ui.print_info("      → OAuth → claude.ai (bypasses Cloudflare!)")
        self.ui.print_info("")
        self.ui.print_info("  💳 [2] API Key - Manual")
        self.ui.print_info("      → Copy/paste API key")
        self.ui.print_info("      → FREE $5 credit")
        self.ui.print_info("")
        self.ui.print_info("=" * 70)

        # Ask which option
        try:
            choice = input("\n  Choose [1/2] (Enter=1): ").strip() or "1"
        except (KeyboardInterrupt, EOFError):
            self.ui.print_info("\nCancelled.")
            return None

        if choice == "1":
            # OAuth automation!
            self.ui.print_info("")
            self.ui.print_info("🚀 Starting Claude Max automation...")

            from utils.claude_max_setup import automatic_claude_max_setup

            oauth_token = automatic_claude_max_setup()
            if oauth_token:
                return oauth_token

            # Failed - fallback
            self.ui.print_info("\n⚠️  OAuth failed - continuing with API key...")
            choice = "2"

        if choice == "2":
            # Continue with API key setup below
            pass

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

            self.agent_router = AgentRouter(self.agent_registry, Anthropic(api_key=api_key))

        # REVOLUTIONARY: Auto-start proxy for OAuth tokens and sessionKeys!
        if api_key.startswith("sk-ant-oat") or api_key.startswith("sk-ant-sid01-"):
            if api_key.startswith("sk-ant-sid01-"):
                self.ui.print_info("🚀 sessionKey detected - starting local proxy...")
            else:
                self.ui.print_info("🚀 OAuth token detected - starting local proxy...")

            # Ensure proxy dependencies are installed
            _ensure_proxy_dependencies()

            try:
                from proxy import start_proxy_server, get_proxy_base_url

                # Start proxy in background (returns tuple: success, port)
                proxy_started, proxy_port = start_proxy_server(api_key, port=8765)
                if proxy_started:
                    self.ui.print_info("✅ Proxy server started!")
                    self.ui.print_info("   OAuth → claude.ai translation active")

                    # Use proxy URL as base for API client (with actual port used)
                    import os

                    proxy_url = get_proxy_base_url(proxy_port)
                    os.environ["ANTHROPIC_BASE_URL"] = proxy_url
                    self.ui.print_info(f"   Set ANTHROPIC_BASE_URL={proxy_url}")

                    # Give proxy time to start
                    import time

                    time.sleep(1)
                else:
                    self.ui.print_error("❌ Failed to start proxy - OAuth may not work")
            except Exception as e:
                self.ui.print_error(f"⚠️  Proxy error: {e}")
                self.ui.print_info("   Continuing anyway...")

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
                        self.ui.print_info(
                            f"Thinking level: {thinking_level.name} ({thinking_level.budget:,} tokens)"
                        )

                    # Use chat_with_tools if tools/agents are enabled
                    if self.tool_registry or self.agent_registry:
                        events = self.client.chat_with_tools(user_input, system=self.system_prompt)
                    else:
                        events = self.client.chat(user_input, system=self.system_prompt)

                    self.ui.stream_response_with_tools(events, self.tool_registry)
                except KeyboardInterrupt:
                    # Ctrl+C during streaming - propagate to outer handler
                    self.ui.print_info("\n⚠️  Interrupted by user (Ctrl+C)")
                    raise
                except AttributeError as e:
                    # SDK parsing error (output_tokens) - ignore, response already displayed
                    if "output_tokens" in str(e):
                        pass  # Ignore - this is SDK trying to parse claude.ai response
                    else:
                        self.ui.print_error(f"API error: {e}")
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

        elif cmd == "/thinking":
            self.ui.toggle_thinking_visibility()

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

        self.ui.console.print(
            "[dim]Claude will automatically choose the right agent for your task![/dim]\n"
        )

    def show_help(self):
        """Show help message."""
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
  • First run will open browser for authentication
        """
        self.ui.console.print(help_text)


def main():
    """Main entry point."""
    app = ClaudeCodePy()
    app.run()


if __name__ == "__main__":
    main()
