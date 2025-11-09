"""Test Writing Agent - specialized in writing comprehensive tests."""

from ..base import BaseAgent, AgentConfig, AgentRole


class TestWriterAgent(BaseAgent):
    """Agent specialized in writing unit and integration tests."""

    def __init__(self):
        """Initialize Test Writer Agent."""
        config = AgentConfig(
            name="Test Writer",
            role=AgentRole.TEST_WRITER,
            description="Expert in writing comprehensive unit tests, integration tests, and test fixtures. Follows best practices for pytest, test coverage, and test design patterns.",
            system_prompt="""You are an expert test engineer specializing in writing high-quality tests.

Your expertise includes:
- Unit testing with pytest
- Integration testing
- Test fixtures and mocks
- Test-driven development (TDD)
- Edge case identification
- Test coverage optimization
- Testing best practices

When writing tests:
1. Write clear, descriptive test names
2. Follow AAA pattern (Arrange, Act, Assert)
3. Test both success and error cases
4. Include edge cases and boundary conditions
5. Use appropriate fixtures and mocks
6. Keep tests independent and isolated
7. Add docstrings explaining what is tested

Always aim for >80% code coverage and write tests that are maintainable and readable.""",
            thinking_budget=15000,
            keywords=[
                "write test",
                "add test",
                "test for",
                "unit test",
                "integration test",
                "test coverage",
                "pytest",
                "test this",
                "need tests",
            ],
        )
        super().__init__(config)

    def can_handle(self, task_description: str) -> float:
        """Determine if this agent can handle the task.

        Args:
            task_description: Task description

        Returns:
            Confidence score (0.0 to 1.0)
        """
        task_lower = task_description.lower()

        # High confidence keywords
        high_confidence = [
            "write test",
            "add test",
            "create test",
            "test for",
            "unit test",
            "integration test",
        ]
        if any(keyword in task_lower for keyword in high_confidence):
            return 0.9

        # Medium confidence keywords
        medium_confidence = ["pytest", "test coverage", "test case", "test this", "need test"]
        if any(keyword in task_lower for keyword in medium_confidence):
            return 0.7

        # Low confidence - test mentioned but not primary focus
        if "test" in task_lower:
            return 0.4

        return 0.0
