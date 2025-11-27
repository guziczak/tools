"""Rich terminal interface for Claude chat."""

from typing import Optional, Iterator, Dict, Any
from rich.console import Console
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from rich.prompt import Prompt
from rich.rule import Rule
import sys


class TerminalUI:
    """Rich terminal interface for Claude interactions."""

    def __init__(self):
        """Initialize terminal UI."""
        self.console = Console()
        self.thinking_buffer = []
        self.text_buffer = []
        self.current_tool = None
        self.tool_buffer = []
        self.thinking_visible = False  # Start with thinking hidden
        self.thinking_token_count = 0
        self.thinking_live = None  # Live display for thinking progress
        self.thinking_done_flag = False  # Prevent duplicate print_thinking_done() calls

    def print_banner(self):
        """Print welcome banner."""
        banner = """
╔═══════════════════════════════════════════════╗
║     Claude Code Python - Sonnet 4.5 MVP      ║
║          Extended Thinking Enabled            ║
╚═══════════════════════════════════════════════╝
        """
        self.console.print(banner, style="bold cyan")
        self.console.print("Type 'exit' or 'quit' to end session\n", style="dim")

    def print_separator(self, title: Optional[str] = None):
        """Print a visual separator."""
        if title:
            self.console.print(Rule(title, style="dim"))
        else:
            self.console.print(Rule(style="dim"))

    def get_user_input(self) -> str:
        """Get input from user with rich prompt."""
        # CRITICAL: Ensure Live display is closed before asking for input
        # Otherwise Rich's Live will interfere with Prompt
        # DEFENSIVE: Try multiple times to ensure Live is truly closed
        if self.thinking_live:
            try:
                # First attempt: normal close
                self.thinking_live.__exit__(None, None, None)
            except Exception:
                pass  # Ignore if already closed
            finally:
                self.thinking_live = None

        # DEFENSIVE: Force flush console to ensure all output is displayed
        try:
            self.console.file.flush()
        except Exception:
            pass  # Ignore if flush fails

        self.console.print()  # Blank line before prompt
        try:
            user_input = Prompt.ask("[bold green]You[/bold green]", console=self.console)
            return user_input.strip()
        except EOFError:
            # EOF (Ctrl+D on Unix, Ctrl+Z on Windows) - return empty to continue
            return ""
        except KeyboardInterrupt:
            # Ctrl+C - re-raise to trigger exit in main loop
            raise

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation: ~4 chars = 1 token)."""
        return len(text) // 4

    def print_thinking(self, content: str, is_start: bool = False):
        """Print thinking content with collapsible /thinking toggle."""
        if is_start:
            print(f"🐛 [DEBUG print_thinking] is_start=True, creating new Live")
            self.thinking_buffer = []
            self.thinking_token_count = 0
            self.thinking_done_flag = False  # Reset flag for new thinking session
            # Start Live display for progress
            self.thinking_live = Live(
                Text("∴ Thinking... (type '/thinking' to show)", style="dim cyan"),
                console=self.console,
                refresh_per_second=10,
            )
            self.thinking_live.__enter__()

        if content:
            self.thinking_buffer.append(content)
            self.thinking_token_count += self._estimate_tokens(content)

            # Update Live display with current progress
            if self.thinking_live:
                # More realistic time estimate: ~50 tokens/sec for thinking
                seconds = max(1, self.thinking_token_count // 50)
                print(f"🐛 [DEBUG print_thinking] Updating Live: {seconds}s · {self.thinking_token_count} tokens")
                self.thinking_live.update(
                    Text(
                        f"∴ Thinking... {seconds}s · {self.thinking_token_count} tokens (type '/thinking' to show)",
                        style="dim cyan",
                    )
                )

            # If thinking is visible, show actual content
            if self.thinking_visible:
                self.console.print(content, end="", style="dim italic cyan")

    def print_thinking_done(self):
        """Print when thinking is complete.

        Uses thinking_done_flag to prevent duplicate calls (defensive programming).
        """
        # DEFENSIVE: Prevent duplicate calls
        if self.thinking_done_flag:
            return  # Already called, skip silently

        self.thinking_done_flag = True  # Mark as done

        # Stop Live display (only if it's active)
        if self.thinking_live:
            try:
                self.thinking_live.__exit__(None, None, None)
            except Exception:
                pass  # Ignore errors if already closed
            self.thinking_live = None

        if self.thinking_buffer:
            # Final summary
            total_tokens = sum(self._estimate_tokens(chunk) for chunk in self.thinking_buffer)
            seconds = max(1, total_tokens // 50)
            self.console.print(
                f"[dim cyan]∴ Thinking complete ({seconds}s, {total_tokens} tokens) - type '/thinking' to view[/dim cyan]"
            )

            if self.thinking_visible:
                self.console.print()  # New line after visible thinking

            self.console.print()  # Extra line
            # Keep buffer for /thinking command
            # self.thinking_buffer = []

    def toggle_thinking_visibility(self):
        """Toggle thinking visibility and show/hide last thinking."""
        self.thinking_visible = not self.thinking_visible

        if self.thinking_visible and self.thinking_buffer:
            self.console.print("\n[bold cyan]💭 Thinking process:[/bold cyan]\n")
            thinking_text = "".join(self.thinking_buffer)
            self.console.print(thinking_text, style="dim italic cyan")
            self.console.print()
        elif not self.thinking_visible:
            self.console.print("[dim]Thinking hidden[/dim]")

    def print_tool_start(self, tool_name: str):
        """Print when tool usage starts."""
        self.current_tool = tool_name
        self.tool_buffer = []
        self.console.print(
            f"\n[yellow]🔧 Using tool:[/yellow] [bold yellow]{tool_name}[/bold yellow]"
        )

    def print_tool_result(self, tool_name: str, result_status: str, output: str):
        """Print tool execution result."""
        # Status icon
        if result_status == "success":
            status_icon = "[green]✓[/green]"
            status_text = "[green]Success[/green]"
        else:
            status_icon = "[red]✗[/red]"
            status_text = "[red]Error[/red]"

        self.console.print(f"{status_icon} Tool result ({status_text}):")

        # Show output (truncated if too long)
        lines = output.strip().split("\n")
        if len(lines) <= 10:
            # Show all lines
            for line in lines:
                self.console.print(f"  {line}", style="dim")
        else:
            # Show first 5 and last 2
            for line in lines[:5]:
                self.console.print(f"  {line}", style="dim")
            self.console.print(f"  [dim italic]... [{len(lines) - 7} more lines] ...[/dim italic]")
            for line in lines[-2:]:
                self.console.print(f"  {line}", style="dim")

        self.console.print()  # Blank line after tool result
        self.current_tool = None

    def stream_response(self, events: Iterator[Dict[str, Any]], tool_callback=None):
        """Stream and display Claude's response.

        Args:
            events: Iterator of event dictionaries from API client
            tool_callback: Optional callback for tool execution
        """
        self.console.print("[bold blue]Claude[/bold blue]:", end=" ")
        self.text_buffer = []
        in_thinking = False
        in_tool_use = False

        for event in events:
            event_type = event["type"]
            content = event["content"]

            if event_type == "thinking_start":
                print(f"🐛 [DEBUG] thinking_start received! in_thinking={in_thinking}")
                in_thinking = True
                self.print_thinking("", is_start=True)

            elif event_type == "thinking" and in_thinking:
                print(f"🐛 [DEBUG] thinking delta! len={len(content) if content else 0}")
                self.print_thinking(content)

            elif event_type == "text_start":
                if in_thinking:
                    self.print_thinking_done()
                    in_thinking = False

            elif event_type == "text":
                self.text_buffer.append(content)
                # FIX: Use file.write + flush to prevent broken fragments (stream_response)
                self.console.file.write(content)
                self.console.file.flush()

            elif event_type == "tool_use_start":
                in_tool_use = True
                tool_name = event.get("tool_name", "unknown")
                tool_id = event.get("tool_id", "")
                self.print_tool_start(tool_name)

                # Execute tool if callback provided
                if tool_callback:
                    # TODO: Get tool input from event
                    # For now, just show that tool was requested
                    pass

            elif event_type == "block_stop":
                if in_thinking:
                    self.print_thinking_done()
                    in_thinking = False
                if in_tool_use:
                    in_tool_use = False

            elif event_type == "message_done":
                self.console.print()  # New line at end
                # DON'T break - let generator finish naturally

        # Ensure we close thinking if still open
        if in_thinking:
            self.print_thinking_done()

        # CRITICAL: Force close Live display even if print_thinking_done() was already called
        # This prevents Live from running in background and interfering with terminal
        if self.thinking_live:
            try:
                self.thinking_live.__exit__(None, None, None)
            except Exception:
                pass
            self.thinking_live = None

        self.text_buffer = []

    def print_error(self, message: str):
        """Print error message."""
        self.console.print(f"\n[bold red]Error:[/bold red] {message}\n")

    def print_info(self, message: str):
        """Print info message."""
        self.console.print(f"[cyan]ℹ[/cyan] {message}")

    def print_success(self, message: str):
        """Print success message."""
        self.console.print(f"[green]✓[/green] {message}")

    def clear_screen(self):
        """Clear the terminal screen."""
        self.console.clear()

    def stream_response_with_tools(self, events: Iterator[Dict[str, Any]], tool_registry=None):
        """Stream and display Claude's response with tool execution support.

        Args:
            events: Iterator of event dictionaries from API client
            tool_registry: Tool registry for executing tools (optional)
        """
        self.console.print("[bold blue]Claude[/bold blue]:", end=" ")
        self.text_buffer = []
        in_thinking = False
        in_tool_use = False
        message_done = False

        for event in events:
            # Skip any events after message is done
            if message_done:
                continue
            event_type = event["type"]
            content = event.get("content", "")

            if event_type == "thinking_start":
                print(f"🐛 [DEBUG] thinking_start received! in_thinking={in_thinking}")
                in_thinking = True
                self.print_thinking("", is_start=True)

            elif event_type == "thinking" and in_thinking:
                print(f"🐛 [DEBUG] thinking delta! len={len(content) if content else 0}")
                self.print_thinking(content)

            elif event_type == "text_start":
                if in_thinking:
                    self.print_thinking_done()
                    in_thinking = False

            elif event_type == "text":
                self.text_buffer.append(content)
                # FIX: Use file.write + flush to prevent broken fragments (stream_response_with_tools)
                self.console.file.write(content)
                self.console.file.flush()

            elif event_type == "tool_use_detected":
                # Tool use was detected in streaming
                tool_name = event.get("tool_name", "unknown")
                self.console.print(
                    f"\n[yellow]🔧 Claude wants to use:[/yellow] [bold yellow]{tool_name}[/bold yellow]"
                )

            elif event_type == "tool_execute":
                # Tool was executed
                tool_name = event["tool_name"]
                tool_input = event["tool_input"]
                result = event["result"]

                self.console.print(
                    f"[yellow]⚙️  Executing tool:[/yellow] [bold yellow]{tool_name}[/bold yellow]"
                )

                # Show input (if not too long)
                input_str = str(tool_input)
                if len(input_str) < 100:
                    self.console.print(f"  Input: {input_str}", style="dim yellow")

                # Show result
                self.print_tool_result(tool_name, result.status.value, result.output)

            elif event_type == "tool_round_start":
                self.console.print(f"\n[dim cyan]Starting tool execution...[/dim cyan]")

            elif event_type == "tool_round_complete":
                self.console.print(f"[dim cyan]Tool execution complete: {content}[/dim cyan]\n")
                # CRITICAL: Reset state for next round!
                # After tool execution, Claude will send new response
                # We need to process those events, not skip them
                message_done = False
                # Reset thinking state to prevent duplicates in next round
                # But DON'T clear thinking_buffer (user needs it for /thinking command!)
                in_thinking = False
                self.thinking_done_flag = False  # Allow new thinking in next round

            elif event_type == "message_done":
                # Message streaming complete
                message_done = True
                if in_thinking:
                    self.print_thinking_done()
                    in_thinking = False
                # Ensure console is flushed before newline
                if self.text_buffer:
                    pass  # Text already printed
                self.console.print()  # New line at end
                # DON'T break yet! Continue consuming events to allow API client
                # to check for tool_blocks and execute next round
                # The loop will end naturally when generator is exhausted

            elif event_type == "error":
                self.print_error(content)
                if in_thinking:
                    self.print_thinking_done()
                    in_thinking = False
                break

        # Ensure we close thinking if still open (fallback)
        if in_thinking:
            self.print_thinking_done()

        # CRITICAL: Force close Live display even if print_thinking_done() was already called
        # This prevents Live from running in background and interfering with terminal
        if self.thinking_live:
            try:
                self.thinking_live.__exit__(None, None, None)
            except Exception:
                pass
            self.thinking_live = None

        self.text_buffer = []

    def print_goodbye(self):
        """Print goodbye message."""
        self.console.print("\n[bold cyan]Goodbye! 👋[/bold cyan]\n")
