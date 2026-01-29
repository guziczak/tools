"""Tests for ConfigDrivenClassifier - all triggers from intent_patterns.json."""

import pytest
from core.intent.classifier import ConfigDrivenClassifier


@pytest.fixture
def classifier():
    return ConfigDrivenClassifier()


class TestExploreProject:
    def test_polish_exact(self, classifier):
        intent, tc = classifier.classify("widzisz projekt")
        assert intent == "explore_project"
        assert tc == {"type": "tool", "name": "bash"}

    def test_polish_question(self, classifier):
        intent, tc = classifier.classify("czy widzisz projekt?")
        assert intent == "explore_project"

    def test_english(self, classifier):
        intent, tc = classifier.classify("show me the project")
        assert intent == "explore_project"

    def test_co_w_projekcie(self, classifier):
        intent, _ = classifier.classify("co jest w projekcie")
        assert intent == "explore_project"


class TestListFiles:
    def test_polish_exact(self, classifier):
        intent, tc = classifier.classify("jakie pliki")
        assert intent == "list_files"
        assert tc == {"type": "tool", "name": "bash"}

    def test_english(self, classifier):
        intent, _ = classifier.classify("list files")
        assert intent == "list_files"

    def test_co_tu_widzisz(self, classifier):
        intent, _ = classifier.classify("co tu widzisz")
        assert intent == "list_files"

    def test_obczaj_folder(self, classifier):
        intent, _ = classifier.classify("obczaj folder")
        assert intent == "list_files"

    def test_show_directory(self, classifier):
        intent, _ = classifier.classify("show directory")
        assert intent == "list_files"

    def test_sprawdz_folder(self, classifier):
        intent, _ = classifier.classify("sprawdz folder")
        assert intent == "list_files"


class TestGitLog:
    def test_polish_keyword(self, classifier):
        intent, tc = classifier.classify("ostatni commit")
        assert intent == "git_log"
        assert tc is None

    def test_english_keyword(self, classifier):
        intent, _ = classifier.classify("last commit")
        assert intent == "git_log"

    def test_git_log_exact(self, classifier):
        intent, _ = classifier.classify("git log")
        assert intent == "git_log"

    def test_git_history(self, classifier):
        intent, _ = classifier.classify("git history")
        assert intent == "git_log"


class TestAnalyzeChanges:
    def test_przeanalizuj(self, classifier):
        intent, _ = classifier.classify("przeanalizuj")
        assert intent == "analyze_changes"

    def test_analyze(self, classifier):
        intent, _ = classifier.classify("analyze")
        assert intent == "analyze_changes"

    def test_analyze_changes(self, classifier):
        intent, _ = classifier.classify("analyze changes")
        assert intent == "analyze_changes"

    def test_show_details(self, classifier):
        intent, _ = classifier.classify("show details")
        assert intent == "analyze_changes"


class TestGeneral:
    def test_random_question(self, classifier):
        intent, tc = classifier.classify("what is the meaning of life?")
        assert intent == "general"
        assert tc is None

    def test_pierdoly_not_analyze(self, classifier):
        """'widzisz pierdoły' should NOT route to analyze_changes."""
        intent, _ = classifier.classify("widzisz pierdoły")
        assert intent != "analyze_changes"
