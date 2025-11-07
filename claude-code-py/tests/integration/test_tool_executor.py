"""Integration tests for tool executor."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from anthropic.types import Message, ContentBlock, ToolUseBlock, TextBlock

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.tool_executor import ToolExecutor
from tools import create_default_registry


class TestToolExecutor:
    """Tests for ToolExecutor with mocked Anthropic client."""

    @pytest.fixture
    def executor(self):
        """Create tool executor with registry."""
        registry = create_default_registry()
        mock_client = Mock()
        return ToolExecutor(registry, mock_client)

    def test_has_tool_use_detection(self, executor):
        """Test detecting tool_use in message."""
        # Message with tool use
        tool_block = ToolUseBlock(
            id="tool_123",
            type="tool_use",
            name="read_file",
            input={"file_path": "/test.txt"}
        )

        message_with_tool = Message(
            id="msg_123",
            type="message",
            role="assistant",
            content=[tool_block],
            model="claude-3",
            stop_reason="tool_use",
            usage={"input_tokens": 10, "output_tokens": 20}
        )

        assert executor.has_tool_use(message_with_tool) is True

        # Message without tool use
        text_block = TextBlock(type="text", text="Hello")
        message_no_tool = Message(
            id="msg_124",
            type="message",
            role="assistant",
            content=[text_block],
            model="claude-3",
            stop_reason="end_turn",
            usage={"input_tokens": 10, "output_tokens": 20}
        )

        assert executor.has_tool_use(message_no_tool) is False

    def test_execute_tools_from_message(self, executor, temp_dir):
        """Test executing tools from message."""
        # Create a test file
        test_file = temp_dir / "test.txt"
        test_file.write_text("test content")

        # Create message with read_file tool use
        tool_block = ToolUseBlock(
            id="tool_456",
            type="tool_use",
            name="read_file",
            input={"file_path": str(test_file)}
        )

        message = Message(
            id="msg_125",
            type="message",
            role="assistant",
            content=[tool_block],
            model="claude-3",
            stop_reason="tool_use",
            usage={"input_tokens": 10, "output_tokens": 20}
        )

        results = executor.execute_tools_from_message(message)

        assert len(results) == 1
        assert results[0]["tool_name"] == "read_file"
        assert results[0]["tool_id"] == "tool_456"
        assert results[0]["result"].status.value == "success"
        assert "test content" in results[0]["result"].output

    def test_execute_multiple_tools(self, executor, temp_dir):
        """Test executing multiple tools in one message."""
        # Create test files
        file1 = temp_dir / "file1.txt"
        file2 = temp_dir / "file2.txt"
        file1.write_text("content 1")
        file2.write_text("content 2")

        # Message with two tool uses
        tool1 = ToolUseBlock(
            id="tool_1",
            type="tool_use",
            name="read_file",
            input={"file_path": str(file1)}
        )
        tool2 = ToolUseBlock(
            id="tool_2",
            type="tool_use",
            name="read_file",
            input={"file_path": str(file2)}
        )

        message = Message(
            id="msg_126",
            type="message",
            role="assistant",
            content=[tool1, tool2],
            model="claude-3",
            stop_reason="tool_use",
            usage={"input_tokens": 10, "output_tokens": 20}
        )

        results = executor.execute_tools_from_message(message)

        assert len(results) == 2
        assert all(r["result"].status.value == "success" for r in results)

    def test_tool_execution_error(self, executor):
        """Test handling tool execution errors."""
        # Try to read nonexistent file
        tool_block = ToolUseBlock(
            id="tool_789",
            type="tool_use",
            name="read_file",
            input={"file_path": "/nonexistent/file.txt"}
        )

        message = Message(
            id="msg_127",
            type="message",
            role="assistant",
            content=[tool_block],
            model="claude-3",
            stop_reason="tool_use",
            usage={"input_tokens": 10, "output_tokens": 20}
        )

        results = executor.execute_tools_from_message(message)

        assert len(results) == 1
        assert results[0]["result"].status.value == "error"
        assert "not found" in results[0]["result"].error.lower()

    def test_unknown_tool(self, executor):
        """Test handling unknown tool."""
        tool_block = ToolUseBlock(
            id="tool_999",
            type="tool_use",
            name="unknown_tool",
            input={}
        )

        message = Message(
            id="msg_128",
            type="message",
            role="assistant",
            content=[tool_block],
            model="claude-3",
            stop_reason="tool_use",
            usage={"input_tokens": 10, "output_tokens": 20}
        )

        results = executor.execute_tools_from_message(message)

        assert len(results) == 1
        assert results[0]["result"].status.value == "error"
        assert "not found" in results[0]["result"].error.lower()
