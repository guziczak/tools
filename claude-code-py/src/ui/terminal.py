"""Terminal UI for Claude chat — Textual TUI.

Full-screen terminal app with separate output panel (scrollable) and input
field. User can type while streaming output appears above. Streaming text
is written from a background thread via ``call_from_thread``.
"""

import re
import threading
from typing import Optional, Iterator, Dict, Any, Callable

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Input, RichLog, Footer

from core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Textual App
# ---------------------------------------------------------------------------

class ChatApp(App):
    """Full-screen chat TUI.

    Layout:
        ┌─────────────────────────┐
        │  RichLog (scrollable)   │  ← streaming output
        ├─────────────────────────┤
        │  Input                  │  ← user types here
        └─────────────────────────┘
    """

    CSS = """
    RichLog {
        height: 1fr;
        border: none;
        scrollbar-size: 1 1;
    }
    Input {
        dock: bottom;
        height: auto;
        min-height: 1;
    }
    Footer {
        dock: bottom;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "cancel_or_quit", "Cancel / Quit", show=True),
    ]

    def __init__(self, terminal_ui: "TerminalUI"):
        super().__init__()
        self._terminal_ui = terminal_ui
        self._ctrl_c_time: float = 0.0

    def compose(self) -> ComposeResult:
        yield RichLog(id="output", wrap=True, markup=True, auto_scroll=True)
        yield Input(id="user_input", placeholder="Type your message...")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#user_input", Input).focus()
        if self._terminal_ui._on_mount_callback:
            self.set_timer(0.1, lambda: self._terminal_ui._on_mount_callback())

    def on_input_submitted(self, event: Input.Submitted) -> None:
        user_input = event.value.strip()
        self.query_one("#user_input", Input).value = ""

        if not user_input:
            return

        if user_input.lower() in ("exit", "quit", "q"):
            self._terminal_ui._write_to_log("\nGoodbye! 👋")
            self.exit()
            return

        # Handle /cpy command directly in UI
        if user_input.lower() == "/cpy":
            self._terminal_ui.copy_all()
            return

        self._terminal_ui._write_to_log(f"\n[bold green]You[/bold green]: {user_input}")

        if self._terminal_ui._on_submit:
            self._terminal_ui._on_submit(user_input)

    def action_cancel_or_quit(self) -> None:
        import time
        if self._terminal_ui._is_streaming():
            if self._terminal_ui._on_cancel:
                self._terminal_ui._on_cancel()
            return
        now = time.monotonic()
        if now - self._ctrl_c_time < 3.0:
            self._terminal_ui._write_to_log("\nGoodbye! 👋")
            self.exit()
        else:
            self._ctrl_c_time = now
            self._terminal_ui._write_to_log("Press Ctrl+C again to exit (or type 'exit')")


# ---------------------------------------------------------------------------
# TerminalUI — public interface (unchanged for main.py)
# ---------------------------------------------------------------------------

class TerminalUI:
    """Terminal UI backed by Textual.

    Public API is identical to the previous prompt_toolkit version so that
    main.py requires no changes. All write methods marshal to the Textual
    RichLog via ``call_from_thread`` when called from a background thread.
    """

    def __init__(self):
        self._app: Optional[ChatApp] = None

        # Streaming state
        self._stream_done = threading.Event()
        self._stream_done.set()

        # Thinking state
        self._thinking_lock = threading.Lock()
        self._thinking_buffer: list[str] = []
        self._thinking_token_count: int = 0
        self._thinking_done_flag: bool = False
        self._thinking_visible: bool = False

        # Plaintext log for /cpy
        self._plaintext_log: list[str] = []

        # Callbacks
        self._on_submit: Optional[Callable[[str], None]] = None
        self._on_cancel: Optional[Callable[[], bool]] = None
        self._on_mount_callback: Optional[Callable] = None

    # --- Public callback setters ---

    def set_submit_callback(self, callback: Callable[[str], None]):
        self._on_submit = callback

    def set_cancel_callback(self, callback: Callable[[], bool]):
        self._on_cancel = callback

    def mark_streaming(self):
        self._stream_done.clear()

    def _is_streaming(self) -> bool:
        return not self._stream_done.is_set()

    # --- Core output ---

    def _strip_markup(self, text: str) -> str:
        """Remove Rich markup tags from text."""
        return re.sub(r'\[/?[^\]]+\]', '', text)

    def _write_to_log(self, text: str):
        """Write markup text to the RichLog. Thread-safe."""
        self._plaintext_log.append(self._strip_markup(text))
        if self._app is None:
            return
        try:
            log_widget = self._app.query_one("#output", RichLog)
            if threading.current_thread() is threading.main_thread():
                log_widget.write(text, expand=True)
            else:
                self._app.call_from_thread(log_widget.write, text, expand=True)
        except Exception:
            pass  # app may be shutting down

    def copy_all(self):
        """Copy entire plaintext log to clipboard."""
        text = "\n".join(self._plaintext_log)
        try:
            import subprocess
            process = subprocess.Popen(
                ["clip.exe"] if __import__("sys").platform == "win32" else ["xclip", "-selection", "clipboard"],
                stdin=subprocess.PIPE,
            )
            process.communicate(text.encode("utf-8"))
            self._write_to_log("[dim]✓ Copied all output to clipboard[/dim]")
        except Exception as e:
            self._write_to_log(f"[bold red]Failed to copy:[/bold red] {e}")

    def _write(self, text: str, end: str = "\n"):
        """Compatibility wrapper."""
        combined = text + end
        content = combined.rstrip("\n") if combined != "\n" else ""
        if content or combined == "\n":
            self._write_to_log(content if content else " ")

    # --- High-level print methods ---

    def print_banner(self):
        self._write_to_log(
            "[bold cyan]╔═══════════════════════════════════════════════╗[/bold cyan]\n"
            "[bold cyan]║     Claude Code Python - Sonnet 4.5 MVP      ║[/bold cyan]\n"
            "[bold cyan]║          Extended Thinking Enabled            ║[/bold cyan]\n"
            "[bold cyan]╚═══════════════════════════════════════════════╝[/bold cyan]\n"
            "Type 'exit' or 'quit' to end session"
        )

    def print_separator(self, title: Optional[str] = None):
        if title:
            self._write_to_log(f"── {title} ──")
        else:
            self._write_to_log("────────────────────────────────────")

    def print_error(self, message: str):
        self._write_to_log(f"[bold red]\\[ERROR][/bold red] {message}")

    def print_info(self, message: str):
        self._write_to_log(f"ℹ {message}")

    def print_success(self, message: str):
        self._write_to_log(f"✓ {message}")

    def print_output(self, text: str):
        self._write_to_log(text)

    def clear_screen(self):
        if self._app:
            try:
                log_widget = self._app.query_one("#output", RichLog)
                if threading.current_thread() is threading.main_thread():
                    log_widget.clear()
                else:
                    self._app.call_from_thread(log_widget.clear)
            except Exception:
                pass

    def print_goodbye(self):
        self._write_to_log("\nGoodbye! 👋")

    def get_user_input(self) -> str:
        return ""

    # --- Thinking support ---

    def _estimate_tokens(self, text: str) -> int:
        return len(text) // 4

    def _start_thinking(self):
        with self._thinking_lock:
            self._thinking_buffer = []
            self._thinking_token_count = 0
            self._thinking_done_flag = False
        self._write_to_log("∴ Thinking...")

    def _accumulate_thinking(self, content: str):
        if not content:
            return
        with self._thinking_lock:
            self._thinking_buffer.append(content)
            self._thinking_token_count += self._estimate_tokens(content)
            should_write = self._thinking_visible
        if should_write:
            self._write_to_log(content)

    def _finish_thinking(self):
        with self._thinking_lock:
            if self._thinking_done_flag:
                return
            self._thinking_done_flag = True
            total_tokens = self._thinking_token_count
        if total_tokens > 0:
            seconds = max(1, total_tokens // 50)
            self._write_to_log(f"∴ Thinking complete ({seconds}s, {total_tokens} tokens)")

    def toggle_thinking_visibility(self):
        with self._thinking_lock:
            self._thinking_visible = not self._thinking_visible
            visible = self._thinking_visible
            buffer_copy = list(self._thinking_buffer)
        if visible and buffer_copy:
            self._write_to_log("💭 Thinking process:")
            self._write_to_log("".join(buffer_copy))
        elif not visible:
            self._write_to_log("Thinking hidden")

    # --- Tool display ---

    def print_tool_start(self, tool_name: str):
        self._write_to_log(f"🔧 Using tool: {tool_name}")

    def print_tool_result(self, tool_name: str, result_status: str, output: str):
        icon = "✓" if result_status == "success" else "✗"
        self._write_to_log(f"{icon} Tool result ({result_status}):")
        lines = output.strip().split("\n")
        if len(lines) <= 10:
            for line in lines:
                self._write_to_log(f"  {line}")
        else:
            for line in lines[:5]:
                self._write_to_log(f"  {line}")
            self._write_to_log(f"  ... \\[{len(lines) - 7} more lines] ...")
            for line in lines[-2:]:
                self._write_to_log(f"  {line}")

    # --- Streaming ---

    def stream_response_with_tools(self, events: Iterator[Dict[str, Any]], tool_registry=None,
                                    cancel_event=None, on_complete: Optional[Callable] = None):
        self._stream_done.clear()
        try:
            self._do_stream(events, cancel_event)
            if on_complete:
                on_complete()
        finally:
            self._stream_done.set()

    def _do_stream(self, events: Iterator[Dict[str, Any]], cancel_event=None):
        in_thinking = False
        message_done = False
        text_chunks: list[str] = []
        showed_prefix = False

        for event in events:
            if cancel_event and cancel_event.is_set():
                break
            if message_done:
                continue

            event_type = event["type"]
            content = event.get("content", "")

            if event_type == "thinking_start":
                in_thinking = True
                self._start_thinking()

            elif event_type == "thinking" and in_thinking:
                self._accumulate_thinking(content)

            elif event_type == "text_start":
                if in_thinking:
                    self._finish_thinking()
                    in_thinking = False

            elif event_type == "text":
                text_chunks.append(content)

            elif event_type == "tool_use_detected":
                showed_prefix = self._flush_text(text_chunks, showed_prefix)
                tool_name = event.get("tool_name", "unknown")
                self._write_to_log(f"🔧 Claude wants to use: {tool_name}")

            elif event_type == "tool_execute":
                showed_prefix = self._flush_text(text_chunks, showed_prefix)
                tool_name = event["tool_name"]
                tool_input = event["tool_input"]
                result = event["result"]
                self._write_to_log(f"⚙️  Executing tool: {tool_name}")
                input_str = str(tool_input)
                if len(input_str) < 100:
                    self._write_to_log(f"  Input: {input_str}")
                self.print_tool_result(tool_name, result.status.value, result.output)

            elif event_type == "tool_round_start":
                showed_prefix = self._flush_text(text_chunks, showed_prefix)
                self._write_to_log("Starting tool execution...")

            elif event_type == "tool_round_complete":
                showed_prefix = self._flush_text(text_chunks, showed_prefix)
                self._write_to_log(f"Tool execution complete: {content}")
                message_done = False
                in_thinking = False
                showed_prefix = False
                with self._thinking_lock:
                    self._thinking_done_flag = False

            elif event_type == "message_done":
                message_done = True
                self._flush_text(text_chunks, showed_prefix)
                if in_thinking:
                    self._finish_thinking()
                    in_thinking = False

            elif event_type == "error":
                self._flush_text(text_chunks, showed_prefix)
                self.print_error(content)
                if in_thinking:
                    self._finish_thinking()
                    in_thinking = False
                break

        self._flush_text(text_chunks, showed_prefix)
        if in_thinking:
            self._finish_thinking()

    def _flush_text(self, chunks: list[str], prefix_shown: bool) -> bool:
        """Flush accumulated text chunks to the log.

        Returns True if prefix has been shown (for tracking across flushes).
        """
        if not chunks:
            return prefix_shown
        text = "".join(chunks)
        chunks.clear()
        if not text:
            return prefix_shown
        if not prefix_shown:
            self._write_to_log(f"[bold blue]Claude:[/bold blue] {text}")
            return True
        else:
            self._write_to_log(text)
            return True

    def stream_response(self, events: Iterator[Dict[str, Any]], tool_callback=None):
        self.stream_response_with_tools(events)

    # --- Main entry point ---

    def run(self):
        """Run the Textual TUI app. Blocks until user exits."""
        self._app = ChatApp(self)
        self._app.run()
        self._app = None
