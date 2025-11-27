"""CLI Mode for Claude Code Python.

Provides CLI commands similar to the original TypeScript implementation.
Usage: python claude.py ask "question"
       python claude.py explain file.py
       python claude.py refactor app.js --focus performance
"""

import sys
import os
from pathlib import Path
from typing import List, Optional
import logging

from rich.console import Console
from dotenv import load_dotenv

from core.api_client import ClaudeAPIClient
from prompts import use_template, get_language_from_filepath
from fileops import FileOperationsManager
from errors import format_error_for_display, create_user_error, ErrorCategory

logger = logging.getLogger(__name__)


class CLIMode:
    """CLI mode handler for one-off commands."""

    def __init__(self):
        """Initialize CLI mode."""
        # Load environment
        load_dotenv()

        self.console = Console()
        self.api_client: Optional[ClaudeAPIClient] = None
        self.file_ops: Optional[FileOperationsManager] = None

    def initialize(self) -> bool:
        """Initialize API client and file operations.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get API key
            api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_CODE_OAUTH_TOKEN")

            if not api_key:
                self.console.print("[red]Error: No API key found[/red]")
                self.console.print("Set ANTHROPIC_API_KEY environment variable or run in REPL mode to authenticate.")
                return False

            # Initialize API client
            self.api_client = ClaudeAPIClient(
                api_key=api_key,
                model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514"),
                max_tokens=int(os.getenv("CLAUDE_MAX_TOKENS", "8000")),
                thinking_enabled=os.getenv("CLAUDE_THINKING_ENABLED", "true").lower() == "true",
            )

            # Initialize file operations
            self.file_ops = FileOperationsManager()

            return True

        except Exception as e:
            self.console.print(f"[red]Initialization error: {e}[/red]")
            return False

    def execute(self, command: str, args: List[str]) -> int:
        """Execute a CLI command.

        Args:
            command: Command name (e.g., 'ask', 'explain')
            args: Command arguments

        Returns:
            Exit code (0 for success, 1 for error)
        """
        if not self.initialize():
            return 1

        try:
            if command == "ask":
                return self.cmd_ask(args)
            elif command == "explain":
                return self.cmd_explain(args)
            elif command == "refactor":
                return self.cmd_refactor(args)
            elif command == "fix":
                return self.cmd_fix(args)
            elif command == "review":
                return self.cmd_review(args)
            elif command == "generate":
                return self.cmd_generate(args)
            elif command == "help":
                return self.cmd_help(args)
            elif command == "version":
                return self.cmd_version(args)
            else:
                self.console.print(f"[red]Unknown command: {command}[/red]")
                self.console.print("Run 'claude help' for available commands")
                return 1

        except KeyboardInterrupt:
            self.console.print("\n[yellow]Interrupted by user[/yellow]")
            return 1

        except Exception as e:
            self.console.print(format_error_for_display(e))
            return 1

    def cmd_ask(self, args: List[str]) -> int:
        """Ask command - ask Claude a question.

        Usage: claude ask "question"
        """
        if not args:
            self.console.print("[red]Error: Question required[/red]")
            self.console.print("Usage: claude ask \"your question\"")
            return 1

        question = " ".join(args)

        self.console.print(f"[cyan]Asking Claude...[/cyan]\n")

        try:
            response = self.api_client.chat(question)

            # Extract text from response
            if hasattr(response, 'content') and response.content:
                for block in response.content:
                    if hasattr(block, 'text'):
                        self.console.print(block.text)
            else:
                self.console.print(response)

            return 0

        except Exception as e:
            self.console.print(format_error_for_display(e))
            return 1

    def cmd_explain(self, args: List[str]) -> int:
        """Explain command - explain code from a file.

        Usage: claude explain file.py
        """
        if not args:
            self.console.print("[red]Error: File path required[/red]")
            self.console.print("Usage: claude explain <file>")
            return 1

        file_path = args[0]

        # Read file
        result = self.file_ops.read_file(file_path)

        if not result.success:
            self.console.print(format_error_for_display(result.error))
            return 1

        # Get language
        language = get_language_from_filepath(file_path)

        # Use template
        prompt, system = use_template("explain_code", code=result.content, language=language)

        self.console.print(f"[cyan]Explaining {file_path}...[/cyan]\n")

        try:
            response = self.api_client.chat(prompt, system=system)

            # Extract text from response
            if hasattr(response, 'content') and response.content:
                for block in response.content:
                    if hasattr(block, 'text'):
                        self.console.print(block.text)
            else:
                self.console.print(response)

            return 0

        except Exception as e:
            self.console.print(format_error_for_display(e))
            return 1

    def cmd_refactor(self, args: List[str]) -> int:
        """Refactor command - refactor code from a file.

        Usage: claude refactor file.py --focus <aspect>
        """
        if not args:
            self.console.print("[red]Error: File path required[/red]")
            self.console.print("Usage: claude refactor <file> [--focus <aspect>]")
            return 1

        file_path = args[0]
        focus = "readability and maintainability"

        # Parse --focus argument
        if "--focus" in args:
            try:
                focus_idx = args.index("--focus")
                if focus_idx + 1 < len(args):
                    focus = args[focus_idx + 1]
            except (ValueError, IndexError):
                pass

        # Read file
        result = self.file_ops.read_file(file_path)

        if not result.success:
            self.console.print(format_error_for_display(result.error))
            return 1

        # Get language
        language = get_language_from_filepath(file_path)

        # Use template
        prompt, system = use_template(
            "refactor_code",
            code=result.content,
            language=language,
            focus=focus,
            context="None",
        )

        self.console.print(f"[cyan]Refactoring {file_path} with focus on {focus}...[/cyan]\n")

        try:
            response = self.api_client.chat(prompt, system=system)

            # Extract text from response
            if hasattr(response, 'content') and response.content:
                for block in response.content:
                    if hasattr(block, 'text'):
                        self.console.print(block.text)
            else:
                self.console.print(response)

            return 0

        except Exception as e:
            self.console.print(format_error_for_display(e))
            return 1

    def cmd_fix(self, args: List[str]) -> int:
        """Fix command - fix issues in code.

        Usage: claude fix file.py [--issue "description"]
        """
        if not args:
            self.console.print("[red]Error: File path required[/red]")
            self.console.print("Usage: claude fix <file> [--issue \"description\"]")
            return 1

        file_path = args[0]
        issue = "Fix any issues found in the code"

        # Parse --issue argument
        if "--issue" in args:
            try:
                issue_idx = args.index("--issue")
                if issue_idx + 1 < len(args):
                    issue = " ".join(args[issue_idx + 1:])
            except (ValueError, IndexError):
                pass

        # Read file
        result = self.file_ops.read_file(file_path)

        if not result.success:
            self.console.print(format_error_for_display(result.error))
            return 1

        # Get language
        language = get_language_from_filepath(file_path)

        # Use template
        prompt, system = use_template(
            "fix_code",
            code=result.content,
            language=language,
            issue=issue,
        )

        self.console.print(f"[cyan]Fixing {file_path}...[/cyan]\n")

        try:
            response = self.api_client.chat(prompt, system=system)

            # Extract text from response
            if hasattr(response, 'content') and response.content:
                for block in response.content:
                    if hasattr(block, 'text'):
                        self.console.print(block.text)
            else:
                self.console.print(response)

            return 0

        except Exception as e:
            self.console.print(format_error_for_display(e))
            return 1

    def cmd_review(self, args: List[str]) -> int:
        """Review command - review code from a file.

        Usage: claude review file.py
        """
        if not args:
            self.console.print("[red]Error: File path required[/red]")
            self.console.print("Usage: claude review <file>")
            return 1

        file_path = args[0]

        # Read file
        result = self.file_ops.read_file(file_path)

        if not result.success:
            self.console.print(format_error_for_display(result.error))
            return 1

        # Get language
        language = get_language_from_filepath(file_path)

        # Use template
        prompt, system = use_template("review_code", code=result.content, language=language)

        self.console.print(f"[cyan]Reviewing {file_path}...[/cyan]\n")

        try:
            response = self.api_client.chat(prompt, system=system)

            # Extract text from response
            if hasattr(response, 'content') and response.content:
                for block in response.content:
                    if hasattr(block, 'text'):
                        self.console.print(block.text)
            else:
                self.console.print(response)

            return 0

        except Exception as e:
            self.console.print(format_error_for_display(e))
            return 1

    def cmd_generate(self, args: List[str]) -> int:
        """Generate command - generate code.

        Usage: claude generate "task description" [--language python]
        """
        if not args:
            self.console.print("[red]Error: Task description required[/red]")
            self.console.print("Usage: claude generate \"task\" [--language <lang>]")
            return 1

        # Parse arguments
        task_args = []
        language = "Python"

        i = 0
        while i < len(args):
            if args[i] == "--language" and i + 1 < len(args):
                language = args[i + 1]
                i += 2
            else:
                task_args.append(args[i])
                i += 1

        task = " ".join(task_args)

        # Use template
        prompt, system = use_template(
            "generate_code",
            task=task,
            language=language,
            requirements="- Follow best practices\n- Include error handling\n- Add helpful comments",
        )

        self.console.print(f"[cyan]Generating {language} code...[/cyan]\n")

        try:
            response = self.api_client.chat(prompt, system=system)

            # Extract text from response
            if hasattr(response, 'content') and response.content:
                for block in response.content:
                    if hasattr(block, 'text'):
                        self.console.print(block.text)
            else:
                self.console.print(response)

            return 0

        except Exception as e:
            self.console.print(format_error_for_display(e))
            return 1

    def cmd_help(self, args: List[str]) -> int:
        """Help command - show help information."""
        help_text = """
