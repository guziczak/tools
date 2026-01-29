"""Tests for ConfigDrivenClassifier (LLM-based intent classification)."""

import pytest
from unittest.mock import MagicMock, patch
from core.intent.classifier import ConfigDrivenClassifier


def _mock_classifier(intent_response: str) -> ConfigDrivenClassifier:
    """Create a classifier with a mocked Anthropic client."""
    c = ConfigDrivenClassifier()
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text=intent_response)]
    mock_client.messages.create.return_value = mock_resp
    c._client = mock_client
    c._init_done = True
    return c


def _classifier_returning(intent_map: dict) -> ConfigDrivenClassifier:
    """Create a classifier that returns different intents based on message content."""
    c = ConfigDrivenClassifier()
    mock_client = MagicMock()

    def side_effect(**kwargs):
        msg = kwargs["messages"][0]["content"]
        # Extract user message from prompt
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


class TestExploreProject:
    def test_polish_exact(self):
        c = _mock_classifier("explore_project")
        intent, tc = c.classify("widzisz projekt")
        assert intent == "explore_project"
        assert tc == {"type": "tool", "name": "bash"}

    def test_polish_question(self):
        c = _mock_classifier("explore_project")
        intent, tc = c.classify("czy widzisz projekt?")
        assert intent == "explore_project"

    def test_english(self):
        c = _mock_classifier("explore_project")
        intent, tc = c.classify("show me the project")
        assert intent == "explore_project"

    def test_co_w_projekcie(self):
        c = _mock_classifier("explore_project")
        intent, _ = c.classify("co jest w projekcie")
        assert intent == "explore_project"


class TestListFiles:
    def test_polish_exact(self):
        c = _mock_classifier("list_files")
        intent, tc = c.classify("jakie pliki")
        assert intent == "list_files"
        assert tc == {"type": "tool", "name": "bash"}

    def test_english(self):
        c = _mock_classifier("list_files")
        intent, _ = c.classify("list files")
        assert intent == "list_files"

    def test_co_tu_widzisz(self):
        c = _mock_classifier("list_files")
        intent, _ = c.classify("co tu widzisz")
        assert intent == "list_files"

    def test_obczaj_folder(self):
        c = _mock_classifier("list_files")
        intent, _ = c.classify("obczaj folder")
        assert intent == "list_files"

    def test_show_directory(self):
        c = _mock_classifier("list_files")
        intent, _ = c.classify("show directory")
        assert intent == "list_files"

    def test_sprawdz_folder(self):
        c = _mock_classifier("list_files")
        intent, _ = c.classify("sprawdz folder")
        assert intent == "list_files"

    def test_profanity_doesnt_break(self):
        """'jakie widzisz kurwa pliki' should still classify as list_files."""
        c = _mock_classifier("list_files")
        intent, _ = c.classify("jakie widzisz kurwa pliki")
        assert intent == "list_files"


class TestGitLog:
    def test_polish_keyword(self):
        c = _mock_classifier("git_log")
        intent, tc = c.classify("ostatni commit")
        assert intent == "git_log"
        assert tc is None

    def test_english_keyword(self):
        c = _mock_classifier("git_log")
        intent, _ = c.classify("last commit")
        assert intent == "git_log"

    def test_git_log_exact(self):
        c = _mock_classifier("git_log")
        intent, _ = c.classify("git log")
        assert intent == "git_log"

    def test_git_history(self):
        c = _mock_classifier("git_log")
        intent, _ = c.classify("git history")
        assert intent == "git_log"


class TestAnalyzeChanges:
    def test_przeanalizuj(self):
        c = _mock_classifier("analyze_changes")
        intent, _ = c.classify("przeanalizuj")
        assert intent == "analyze_changes"

    def test_analyze(self):
        c = _mock_classifier("analyze_changes")
        intent, _ = c.classify("analyze")
        assert intent == "analyze_changes"

    def test_analyze_changes(self):
        c = _mock_classifier("analyze_changes")
        intent, _ = c.classify("analyze changes")
        assert intent == "analyze_changes"

    def test_show_details(self):
        c = _mock_classifier("analyze_changes")
        intent, _ = c.classify("show details")
        assert intent == "analyze_changes"


class TestGeneral:
    def test_random_question(self):
        c = _mock_classifier("general")
        intent, tc = c.classify("what is the meaning of life?")
        assert intent == "general"
        assert tc is None

    def test_pierdoly_not_analyze(self):
        """'widzisz pierdoły' should NOT route to analyze_changes."""
        c = _mock_classifier("general")
        intent, _ = c.classify("widzisz pierdoły")
        assert intent != "analyze_changes"

    def test_long_message_skips_llm(self):
        """Messages >20 words should skip LLM and return general."""
        c = ConfigDrivenClassifier()
        long_msg = " ".join(["word"] * 25)
        intent, _ = c.classify(long_msg)
        assert intent == "general"

    def test_no_client_returns_general(self):
        """Without a client, always returns general."""
        c = ConfigDrivenClassifier()
        c._init_done = True  # skip lazy init
        intent, _ = c.classify("jakie pliki")
        assert intent == "general"


class TestUnknownIntent:
    def test_unknown_intent_falls_back(self):
        """If LLM returns gibberish, fall back to general."""
        c = _mock_classifier("some_random_nonsense")
        intent, _ = c.classify("hello")
        assert intent == "general"


class TestLLMCallParams:
    def test_uses_haiku(self):
        """Classifier should use haiku model."""
        c = _mock_classifier("general")
        c.classify("test")
        call_kwargs = c._client.messages.create.call_args.kwargs
        assert "haiku" in call_kwargs["model"]

    def test_low_max_tokens(self):
        """Classifier should use minimal tokens."""
        c = _mock_classifier("general")
        c.classify("test")
        call_kwargs = c._client.messages.create.call_args.kwargs
        assert call_kwargs["max_tokens"] <= 20

    def test_zero_temperature(self):
        """Classifier should use temperature=0 for determinism."""
        c = _mock_classifier("general")
        c.classify("test")
        call_kwargs = c._client.messages.create.call_args.kwargs
        assert call_kwargs["temperature"] == 0.0
