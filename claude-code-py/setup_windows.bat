@echo off
echo ========================================
echo Claude Code Python - Windows Setup
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Please install Python 3.8+ from https://www.python.org/
    pause
    exit /b 1
)

echo [1/3] Checking Python version...
python --version

echo.
echo [2/3] Creating virtual environment...
if exist venv (
    echo Virtual environment already exists, recreating...
    rmdir /s /q venv
)
python -m venv venv
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment!
    echo Make sure you have python3-venv installed
    pause
    exit /b 1
)

echo.
echo [3/3] Installing dependencies...
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\pip.exe install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Setup complete!
echo ========================================
echo.
echo To run Claude Code Python:
echo   run.bat
echo.
echo Or manually:
echo   venv\Scripts\python.exe claude.py
echo.
pause
