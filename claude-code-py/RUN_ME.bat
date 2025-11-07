@echo off
REM Quick launcher for Claude Code Python (Windows)

echo.
echo ========================================
echo   Claude Code Python Launcher
echo ========================================
echo.

REM Check if .env exists
if not exist .env (
    echo [WARNING] No .env file found!
    echo.
    echo Creating .env from example...
    copy .env.example .env >nul

    echo.
    echo Please edit .env and add your ANTHROPIC_API_KEY:
    echo    notepad .env
    echo.
    echo Get your API key from: https://console.anthropic.com/
    echo.
    pause
    notepad .env
)

REM Check if API key is configured
findstr /C:"ANTHROPIC_API_KEY=sk-ant-" .env >nul 2>&1
if errorlevel 1 (
    echo.
    echo [WARNING] API key not configured in .env
    echo.
    echo Please add your Anthropic API key to .env:
    echo    ANTHROPIC_API_KEY=sk-ant-your-key-here
    echo.
    echo Get it from: https://console.anthropic.com/
    echo.
    pause
    notepad .env
    exit /b 1
)

echo [OK] Configuration found
echo.
echo Starting Claude Code Python...
echo.

REM Run the app
python claude.py

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to start!
    echo.
    echo Make sure you have Python installed and dependencies:
    echo    pip install -r requirements.txt
    echo.
    pause
)
