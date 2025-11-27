#!/usr/bin/env python3
"""Test script for new enhancements.

Run this to verify that all new systems are working correctly.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_command_registry():
    """Test command registry system."""
    print("\n🧪 Testing Command Registry System...")

    from commands import command_registry, CommandDef, CommandArg, ArgType

    # Define test command
    async def test_handler(args):
        return f"Hello {args.get('name', 'World')}!"

    command = CommandDef(
        name="greet",
        description="Greet someone",
        handler=test_handler,
        args=[
            CommandArg(
                name="name",
                description="Name to greet",
                type=ArgType.STRING,
                position=0,
                required=False,
                default="World"
            )
        ],
        examples=["greet", "greet Alice"]
    )

    # Register
    command_registry.register(command)

    # Get back
    retrieved = command_registry.get("greet")
    assert retrieved is not None, "Failed to retrieve command"
    assert retrieved.name == "greet", "Command name mismatch"

    print("✅ Command Registry: OK")


def test_prompt_templates():
    """Test prompt templates system."""
    print("\n🧪 Testing Prompt Templates...")

    from prompts import use_template, TEMPLATES, format_prompt

    # Test template exists
    assert "explain_code" in TEMPLATES, "Template not found"

    # Test template usage
    prompt, system = use_template("explain_code", code="print('hello')", language="python")

    assert "print('hello')" in prompt, "Code not in prompt"
    assert system is not None, "System prompt missing"

    # Test format_prompt
    result = format_prompt("Hello {name}!", {"name": "World"})
    assert result == "Hello World!", "Prompt formatting failed"

    print("✅ Prompt Templates: OK")


def test_file_operations():
    """Test file operations manager."""
    print("\n🧪 Testing FileOperationsManager...")

    from fileops import FileOperationsManager
    import tempfile
    import os

    # Create temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        file_ops = FileOperationsManager(workspace_path=tmpdir)
        file_ops.initialize()

        # Test write
        result = file_ops.write_file("test.txt", "Hello World!")
        assert result.success, f"Write failed: {result.error}"

        # Test read
        result = file_ops.read_file("test.txt")
        assert result.success, f"Read failed: {result.error}"
        assert result.content == "Hello World!", "Content mismatch"

        # Test security - path traversal
        result = file_ops.read_file("../../etc/passwd")
        assert not result.success, "Path traversal should be blocked!"

        # Test file exists
        exists = file_ops.file_exists("test.txt")
        assert exists, "File should exist"

        # Test directory listing
        result = file_ops.list_directory(".")
        assert result.success, f"List failed: {result.error}"
        assert "test.txt" in result.files, "File not in listing"

    print("✅ FileOperationsManager: OK")


def test_error_handling():
    """Test error handling system."""
    print("\n🧪 Testing Error Handling...")

    from errors import (
        create_user_error,
        ErrorCategory,
        format_error_for_display,
        UserError
    )

    # Create error
    error = create_user_error(
        "Test error message",
        category=ErrorCategory.VALIDATION,
        resolution="Fix the test"
    )

    assert isinstance(error, UserError), "Wrong error type"
    assert error.message == "Test error message", "Message mismatch"
    assert error.category == ErrorCategory.VALIDATION, "Category mismatch"

    # Format error
    formatted = format_error_for_display(error)
    assert "Test error message" in formatted, "Message not in formatted output"
    assert "Fix the test" in formatted, "Resolution not in formatted output"

    print("✅ Error Handling: OK")


def test_cli_mode_structure():
    """Test CLI mode structure."""
    print("\n🧪 Testing CLI Mode Structure...")

    try:
        # Just verify the module can be imported
        from cli_mode import CLIMode

        cli = CLIMode()
        assert cli is not None, "Failed to create CLIMode instance"

        # Verify methods exist
        assert hasattr(cli, 'cmd_ask'), "cmd_ask missing"
        assert hasattr(cli, 'cmd_explain'), "cmd_explain missing"
        assert hasattr(cli, 'cmd_refactor'), "cmd_refactor missing"
        assert hasattr(cli, 'cmd_fix'), "cmd_fix missing"
        assert hasattr(cli, 'cmd_review'), "cmd_review missing"
        assert hasattr(cli, 'cmd_generate'), "cmd_generate missing"
        assert hasattr(cli, 'cmd_help'), "cmd_help missing"

        print("✅ CLI Mode Structure: OK")
    except ImportError as e:
        print(f"⚠️  CLI Mode Structure: SKIPPED (missing dependencies: {e})")
        print("    Run: pip install -r requirements.txt")


def main():
    """Run all tests."""
    print("=" * 60)
    print("🧪 Testing Claude Code Python Enhancements")
    print("=" * 60)

    try:
        test_command_registry()
        test_prompt_templates()
        test_file_operations()
        test_error_handling()
        test_cli_mode_structure()

        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        print("\n🎉 Enhancements are working correctly!")
        print("\nNext steps:")
        print("  1. Try CLI mode: python claude.py help")
        print("  2. Try REPL mode: python claude.py")
        print("  3. Read ENHANCEMENTS.md for documentation")

        return 0

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
