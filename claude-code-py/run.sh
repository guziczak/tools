#!/bin/bash
# Claude Code Python - Auto-venv launcher
# This script automatically uses the virtual environment

# Get the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Activate venv and run claude.py
"$DIR/venv/bin/python" "$DIR/claude.py" "$@"
