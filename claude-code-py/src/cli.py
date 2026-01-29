"""CLI entry point for Claude Code Python.

Thin wrapper: parse args, create Application, run.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))


def main() -> None:
    """Entry point."""
    if len(sys.argv) > 1:
        from cli_mode import run_cli_mode

        command = sys.argv[1]
        args = sys.argv[2:]
        sys.exit(run_cli_mode(command, args))
    else:
        # Interactive REPL - delegate to existing main.py
        from main import ClaudeCodePy

        app = ClaudeCodePy()
        app.run()


if __name__ == "__main__":
    main()
