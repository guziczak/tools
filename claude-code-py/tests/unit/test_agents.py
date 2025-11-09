"""Unit tests for agent system."""

import pytest
from agents.base import BaseAgent, AgentConfig, AgentRole, AgentResult
from agents.registry import AgentRegistry
from agents.thinking import detect_thinking_level, ThinkingLevel
from agents.prebuilt import TestWriterAgent, CodeReviewerAgent, BugFixerAgent, RefactorerAgent


class TestThinkingLevel:
    """Tests for thinking level detection."""

    def test_ultrathink_detection(self):
        """Test ultrathink keyword detection."""
        level, explicit = detect_thinking_level("ultrathink about this problem")
        assert level == ThinkingLevel.ULTRA
        assert explicit is True
        assert level.budget == 32000

    def test_think_hard_detection(self):
        """Test think hard detection."""
        level, explicit = detect_thinking_level("think hard about the solution")
        assert level == ThinkingLevel.STANDARD
        assert explicit is True
        assert level.budget == 10000

    def test_basic_think_detection(self):
        """Test basic think detection."""
        level, explicit = detect_thinking_level("think about this")
        assert level == ThinkingLevel.BASIC
        assert explicit is True

    def test_implicit_complex_detection(self):
        """Test implicit thinking for complex tasks."""
        level, explicit = detect_thinking_level("refactor the entire codebase")
        assert level in [ThinkingLevel.STANDARD, ThinkingLevel.BASIC]
        assert explicit is False

    def test_no_thinking_for_simple_query(self):
        """Test no thinking for simple questions."""
        level, explicit = detect_thinking_level("what is 2+2?")
        assert level == ThinkingLevel.NONE
        assert explicit is False


class TestAgentRegistry:
    """Tests for agent registry."""

    def test_register_agent(self):
        """Test registering an agent."""
        registry = AgentRegistry()
        agent = TestWriterAgent()

        registry.register(agent)

        assert len(registry) == 1
        assert agent.name in registry
        assert registry.get_agent(agent.name) == agent

    def test_unregister_agent(self):
        """Test unregistering an agent."""
        registry = AgentRegistry()
        agent = TestWriterAgent()

        registry.register(agent)
        assert len(registry) == 1

        result = registry.unregister(agent.name)
        assert result is True
        assert len(registry) == 0
        assert agent.name not in registry

    def test_get_agents_by_role(self):
        """Test getting agents by role."""
        registry = AgentRegistry()

        test_agent = TestWriterAgent()
        review_agent = CodeReviewerAgent()

        registry.register(test_agent)
        registry.register(review_agent)

        test_agents = registry.get_agents_by_role(AgentRole.TEST_WRITER)
        assert len(test_agents) == 1
        assert test_agents[0] == test_agent

        review_agents = registry.get_agents_by_role(AgentRole.CODE_REVIEWER)
        assert len(review_agents) == 1
        assert review_agents[0] == review_agent

    def test_find_best_agent(self):
        """Test finding best agent for task."""
        registry = AgentRegistry()

        registry.register(TestWriterAgent())
        registry.register(CodeReviewerAgent())
        registry.register(BugFixerAgent())

        # Test writer should handle test-related tasks
        result = registry.find_best_agent("write tests for this function")
        assert result is not None
        agent, confidence = result
        assert agent.role == AgentRole.TEST_WRITER
        assert confidence >= 0.5

        # Bug fixer should handle bug-related tasks
        result = registry.find_best_agent("fix this bug in the code")
        assert result is not None
        agent, confidence = result
        assert agent.role == AgentRole.BUG_FIXER
        assert confidence >= 0.5

    def test_no_suitable_agent(self):
        """Test when no agent is suitable."""
        registry = AgentRegistry()
        registry.register(TestWriterAgent())

        # Code review task but only test writer available
        result = registry.find_best_agent("just say hello")
        # Should return None or low confidence
        if result:
            _, confidence = result
            assert confidence < 0.9  # Not highly confident


class TestTestWriterAgent:
    """Tests for Test Writer Agent."""

    def test_handles_test_writing(self):
        """Test that agent identifies test writing tasks."""
        agent = TestWriterAgent()

        confidence = agent.can_handle("write unit tests for read_file function")
        assert confidence >= 0.7

    def test_rejects_non_test_tasks(self):
        """Test that agent rejects non-test tasks."""
        agent = TestWriterAgent()

        confidence = agent.can_handle("refactor this code")
        assert confidence < 0.5

    def test_agent_config(self):
        """Test agent configuration."""
        agent = TestWriterAgent()

        assert agent.role == AgentRole.TEST_WRITER
        assert agent.name == "Test Writer"
        assert agent.thinking_budget == 15000
        assert len(agent.keywords) > 0

    def test_anthropic_tool_format(self):
        """Test conversion to Anthropic tool format."""
        agent = TestWriterAgent()

        tool = agent.to_anthropic_tool()

        assert tool["name"] == "delegate_to_test_writer"
        assert "description" in tool
        assert "input_schema" in tool
        assert tool["input_schema"]["type"] == "object"
        assert "task" in tool["input_schema"]["properties"]


class TestBugFixerAgent:
    """Tests for Bug Fixer Agent."""

    def test_handles_bug_fixing(self):
        """Test that agent identifies bug fixing tasks."""
        agent = BugFixerAgent()

        confidence = agent.can_handle("fix this bug in the authentication")
        assert confidence >= 0.9

        confidence = agent.can_handle("error when calling this function")
        assert confidence >= 0.7

    def test_high_confidence_for_errors(self):
        """Test high confidence for error-related tasks."""
        agent = BugFixerAgent()

        confidence = agent.can_handle("this is broken and crashes")
        assert confidence >= 0.8


class TestCodeReviewerAgent:
    """Tests for Code Reviewer Agent."""

    def test_handles_reviews(self):
        """Test that agent identifies review tasks."""
        agent = CodeReviewerAgent()

        confidence = agent.can_handle("review this pull request")
        assert confidence >= 0.8

        confidence = agent.can_handle("check if this code is correct")
        assert confidence >= 0.7

    def test_questions_about_code(self):
        """Test detection of code quality questions."""
        agent = CodeReviewerAgent()

        confidence = agent.can_handle("is this code good?")
        assert confidence >= 0.4  # Should match question pattern


class TestRefactorerAgent:
    """Tests for Refactorer Agent."""

    def test_handles_refactoring(self):
        """Test that agent identifies refactoring tasks."""
        agent = RefactorerAgent()

        confidence = agent.can_handle("refactor this function")
        assert confidence >= 0.9

        confidence = agent.can_handle("improve the structure of this code")
        assert confidence >= 0.7

    def test_cleanup_tasks(self):
        """Test detection of code cleanup tasks."""
        agent = RefactorerAgent()

        confidence = agent.can_handle("clean up this messy code")
        assert confidence >= 0.8
