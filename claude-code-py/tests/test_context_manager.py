"""Tests for ContextManager (safe memory system).

This tests the key feature that prevents dezinformacja:
- Automatic verification of cached data
- TTL expiration
- Stale data detection
"""

import pytest
from pathlib import Path
import sys
from datetime import datetime, timedelta
import time

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.memory import ContextManager, ContextEntry


class MockToolRegistry:
    """Mock tool registry for testing verification."""

    def __init__(self, output="abc123", success=True):
        self.output = output
        self.success = success
        self.calls = []

    def execute_tool(self, tool_name, **kwargs):
        """Mock execute_tool."""
        from tools.base import ToolResult, ToolStatus

        self.calls.append((tool_name, kwargs))

        if self.success:
            return ToolResult(status=ToolStatus.SUCCESS, output=self.output, error=None)
        else:
            return ToolResult(status=ToolStatus.ERROR, output=None, error="Mock error")


class TestContextManager:
    """Tests for ContextManager."""

    def test_store_and_get(self):
        """Should store and retrieve values."""
        ctx = ContextManager()

        ctx.store("key1", "value1", ttl_seconds=300)
        value = ctx.get("key1")

        assert value == "value1"

    def test_ttl_expiration(self):
        """Should expire after TTL."""
        ctx = ContextManager()

        # Store with 0 second TTL
        ctx.store("key1", "value1", ttl_seconds=0)

        # Wait a tiny bit
        time.sleep(0.01)

        # Should be expired
        value = ctx.get("key1")
        assert value is None

    def test_get_expired_with_flag(self):
        """Should allow retrieving expired if explicitly requested."""
        ctx = ContextManager()

        ctx.store("key1", "value1", ttl_seconds=0)
        time.sleep(0.01)

        # Without flag - expired
        assert ctx.get("key1") is None

        # With flag - returns even if expired
        assert ctx.get("key1", allow_expired=True) == "value1"

    def test_get_nonexistent(self):
        """Should return None for nonexistent keys."""
        ctx = ContextManager()

        value = ctx.get("nonexistent")
        assert value is None

    def test_clear_specific_key(self):
        """Should clear specific key."""
        ctx = ContextManager()

        ctx.store("key1", "value1")
        ctx.store("key2", "value2")

        ctx.clear("key1")

        assert ctx.get("key1") is None
        assert ctx.get("key2") == "value2"

    def test_clear_all(self):
        """Should clear all keys."""
        ctx = ContextManager()

        ctx.store("key1", "value1")
        ctx.store("key2", "value2")

        ctx.clear()

        assert ctx.get("key1") is None
        assert ctx.get("key2") is None


class TestVerification:
    """Tests for automatic freshness verification."""

    def test_get_verified_fresh_data(self):
        """Should return fresh data when verification passes."""
        # Mock registry returns same value as cached
        mock_registry = MockToolRegistry(output="abc123")
        ctx = ContextManager(tool_registry=mock_registry)

        # Store with verification command
        ctx.store(
            "last_commit", "abc123", ttl_seconds=300, verification_cmd="git log -1 --format=%H"
        )

        # Get with verification
        result = ctx.get_verified("last_commit")

        # Should be fresh
        assert result["status"] == "fresh"
        assert result["value"] == "abc123"
        assert result["verified"] is True

        # Verify command was executed
        assert len(mock_registry.calls) == 1
        assert mock_registry.calls[0][1]["command"] == "git log -1 --format=%H"

    def test_get_verified_stale_data(self):
        """Should detect stale data and return live value."""
        # Mock registry returns DIFFERENT value than cached
        mock_registry = MockToolRegistry(output="xyz789")  # Different!
        ctx = ContextManager(tool_registry=mock_registry)

        # Store old value
        ctx.store(
            "last_commit",
            "abc123",  # Old value
            ttl_seconds=300,
            verification_cmd="git log -1 --format=%H",
        )

        # Get with verification
        result = ctx.get_verified("last_commit")

        # Should detect stale + return live value
        assert result["status"] == "stale"
        assert result["value"] == "xyz789"  # Live value!
        assert result["cached_value"] == "abc123"  # Old value
        assert result["live_value"] == "xyz789"
        assert result["verified"] is True

    def test_get_verified_expired(self):
        """Should not verify if TTL expired."""
        mock_registry = MockToolRegistry(output="abc123")
        ctx = ContextManager(tool_registry=mock_registry)

        # Store with 0 TTL
        ctx.store("last_commit", "abc123", ttl_seconds=0, verification_cmd="git log -1 --format=%H")

        time.sleep(0.01)

        # Get with verification
        result = ctx.get_verified("last_commit")

        # Should be expired (not even verified)
        assert result["status"] == "expired"
        assert result["value"] is None
        assert result["verified"] is False

        # Verification command should NOT be executed (TTL check happens first)
        assert len(mock_registry.calls) == 0

    def test_get_verified_no_verification_cmd(self):
        """Should warn when no verification command configured."""
        ctx = ContextManager()

        # Store WITHOUT verification command
        ctx.store("key1", "value1", ttl_seconds=300)

        # Get with verification
        result = ctx.get_verified("key1")

        # Should return value but with warning
        assert result["status"] == "unverified"
        assert result["value"] == "value1"
        assert result["verified"] is False

    def test_get_verified_no_tool_registry(self):
        """Should warn when no tool registry available."""
        ctx = ContextManager(tool_registry=None)

        ctx.store("key1", "value1", ttl_seconds=300, verification_cmd="git log")

        result = ctx.get_verified("key1")

        # Should return value but unverified
        assert result["status"] == "unverified"
        assert result["value"] == "value1"
        assert result["verified"] is False

    def test_verification_command_fails(self):
        """Should handle verification command failure."""
        mock_registry = MockToolRegistry(success=False)
        ctx = ContextManager(tool_registry=mock_registry)

        ctx.store("key1", "value1", ttl_seconds=300, verification_cmd="git log")

        result = ctx.get_verified("key1")

        # Should report verification failed
        assert result["status"] == "verification_failed"
        assert result["value"] is None
        assert result["verified"] is False


class TestRealWorldScenario:
    """Integration tests for real scenarios."""

    def test_prevent_stale_commit_info(self):
        """Test: Prevents showing stale commit (main dezinformacja problem)."""
        # Simulate: User asks "ostatni commit?" twice with different results

        # Round 1: Commit is abc123
        mock_registry = MockToolRegistry(output="abc123")
        ctx = ContextManager(tool_registry=mock_registry)

        ctx.store(
            "last_commit", "abc123", ttl_seconds=300, verification_cmd="git log -1 --format=%H"
        )

        result1 = ctx.get_verified("last_commit")
        assert result1["status"] == "fresh"
        assert result1["value"] == "abc123"

        # Round 2: Commit changed to xyz789 (user made new commit)
        mock_registry.output = "xyz789"

        result2 = ctx.get_verified("last_commit")

        # Should detect change and return NEW value
        assert result2["status"] == "stale"
        assert result2["value"] == "xyz789"  # NEW value
        assert result2["cached_value"] == "abc123"  # OLD value
        assert "Data changed" in result2["message"]

    def test_ttl_prevents_long_term_staleness(self):
        """Test: TTL prevents using very old data."""
        ctx = ContextManager()

        # Store with 1 second TTL
        ctx.store("data", "old_value", ttl_seconds=1)

        # Immediately available
        assert ctx.get("data") == "old_value"

        # Wait for expiration
        time.sleep(1.1)

        # Now expired
        assert ctx.get("data") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
