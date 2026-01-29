"""Unit tests for keyword-based intent classification."""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.intent import ConfigDrivenClassifier


class TestConfigDrivenClassifier:
    def test_handles_polish_queries(self):
        c = ConfigDrivenClassifier()
        assert c.classify("widzisz projekt")[0] == "explore_project"
        assert c.classify("ostatni commit")[0] == "git_log"
        assert c.classify("jakie pliki")[0] == "list_files"

    def test_handles_english_queries(self):
        c = ConfigDrivenClassifier()
        assert c.classify("show me the project")[0] == "explore_project"
        assert c.classify("last commit")[0] == "git_log"
        assert c.classify("list files")[0] == "list_files"

    def test_returns_tool_choice(self):
        c = ConfigDrivenClassifier()
        _, tc = c.classify("widzisz projekt")
        assert tc == {"type": "tool", "name": "bash"}
        _, tc = c.classify("git log")
        assert tc is None

    def test_word_order_invariance(self):
        c = ConfigDrivenClassifier()
        assert c.classify("ostatni commit")[0] == "git_log"
        assert c.classify("commit ostatni")[0] == "git_log"

    def test_profanity_resilience(self):
        c = ConfigDrivenClassifier()
        assert c.classify("obczaj pliki kurwa")[0] == "list_files"
        assert c.classify("co tu kurwa mamy")[0] == "list_files"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
