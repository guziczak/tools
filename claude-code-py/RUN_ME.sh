#!/bin/bash
# Quick launcher script for Claude Code Python

echo "🚀 Claude Code Python Launcher"
echo "=============================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found!"
    echo ""
    echo "Creating .env from example..."
    cp .env.example .env
    
    echo ""
    echo "📝 Please edit .env and add your ANTHROPIC_API_KEY:"
    echo "   nano .env"
    echo ""
    echo "Get your API key from: https://console.anthropic.com/"
    echo ""
    read -p "Press Enter when ready..."
fi

# Check if API key is set
if ! grep -q "ANTHROPIC_API_KEY=sk-ant-" .env 2>/dev/null; then
    echo ""
    echo "⚠️  API key not configured in .env"
    echo ""
    echo "Please add your Anthropic API key to .env:"
    echo "   ANTHROPIC_API_KEY=sk-ant-your-key-here"
    echo ""
    echo "Get it from: https://console.anthropic.com/"
    exit 1
fi

echo "✓ Configuration found"
echo ""
echo "Starting Claude Code Python..."
echo ""

# Run the app
python3 claude.py
