"""Terminal UI for Claude chat.

Uses prompt_toolkit PromptSession with patch_stdout(raw=True) so that
streaming output appears above the prompt while the user can type freely.
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


class WriteBatcher:
    """Batches small writes and flushes them periodically.

    Reduces prompt_toolkit redraws from hundreds/s to ~25/s by coalescing
    tiny SSE chunks into larger batches flushed every ``interval`` seconds.
    """

    def __init__(self, interval: float = 0.04):
        self._buf: list[str] = []
        self._lock = threading.Lock()
        self._interval = interval
        self._timer: Optional[threading.Timer] = None

    def write(self, text: str):
        with self._lock:
            self._buf.append(text)
            if self._timer is None:
                self._timer = threading.Timer(self._interval, self._flush)
                self._timer.daemon = True
                self._timer.start()

    def _flush(self):
        with self._lock:
            data = "".join(self._buf)
            self._buf.clear()
            self._timer = None
        if data:
            sys.stdout.write(data)
            sys.stdout.flush()

    def flush_now(self):
        """Force-flush remaining buffer. Call on stream end."""
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
            data = "".join(self._buf)
            self._buf.clear()
        if data:
            sys.stdout.write(data)
            sys.stdout.flush()


class TerminalUI:
    """Terminal UI: prompt_toolkit input + patch_stdout streaming.

    Threading model:
        - Main thread: run() loop — prompt is always visible
        - Stream thread: writes go through WriteBatcher → stdout
        - patch_stdout(raw=True) renders output above the prompt
        - _stream_done Event gates whether submit is accepted
    """

    def __init__(self):
        self._session: Optional[PromptSession] = None
        self._batcher = WriteBatcher()

        # Streaming state — _stream_done is set when no stream is active
        self._stream_done = threading.Event()
        self._stream_done.set()

        # Thinking state
        self._thinking_lock = threading.Lock()
        self._thinking_buffer: list[str] = []
        self._thinking_token_count: int = 0
        self._thinking_done_flag: bool = False
        self._thinking_visible: bool = False

        # Callbacks — set via public methods
        self._on_submit: Optional[Callable[[str], None]] = None
        self._on_cancel: Optional[Callable[[], bool]] = None

        # Double Ctrl+C exit
        self._ctrl_c_time: float = 0.0

    # --- Public callback setters ---

    def set_submit_callback(self, callback: Callable[[str], None]):
        self._on_submit = callback

    def set_cancel_callback(self, callback: Callable[[], bool]):
        self._on_cancel = callback

    def mark_streaming(self):
        """Mark that streaming is about to start."""
        self._stream_done.clear()

    def _is_streaming(self) -> bool:
        return not self._stream_done.is_set()

    # --- Core output ---

    def _write(self, text: str, end: str = "\n"):
        """Write to stdout. patch_stdout proxy handles rendering above prompt."""
        sys.stdout.write(text + end)
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

    def clear_screen(self):
        self._write("\033[2J\033[H", end="")

    def print_goodbye(self):
        self._write("\nGoodbye! 👋")

    def get_user_input(self) -> str:
        """Legacy fallback."""
        return ""

    # --- Thinking support ---

    def _estimate_tokens(self, text: str) -> int:
        return len(text) // 4

    def _start_thinking(self):
        """Reset thinking state and print start marker."""
        with self._thinking_lock:
            self._thinking_buffer = []
            self._thinking_token_count = 0
            self._thinking_done_flag = False
        self._write("∴ Thinking...")

    def _accumulate_thinking(self, content: str):
        """Accumulate thinking content (no live output unless visible)."""
        if not content:
            return
        with self._thinking_lock:
            self._thinking_buffer.append(content)
            self._thinking_token_count += self._estimate_tokens(content)
            if self._thinking_visible:
                self._batcher.write(content)

    def _finish_thinking(self):
        """Print thinking summary. Idempotent."""
        with self._thinking_lock:
            if self._thinking_done_flag:
                return
            self._thinking_done_flag = True
            total_tokens = self._thinking_token_count
        if total_tokens > 0:
            seconds = max(1, total_tokens // 50)
            self._write(f"∴ Thinking complete ({seconds}s, {total_tokens} tokens)")

    def toggle_thinking_visibility(self):
        with self._thinking_lock:
            self._thinking_visible = not self._thinking_visible
            visible = self._thinking_visible
            buffer_copy = list(self._thinking_buffer)
        if visible and buffer_copy:
            self._write("\n💭 Thinking process:\n")
            self._write("".join(buffer_copy))
        elif not visible:
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

    def stream_response_with_tools(self, events: Iterator[Dict[str, Any]], tool_registry=None,
                                    cancel_event=None, on_complete: Optional[Callable] = None):
        """Stream Claude's response to stdout via WriteBatcher.

        on_complete runs after streaming but before _stream_done is set.
        """
        self._stream_done.clear()  # idempotent if mark_streaming() already called
        try:
            self._do_stream(events, cancel_event)
            if on_complete:
                on_complete()
        finally:
            self._batcher.flush_now()
            self._stream_done.set()

    def _do_stream(self, events: Iterator[Dict[str, Any]], cancel_event=None):
        """Internal streaming logic, separated for clean finally in caller."""
        in_thinking = False
        message_done = False
        text_started = False

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
                if not text_started:
                    self._write("\nClaude: ", end="")
                    text_started = True

            elif event_type == "text":
                if not text_started:
                    self._write("\nClaude: ", end="")
                    text_started = True
                self._batcher.write(content)

            elif event_type == "tool_use_detected":
                tool_name = event.get("tool_name", "unknown")
                self._write(f"\n🔧 Claude wants to use: {tool_name}")

            elif event_type == "tool_execute":
                tool_name = event["tool_name"]
                tool_input = event["tool_input"]
                result = event["result"]
                self._write(f"\n⚙️  Executing tool: {tool_name}")
                input_str = str(tool_input)
                if len(input_str) < 100:
                    self._write(f"  Input: {input_str}")
                self.print_tool_result(tool_name, result.status.value, result.output)

            elif event_type == "tool_round_start":
                self._write("\nStarting tool execution...")

            elif event_type == "tool_round_complete":
                self._batcher.flush_now()
                self._write(f"Tool execution complete: {content}")
                message_done = False
                in_thinking = False
                text_started = False
                with self._thinking_lock:
                    self._thinking_done_flag = False

            elif event_type == "message_done":
                message_done = True
                self._batcher.flush_now()
                if in_thinking:
                    self._finish_thinking()
                    in_thinking = False
                self._write("")  # final newline

            elif event_type == "error":
                self._batcher.flush_now()
                self.print_error(content)
                if in_thinking:
                    self._finish_thinking()
                    in_thinking = False
                break

        if in_thinking:
            self._finish_thinking()

    def stream_response(self, events: Iterator[Dict[str, Any]], tool_callback=None):
        self.stream_response_with_tools(events)

    # --- Main input loop ---

    def run(self):
        """Run the input loop.

        patch_stdout(raw=True) renders streaming output above the prompt.
        The user can type at any time; submit is rejected while streaming.
        Ctrl+C during streaming cancels it. Double Ctrl+C at prompt exits.
        """
        self._session = PromptSession()

        with patch_stdout(raw=True):
            while True:
                try:
                    user_input = self._session.prompt(
                        HTML("<ansigreen><b>You</b></ansigreen>: "),
                    )
                    user_input = user_input.strip() if user_input else ""
                except KeyboardInterrupt:
                    if self._is_streaming():
                        if self._on_cancel:
                            self._on_cancel()
                        continue
                    now = time.monotonic()
                    if now - self._ctrl_c_time < 3.0:
                        self.print_goodbye()
                        break
                    self._ctrl_c_time = now
                    self._write("\nPress Ctrl+C again to exit (or type 'exit')")
                    continue
                except EOFError:
                    self.print_goodbye()
                    break

                if not user_input:
                    continue

                if user_input.lower() in ("exit", "quit", "q"):
                    self.print_goodbye()
                    break

                if self._is_streaming():
                    self._write("⏳ Please wait for the current response to finish.")
                    continue

                if self._on_submit:
                    self._on_submit(user_input)
