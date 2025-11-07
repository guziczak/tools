#!/usr/bin/env python3
"""Basic test script for Claude Code Python - no tools."""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
from core.api_client import ClaudeAPIClient
from rich.console import Console

load_dotenv()

console = Console()

def test_basic_chat():
    """Test basic chat without tools."""
    console.print("\n[bold cyan]Test 1: Basic Chat (no tools)[/bold cyan]\n")

    # Check for API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        console.print("[red]ERROR:[/red] ANTHROPIC_API_KEY not set in .env")
        console.print("Please create .env and add your API key:")
        console.print("  ANTHROPIC_API_KEY=sk-ant-...")
        return False

    console.print(f"[green]✓[/green] API key found: {api_key[:10]}...")

    try:
        # Create client without tools
        console.print("[cyan]Creating API client...[/cyan]")
        client = ClaudeAPIClient(
            api_key=api_key,
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            thinking_enabled=False,  # Disable thinking for basic test
        )
        console.print("[green]✓[/green] Client created")

        # Test simple chat
        console.print("\n[cyan]Sending test message...[/cyan]")
        test_message = "Say 'Hello from Claude Code Python!' in exactly 5 words."

        console.print(f"[dim]User: {test_message}[/dim]\n")
        console.print("[bold blue]Claude:[/bold blue] ", end="")

        # Stream response
        response_text = ""
        for event in client.chat(test_message):
            if event["type"] == "text":
                text = event["content"]
                console.print(text, end="")
                response_text += text

        console.print("\n")

        if response_text:
            console.print(f"[green]✓[/green] Response received ({len(response_text)} chars)")
            return True
        else:
            console.print("[red]✗[/red] Empty response")
            return False

    except Exception as e:
        console.print(f"\n[red]✗ ERROR:[/red] {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        return False


def test_thinking():
    """Test with extended thinking."""
    console.print("\n[bold cyan]Test 2: Extended Thinking[/bold cyan]\n")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        console.print("[red]Skipping (no API key)[/red]")
        return False

    try:
        client = ClaudeAPIClient(
            api_key=api_key,
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            thinking_enabled=True,
            thinking_budget=5000,
        )

        console.print("[cyan]Sending message with thinking...[/cyan]")
        test_message = "What is 15 * 23? Show your work."

        console.print(f"[dim]User: {test_message}[/dim]\n")

        has_thinking = False
        has_text = False

        for event in client.chat(test_message):
            event_type = event["type"]

            if event_type == "thinking_start":
                console.print("[dim cyan]🧠 Thinking...[/dim cyan]")
                has_thinking = True
            elif event_type == "thinking":
                pass  # Don't print thinking content for brevity
            elif event_type == "text_start":
                console.print("\n[bold blue]Claude:[/bold blue] ", end="")
            elif event_type == "text":
                console.print(event["content"], end="")
                has_text = True

        console.print("\n")

        if has_thinking and has_text:
            console.print(f"[green]✓[/green] Thinking and response received")
            return True
        else:
            console.print(f"[yellow]⚠[/yellow] Missing thinking={has_thinking}, text={has_text}")
            return False

    except Exception as e:
        console.print(f"[red]✗ ERROR:[/red] {e}")
        return False


if __name__ == "__main__":
    console.print("[bold]Claude Code Python - Basic Tests[/bold]")
    console.print("=" * 50)

    results = []

    # Run tests
    results.append(("Basic Chat", test_basic_chat()))
    results.append(("Extended Thinking", test_thinking()))

    # Summary
    console.print("\n" + "=" * 50)
    console.print("[bold]Test Results:[/bold]\n")

    for test_name, passed in results:
        status = "[green]✓ PASS[/green]" if passed else "[red]✗ FAIL[/red]"
        console.print(f"  {status} - {test_name}")

    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)

    console.print(f"\n[bold]Total: {passed_count}/{total_count} passed[/bold]")

    sys.exit(0 if passed_count == total_count else 1)