[bold cyan]Claude Code Python - CLI Mode[/bold cyan]

[bold]Usage:[/bold]
  claude <command> [arguments] [options]

[bold]Available Commands:[/bold]

  [yellow]ask[/yellow] <question>
    Ask Claude a question about code or programming
    Example: claude ask "How do I implement a binary search tree?"

  [yellow]explain[/yellow] <file>
    Explain code from a file
    Example: claude explain app.py

  [yellow]refactor[/yellow] <file> [--focus <aspect>]
    Refactor code to improve quality
    Example: claude refactor app.js --focus performance

  [yellow]fix[/yellow] <file> [--issue "description"]
    Fix issues in code
    Example: claude fix bug.py --issue "IndexError on line 42"

  [yellow]review[/yellow] <file>
    Review code and provide feedback
    Example: claude review main.ts

  [yellow]generate[/yellow] <task> [--language <lang>]
    Generate code for a task
    Example: claude generate "REST API with auth" --language python

  [yellow]help[/yellow]
    Show this help message

  [yellow]version[/yellow]
    Show version information

[bold]For interactive mode:[/bold]
  Run 'claude' without arguments to start the REPL

[bold]Tips:[/bold]
  • Set ANTHROPIC_API_KEY environment variable for API access
  • Use quotes for multi-word arguments
  • Add --help after any command for command-specific help
        """
        self.console.print(help_text)
        return 0

    def cmd_version(self, args: List[str]) -> int:
        """Version command - show version information."""
        self.console.print("[bold cyan]Claude Code Python[/bold cyan]")
        self.console.print("Version: 0.2.0 (Enhanced)")
        self.console.print("Based on: @anthropic-ai/claude-code")
        return 0


def run_cli_mode(command: str, args: List[str]) -> int:
    """Run CLI mode with the given command.

    Args:
        command: Command name
        args: Command arguments

    Returns:
        Exit code
    """
    cli = CLIMode()
    return cli.execute(command, args)
