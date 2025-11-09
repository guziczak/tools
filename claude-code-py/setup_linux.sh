#!/bin/bash
# Claude Code Python - Linux/Mac Setup

echo "========================================"
echo "Claude Code Python - Linux/Mac Setup"
echo "========================================"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found!"
    echo "Please install Python 3.8+ from your package manager"
    exit 1
fi

echo "[1/3] Checking Python version..."
python3 --version

echo ""
echo "[2/3] Creating virtual environment..."
if [ -d "venv" ]; then
    echo "Virtual environment already exists, recreating..."
    rm -rf venv
fi
python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to create virtual environment!"
    echo "On Ubuntu/Debian, try: sudo apt install python3-venv"
    exit 1
fi

echo ""
echo "[3/3] Installing dependencies..."
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install dependencies!"
    exit 1
fi

echo ""
echo "========================================"
echo "Setup complete!"
echo "========================================"
echo ""
echo "To run Claude Code Python:"
echo "  ./run.sh"
echo ""
echo "Or manually:"
echo "  ./venv/bin/python claude.py"
echo ""
