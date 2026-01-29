"""Tests for the unified tool execution loop."""

import pytest
from unittest.mock import Mock, MagicMock
from core.pipeline.tool_loop import prepare_tool_input, execute_tool_blocks, run_tool_loop
from tools.base import ToolResult, ToolStatus


class TestPrepareToolInput:
    def test_non_bash_passthrough(self):
        inp = {"file_path": "/tmp/x"}
        fixed, err, warnings = prepare_tool_input("read_file", inp)
        assert fixed is inp
        assert err is None
        assert warnings == []

    def test_bash_cwd_rewrite(self):
        inp = {"command": "ls", "cwd": "/home/claude/src"}
        fixed, err, warnings = prepare_tool_input("bash", inp)
        assert "/home/claude" not in fixed["cwd"]
        assert len(warnings) == 1

    def test_bash_command_validation(self):
        validator = Mock()
        result = Mock()
        result.is_valid = False
        result.error_message = "blocked"
        result.warnings = []
        validator.validate.return_value = result

        inp = {"command": "rm -rf /"}
        fixed, err, warnings = prepare_tool_input("bash", inp, command_validator=validator)
        assert err == "blocked"


class TestExecuteToolBlocks:
    def test_success(self):
        registry = Mock()
        registry.execute_tool.return_value = ToolResult(
            status=ToolStatus.SUCCESS, output="hello", error=None
        )
        blocks = [{"name": "bash", "id": "t1", "input": {"command": "echo hi"}}]
        results, uses, records, all_failed = execute_tool_blocks(blocks, registry)
        assert len(results) == 1
        assert results[0]["content"] == "hello"
        assert not all_failed

    def test_all_failed(self):
        registry = Mock()
        registry.execute_tool.return_value = ToolResult(
            status=ToolStatus.ERROR, output="", error="fail"
        )
        blocks = [{"name": "bash", "id": "t1", "input": {"command": "bad"}}]
        results, uses, records, all_failed = execute_tool_blocks(blocks, registry)
        assert all_failed


class TestRunToolLoop:
    def test_no_tools_exits_immediately(self):
        """When stream yields no tool blocks, loop exits after one round."""
        def stream_fn(round_num):
            yield {"type": "text", "content": "Hello!"}
            yield {"type": "message_done", "content": ""}

        messages = []
        events = list(run_tool_loop(
            stream_fn=stream_fn,
            messages=messages,
            tool_registry=Mock(),
            add_message=lambda r, c: None,
        ))
        text_events = [e for e in events if e["type"] == "text"]
        assert len(text_events) == 1
        assert text_events[0]["content"] == "Hello!"
