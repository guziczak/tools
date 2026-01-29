"""Unit tests for LLM-based intent classification."""

import pytest
from unittest.mock import MagicMock
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.intent import ConfigDrivenClassifier


class TestConfigDrivenClassifier:
    """Tests for LLM-based classifier (mocked)."""

    def _make(self, intent_map):
        c = ConfigDrivenClassifier()
        mock_client = MagicMock()
        def side_effect(**kwargs):
            msg = kwargs["messages"][0]["content"]
            for key, intent in intent_map.items():
                if key in msg:
                    resp = MagicMock()
                    resp.content = [MagicMock(text=intent)]
                    return resp
            resp = MagicMock()
            resp.content = [MagicMock(text="general")]
            return resp
        mock_client.messages.create.side_effect = side_effect
        c._client = mock_client
        c._init_done = True
        return c

    def test_handles_polish_queries(self):
        classifier = self._make({
            "widzisz projekt": "explore_project",
            "ostatni commit": "git_log",
            "jakie pliki": "list_files",
        })
        assert classifier.classify("widzisz projekt")[0] == "explore_project"
        assert classifier.classify("ostatni commit")[0] == "git_log"
        assert classifier.classify("jakie pliki")[0] == "list_files"

    def test_handles_english_queries(self):
        classifier = self._make({
            "show me the project": "explore_project",
            "last commit": "git_log",
            "list files": "list_files",
        })
        assert classifier.classify("show me the project")[0] == "explore_project"
        assert classifier.classify("last commit")[0] == "git_log"
        assert classifier.classify("list files")[0] == "list_files"

    def test_returns_tool_choice(self):
        classifier = self._make({
            "widzisz projekt": "explore_project",
            "git log": "git_log",
        })
        _, tc = classifier.classify("widzisz projekt")
        assert tc == {"type": "tool", "name": "bash"}
        _, tc = classifier.classify("git log")
        assert tc is None

    def test_word_order_invariance(self):
        classifier = self._make({
            "ostatni commit": "git_log",
            "commit ostatni": "git_log",
        })
        assert classifier.classify("ostatni commit")[0] == "git_log"
        assert classifier.classify("commit ostatni")[0] == "git_log"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
