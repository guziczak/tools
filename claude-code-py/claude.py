#!/usr/bin/env python3
"""
Claude Code Python - Main Entry Point

Simple launcher for Claude Code Python.

Usage:
    python claude.py
    python claude.py --debug
    python claude.py --help
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import and run main
from main import main

if __name__ == "__main__":
    main()
