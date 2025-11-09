"""Unit tests for security validator.

These tests are CRITICAL - they ensure dangerous commands are blocked.
Never skip security tests!

Test Coverage:
- Whitelist policy (positive and negative cases)
- Blacklist policy (various dangerous patterns)
- Edge cases (bypass attempts, encoding tricks)
- Integration tests (full validator chain)
"""

import pytest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.security import (
    CommandSecurityValidator,
    WhitelistPolicy,
    BlacklistPolicy,
    LengthPolicy,
    PatternPolicy,
    ValidationResult,
)


class TestWhitelistPolicy:
    """Tests for whitelist-based validation."""

    def test_allows_whitelisted_command(self):
        """Should allow commands in whitelist."""
        policy = WhitelistPolicy(["git log", "ls"])
        result = policy.validate("git log --oneline")

        assert result.is_safe is True
        assert "whitelist" in result.reason.lower()

    def test_blocks_non_whitelisted_command(self):
        """Should block commands not in whitelist."""
        policy = WhitelistPolicy(["git log", "ls"])
        result = policy.validate("rm -rf /")

        assert result.is_safe is False
        assert "whitelist" in result.reason.lower()

    def test_case_insensitive(self):
        """Should be case insensitive."""
        policy = WhitelistPolicy(["git log"])
        result = policy.validate("GIT LOG --oneline")

        assert result.is_safe is True

    def test_prefix_matching(self):
        """Should match command prefixes."""
        policy = WhitelistPolicy(["git log"])

        # Should match (prefix)
        assert policy.validate("git log --oneline").is_safe
        assert policy.validate("git log -n 10").is_safe

        # Should not match (different command)
        assert not policy.validate("git push").is_safe


class TestBlacklistPolicy:
    """Tests for blacklist-based validation."""

    def test_blocks_dangerous_rm(self):
        """Should block rm commands."""
        policy = BlacklistPolicy(["rm ", "rm-"])

        assert not policy.validate("rm -rf /").is_safe
        assert not policy.validate("rm file.txt").is_safe
        assert not policy.validate("sudo rm -rf /").is_safe

    def test_blocks_sudo(self):
        """Should block sudo commands."""
        policy = BlacklistPolicy(["sudo "])

        assert not policy.validate("sudo apt install").is_safe
        assert not policy.validate("sudo rm -rf /").is_safe

    def test_blocks_git_push(self):
        """Should block git push (state-modifying)."""
        policy = BlacklistPolicy(["git push", "git commit"])

        assert not policy.validate("git push origin main").is_safe
        assert not policy.validate("git commit -m 'test'").is_safe

    def test_allows_safe_commands(self):
        """Should allow safe commands not in blacklist."""
        policy = BlacklistPolicy(["rm ", "sudo "])

        assert policy.validate("ls -la").is_safe
        assert policy.validate("git log").is_safe
        assert policy.validate("cat file.txt").is_safe

    def test_blocks_file_redirection(self):
        """Should block file redirection (overwrite risk)."""
        policy = BlacklistPolicy(["> ", ">> "])

        assert not policy.validate("echo 'data' > file.txt").is_safe
        assert not policy.validate("cat data >> file.txt").is_safe

    def test_detects_pattern_in_middle(self):
        """Should detect dangerous patterns anywhere in command."""
        policy = BlacklistPolicy(["rm "])

        # Pattern at start
        assert not policy.validate("rm file.txt").is_safe

        # Pattern in middle (with space before)
        assert not policy.validate("cd /tmp && rm file.txt").is_safe


class TestLengthPolicy:
    """Tests for command length validation."""

    def test_allows_short_commands(self):
        """Should allow commands under max length."""
        policy = LengthPolicy(max_length=100)

        assert policy.validate("ls -la").is_safe
        assert policy.validate("git log --oneline").is_safe

    def test_blocks_long_commands(self):
        """Should block commands over max length."""
        policy = LengthPolicy(max_length=50)

        long_cmd = "echo " + "x" * 100
        result = policy.validate(long_cmd)

        assert not result.is_safe
        assert "too long" in result.reason.lower()


