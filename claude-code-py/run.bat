@echo off
REM Claude Code Python - Auto-venv launcher (Windows)
REM This script automatically uses the virtual environment

REM Get the directory where this script is located
set DIR=%~dp0

REM Run claude.py with venv Python
"%DIR%venv\Scripts\python.exe" "%DIR%claude.py" %*
