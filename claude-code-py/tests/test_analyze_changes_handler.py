"""Test for AnalyzeChangesHandler - commit analysis intent.

This tests the critical "przeanalizuj zmiany" flow that wasn't working before.
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.intent_handlers import AnalyzeChangesHandler, IntentResult


class MockToolRegistry:
    """Mock tool registry for testing."""

    def __init__(self, output="mock diff", success=True):
        self.output = output
        self.success = success

    def execute_tool(self, tool_name, **kwargs):
        """Mock execute_tool."""
        from tools.base import ToolResult, ToolStatus

        if self.success:
            return ToolResult(
                status=ToolStatus.SUCCESS,
                output=self.output,
                error=None
            )
        else:
            return ToolResult(
                status=ToolStatus.ERROR,
                output=None,
                error="Mock error"
            )


class TestAnalyzeChangesHandler:
    """Tests for AnalyzeChangesHandler."""

    def test_can_handle_analyze_changes(self):
        """Should handle analyze_changes intent."""
        handler = AnalyzeChangesHandler()
        assert handler.can_handle("analyze_changes")
        assert not handler.can_handle("git_log")

    def test_extracts_commit_hash_from_messages(self):
        """Should extract commit hash from conversation history."""
        messages = [
            {"role": "user", "content": "widzisz ostatniego commita?"},
            {"role": "assistant", "content": "Tak, ostatni commit to e35c4f4 'update'"}
        ]

        handler = AnalyzeChangesHandler(messages=messages)
        commit_hash = handler._extract_commit_hash()

        assert commit_hash == "e35c4f4"

    def test_extracts_long_commit_hash(self):
        """Should extract full 40-char commit hash."""
        messages = [
            {"role": "assistant", "content": "commit: e35c4f43749b9e3b5bd946064f349b969ea88b3b"}
        ]

        handler = AnalyzeChangesHandler(messages=messages)
        commit_hash = handler._extract_commit_hash()

        assert commit_hash == "e35c4f43749b9e3b5bd946064f349b969ea88b3b"

    def test_no_hash_found(self):
        """Should return None if no commit hash in messages."""
        messages = [
            {"role": "user", "content": "hello world"},
            {"role": "assistant", "content": "how can I help?"}
        ]

        handler = AnalyzeChangesHandler(messages=messages)
        commit_hash = handler._extract_commit_hash()

        assert commit_hash is None

    def test_handle_with_hash_success(self):
        """Should pre-execute git show when hash found."""
        messages = [
            {"role": "assistant", "content": "Last commit: abc123 'test'"}
        ]

        mock_registry = MockToolRegistry(output="diff --git a/file.txt...")
        handler = AnalyzeChangesHandler(tool_registry=mock_registry, messages=messages)

        result = handler.handle("przeanalizuj zmiany", "analyze_changes")

        # Should enrich message with diff
        assert isinstance(result, IntentResult)
        assert "abc123" in result.enriched_message
        assert "diff --git a/file.txt" in result.enriched_message
        assert result.metadata["commit_hash"] == "abc123"

    def test_handle_no_hash_in_context(self):
        """Should fail gracefully if no hash in context."""
        messages = [
            {"role": "user", "content": "random message"}
        ]

        mock_registry = MockToolRegistry()
        handler = AnalyzeChangesHandler(tool_registry=mock_registry, messages=messages)

        result = handler.handle("przeanalizuj zmiany", "analyze_changes")

        # Should return original message with error
        assert isinstance(result, IntentResult)
        assert "No commit hash found" in result.metadata.get("error", "")

    def test_handle_git_show_fails(self):
        """Should handle git show failure gracefully."""
        messages = [
            {"role": "assistant", "content": "commit: abc123"}
        ]

        mock_registry = MockToolRegistry(success=False)
        handler = AnalyzeChangesHandler(tool_registry=mock_registry, messages=messages)

        result = handler.handle("przeanalizuj zmiany", "analyze_changes")

        # Should return error
        assert isinstance(result, IntentResult)
        assert "error" in result.metadata


class TestIntegration:
    """Integration tests with full system."""

    def test_full_flow(self):
        """Test full flow: user asks about commit, then asks to analyze."""
        from core.intent_handlers import IntentRouter

        # Setup
        mock_registry = MockToolRegistry(
            output="commit abc123\nAuthor: Test\n\ndiff --git a/file.txt"
        )
        router = IntentRouter(mock_registry)

        # Simulate conversation
        messages = [
            {"role": "user", "content": "widzisz ostatniego commita?"},
            {"role": "assistant", "content": "Tak, ostatni commit to abc123 'test'"}
        ]

        # User asks to analyze
        result = router.route(
            intent="analyze_changes",
            user_message="przeanalizuj zmiany",
            messages=messages
        )

        # Should execute git show and enrich message
        assert result is not None
        assert "diff --git a/file.txt" in result.enriched_message
        assert result.metadata["commit_hash"] == "abc123"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