class TestPatternPolicy:
    """Tests for suspicious pattern detection."""

    def test_blocks_eval(self):
        """Should block commands with eval."""
        policy = PatternPolicy(["eval", "exec"])

        assert not policy.validate("python -c 'eval(input())'").is_safe
        assert not policy.validate("bash -c 'eval $cmd'").is_safe

    def test_blocks_os_system(self):
        """Should block os.system calls."""
        policy = PatternPolicy(["os.system"])

        assert not policy.validate("python -c 'import os; os.system(\"rm -rf /\")'").is_safe

    def test_allows_clean_commands(self):
        """Should allow commands without suspicious patterns."""
        policy = PatternPolicy(["eval", "exec"])

        assert policy.validate("git log").is_safe
        assert policy.validate("python script.py").is_safe


class TestCommandSecurityValidator:
    """Integration tests for full validator."""

    def test_whitelist_mode_blocks_by_default(self):
        """In whitelist mode, should block commands not in whitelist."""
        validator = CommandSecurityValidator(
            [
                WhitelistPolicy(["git log", "ls"]),
            ]
        )

        # Whitelisted - allow
        assert validator.validate("git log --oneline").is_safe

        # Not whitelisted - block
        assert not validator.validate("git push").is_safe
        assert not validator.validate("rm file.txt").is_safe

    def test_all_policies_must_pass(self):
        """All policies must pass (AND logic)."""
        validator = CommandSecurityValidator(
            [
                WhitelistPolicy(["git log", "ls", "rm"]),  # rm is in whitelist
                BlacklistPolicy(["rm "]),  # But also in blacklist
            ]
        )

        # Blocked by blacklist even though in whitelist
        result = validator.validate("rm file.txt")
        assert not result.is_safe
        assert "blacklist" in result.reason.lower()

    def test_defense_in_depth(self):
        """Multiple layers catch different bypass attempts."""
        validator = CommandSecurityValidator(
            [
                WhitelistPolicy(["git", "ls", "cat"]),
                BlacklistPolicy(["rm ", "sudo "]),
                LengthPolicy(100),
                PatternPolicy(["eval", "exec"]),
            ]
        )

        # Caught by different policies
        assert not validator.validate("rm file.txt").is_safe  # Blacklist
        assert not validator.validate("python -c 'eval(x)'").is_safe  # Pattern
        assert not validator.validate("echo " + "x" * 200).is_safe  # Length

    def test_safe_command_passes_all_checks(self):
        """Safe commands should pass all policies."""
        validator = CommandSecurityValidator(
            [
                WhitelistPolicy(["git log"]),
                BlacklistPolicy(["rm ", "sudo "]),
                LengthPolicy(100),
            ]
        )

        result = validator.validate("git log --oneline")
        assert result.is_safe


class TestBypassAttempts:
    """Test common bypass attempts (security hardening)."""

    def test_case_variations(self):
        """Should catch case variations."""
        policy = BlacklistPolicy(["rm "])

        # Standard case handling should catch these
        assert not policy.validate("RM file.txt").is_safe
        assert not policy.validate("Rm file.txt").is_safe

    def test_spacing_variations(self):
        """Should catch spacing variations."""
        policy = BlacklistPolicy(["rm "])

        # Extra spaces
        assert not policy.validate("rm  file.txt").is_safe  # Double space

    def test_command_chaining(self):
        """Should catch dangerous commands in chains."""
        policy = BlacklistPolicy(["rm "])

        assert not policy.validate("ls -la && rm file.txt").is_safe
        assert not policy.validate("cat file.txt; rm file.txt").is_safe

    def test_whitespace_tricks(self):
        """Should handle whitespace tricks."""
        policy = BlacklistPolicy(["rm "])

        # Tabs, newlines (in command string)
        assert not policy.validate("rm\tfile.txt").is_safe


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_command(self):
        """Should handle empty commands."""
        policy = WhitelistPolicy(["git log"])
        result = policy.validate("")

        assert not result.is_safe

    def test_whitespace_only(self):
        """Should handle whitespace-only commands."""
        policy = WhitelistPolicy(["git log"])
        result = policy.validate("   ")

        assert not result.is_safe

    def test_unicode_commands(self):
        """Should handle Unicode characters."""
        policy = WhitelistPolicy(["git log"])

        # Polish characters
        result = policy.validate("git log --author='Michał'")
        assert result.is_safe


# Pytest configuration
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
