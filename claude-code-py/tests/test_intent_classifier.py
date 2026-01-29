"""Tests for ConfigDrivenClassifier (keyword-based intent classification)."""

import pytest
from core.intent.classifier import ConfigDrivenClassifier


@pytest.fixture
def classifier():
    return ConfigDrivenClassifier()


class TestExploreProject:
    def test_polish(self, classifier):
        intent, tc = classifier.classify("widzisz projekt")
        assert intent == "explore_project"
        assert tc == {"type": "tool", "name": "bash"}

    def test_english(self, classifier):
        assert classifier.classify("show me the project")[0] == "explore_project"

    def test_co_w_projekcie(self, classifier):
        assert classifier.classify("co jest w projekcie")[0] == "explore_project"


class TestListFiles:
    def test_polish(self, classifier):
        intent, tc = classifier.classify("jakie pliki")
        assert intent == "list_files"
        assert tc == {"type": "tool", "name": "bash"}

    def test_english(self, classifier):
        assert classifier.classify("list files")[0] == "list_files"

    def test_obczaj(self, classifier):
        assert classifier.classify("obczaj co tu jest")[0] == "list_files"

    def test_co_tu_widzisz(self, classifier):
        assert classifier.classify("co tu widzisz")[0] == "list_files"

    def test_profanity(self, classifier):
        assert classifier.classify("jakie widzisz kurwa pliki")[0] == "list_files"

    def test_obczaj_pliki_kurwa(self, classifier):
        assert classifier.classify("obczaj pliki kurwa")[0] == "list_files"

    def test_show_files(self, classifier):
        assert classifier.classify("show files")[0] == "list_files"

    def test_sprawdz_folder(self, classifier):
        assert classifier.classify("sprawdz folder")[0] == "list_files"


class TestGitLog:
    def test_polish(self, classifier):
        assert classifier.classify("ostatni commit")[0] == "git_log"

    def test_english(self, classifier):
        assert classifier.classify("last commit")[0] == "git_log"

    def test_git_log(self, classifier):
        assert classifier.classify("git log")[0] == "git_log"


class TestAnalyzeChanges:
    def test_przeanalizuj(self, classifier):
        assert classifier.classify("przeanalizuj")[0] == "analyze_changes"

    def test_analyze(self, classifier):
        assert classifier.classify("analyze changes")[0] == "analyze_changes"


class TestGeneral:
    def test_greeting(self, classifier):
        intent, tc = classifier.classify("what is the meaning of life?")
        assert intent == "general"
        assert tc is None

    def test_pierdoly_not_analyze(self, classifier):
        assert classifier.classify("widzisz pierdoły")[0] != "analyze_changes"

    def test_hello(self, classifier):
        assert classifier.classify("heloł śmieciu")[0] == "general"
