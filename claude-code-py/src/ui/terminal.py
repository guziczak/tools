"""Terminal UI for Claude chat.

Uses prompt_toolkit PromptSession for input (history, key bindings)
and plain print() for output. No full-screen mode — terminal scrolls
normally, text is selectable, no rendering glitches.
"""

import sys
import threading
import time
from typing import Optional, Iterator, Dict, Any, Callable

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.patch_stdout import patch_stdout

from core.logging import get_logger

logger = get_logger(__name__)


class TerminalUI:
    """Terminal UI with non-blocking streaming output and prompt_toolkit input."""

    def __init__(self):
        self.thinking_buffer = []
        self.text_buffer = []
        self.thinking_visible = False
        self.thinking_token_count = 0
        self.thinking_done_flag = False

        self._print_lock = threading.Lock()
        self._session: Optional[PromptSession] = None

        # Callback set by ClaudeCodePy when user submits input
        self.on_submit: Optional[Callable[[str], None]] = None

        # Double Ctrl+C exit
        self._ctrl_c_time: float = 0.0

        # Cancel callback (returns True if cancelled something)
        self._cancel_callback: Optional[Callable[[], bool]] = None

        # Current thinking status (displayed in prompt toolbar)
        self._thinking_status: str = ""

    def _write(self, text: str, end: str = "\n", flush: bool = True):
        """Thread-safe write to stdout."""
        with self._print_lock:
            sys.stdout.write(text + end)
            if flush:
                sys.stdout.flush()

    # --- High-level print methods ---

    def print_banner(self):
        self._write(
            "\n╔═══════════════════════════════════════════════╗\n"
            "║     Claude Code Python - Sonnet 4.5 MVP      ║\n"
            "║          Extended Thinking Enabled            ║\n"
            "╚═══════════════════════════════════════════════╝\n"
            "Type 'exit' or 'quit' to end session"
        )

    def print_separator(self, title: Optional[str] = None):
        if title:
            self._write(f"\n── {title} ──")
        else:
            self._write("\n────────────────────────────────────")

    def print_error(self, message: str):
        self._write(f"\n[ERROR] {message}")

    def print_info(self, message: str):
        self._write(f"ℹ {message}")

    def print_success(self, message: str):
        self._write(f"✓ {message}")

    def print_output(self, text: str):
        """Write text to output (used by CommandHandler etc.)."""
        self._write(text, end="")

    def set_status(self, text: str):
        """Update thinking status shown in prompt toolbar."""
        self._thinking_status = text
        # Trigger prompt_toolkit to re-render the toolbar
        if self._session and self._session.app and self._session.app.is_running:
            try:
                self._session.app.invalidate()
            except Exception:
                pass

    def clear_screen(self):
        self._write("\033[2J\033[H", end="")

    def print_goodbye(self):
        self._write("\nGoodbye! 👋")

    def get_user_input(self) -> str:
        """Legacy fallback — not used when run() drives the loop."""
        return ""

    # --- Thinking support ---

    def _estimate_tokens(self, text: str) -> int:
        return len(text) // 4

    def print_thinking(self, content: str, is_start: bool = False):
        if is_start:
            self.thinking_buffer = []
            self.thinking_token_count = 0
            self.thinking_done_flag = False
            self.set_status("∴ Thinking...")

        if content:
            self.thinking_buffer.append(content)
            self.thinking_token_count += self._estimate_tokens(content)
            seconds = max(1, self.thinking_token_count // 50)
            self.set_status(f"∴ Thinking... {seconds}s · {self.thinking_token_count} tokens")

            if self.thinking_visible:
                self._write(content, end="")

    def print_thinking_done(self):
        if self.thinking_done_flag:
            return
        self.thinking_done_flag = True

        self.set_status("")  # Clear thinking status

        if self.thinking_buffer:
            total_tokens = sum(self._estimate_tokens(c) for c in self.thinking_buffer)
            seconds = max(1, total_tokens // 50)
            self._write(f"∴ Thinking complete ({seconds}s, {total_tokens} tokens)")

    def toggle_thinking_visibility(self):
        self.thinking_visible = not self.thinking_visible
        if self.thinking_visible and self.thinking_buffer:
            self._write("\n💭 Thinking process:\n")
            self._write("".join(self.thinking_buffer))
        elif not self.thinking_visible:
            self._write("Thinking hidden")

    # --- Tool display ---

    def print_tool_start(self, tool_name: str):
        self._write(f"\n🔧 Using tool: {tool_name}")

    def print_tool_result(self, tool_name: str, result_status: str, output: str):
        icon = "✓" if result_status == "success" else "✗"
        self._write(f"{icon} Tool result ({result_status}):")
        lines = output.strip().split("\n")
        if len(lines) <= 10:
            for line in lines:
                self._write(f"  {line}")
        else:
            for line in lines[:5]:
                self._write(f"  {line}")
            self._write(f"  ... [{len(lines) - 7} more lines] ...")
            for line in lines[-2:]:
                self._write(f"  {line}")

    # --- Streaming ---

    def stream_response_with_tools(self, events: Iterator[Dict[str, Any]], tool_registry=None, cancel_event=None):
        """Stream Claude's response to stdout."""
        self._write("\nClaude: ", end="")
        self.text_buffer = []
        in_thinking = False
        message_done = False

        for event in events:
            if cancel_event and cancel_event.is_set():
                break
            if message_done:
                continue

            event_type = event["type"]
            content = event.get("content", "")

            if event_type == "thinking_start":
                in_thinking = True
                self.print_thinking("", is_start=True)

            elif event_type == "thinking" and in_thinking:
                self.print_thinking(content)

            elif event_type == "text_start":
                if in_thinking:
                    self.print_thinking_done()
                    in_thinking = False

            elif event_type == "text":
                self.text_buffer.append(content)
                self._write(content, end="")

            elif event_type == "tool_use_detected":
                tool_name = event.get("tool_name", "unknown")
                self._write(f"\n🔧 Claude wants to use: {tool_name}")

            elif event_type == "tool_execute":
                tool_name = event["tool_name"]
                tool_input = event["tool_input"]
                result = event["result"]
                self._write(f"⚙️  Executing tool: {tool_name}")
                input_str = str(tool_input)
                if len(input_str) < 100:
                    self._write(f"  Input: {input_str}")
                self.print_tool_result(tool_name, result.status.value, result.output)

            elif event_type == "tool_round_start":
                self._write("\nStarting tool execution...")

            elif event_type == "tool_round_complete":
                self._write(f"Tool execution complete: {content}\n")
                message_done = False
                in_thinking = False
                self.thinking_done_flag = False

            elif event_type == "message_done":
                message_done = True
                if in_thinking:
                    self.print_thinking_done()
                    in_thinking = False
                self._write("")  # newline

            elif event_type == "error":
                self.print_error(content)
                if in_thinking:
                    self.print_thinking_done()
                    in_thinking = False
                break

        if in_thinking:
            self.print_thinking_done()

        self.text_buffer = []

    def stream_response(self, events: Iterator[Dict[str, Any]], tool_callback=None):
        """Stream response (simple version without tools)."""
        self.stream_response_with_tools(events)

    # --- Main input loop using prompt_toolkit ---

    def _get_toolbar(self):
        """Return bottom toolbar text (thinking status)."""
        if self._thinking_status:
            return HTML(f"<style bg='#333333' fg='#88cccc'> {self._thinking_status} </style>")
        return ""

    def run(self):
        """Run the input loop. Output goes to stdout, input via prompt_toolkit."""
        self._session = PromptSession()

        with patch_stdout():
            while True:
                try:
                    user_input = self._session.prompt(
                        HTML("<ansigreen><b>You</b></ansigreen>: "),
                        bottom_toolbar=self._get_toolbar,
                    )
                    user_input = user_input.strip() if user_input else ""
                except KeyboardInterrupt:
                    now = time.monotonic()
                    # If streaming, first Ctrl+C cancels it
                    if self._cancel_callback and self._cancel_callback():
                        self._ctrl_c_time = now
                        continue
                    # Double Ctrl+C within 3s → exit
                    if now - self._ctrl_c_time < 3.0:
                        self.print_goodbye()
                        break
                    self._ctrl_c_time = now
                    self._write("\nPress Ctrl+C again to exit (or type 'exit')")
                    continue
                except EOFError:
                    # Ctrl+D → exit immediately
                    self.print_goodbye()
                    break

                if not user_input:
                    continue

                if user_input.lower() in ("exit", "quit", "q"):
                    self.print_goodbye()
                    break

                if self.on_submit:
                    self.on_submit(user_input)
