"""Refactoring Agent - specialized in code improvement and restructuring."""

from ..base import BaseAgent, AgentConfig, AgentRole


class RefactorerAgent(BaseAgent):
    """Agent specialized in refactoring and code improvement."""

    def __init__(self):
        """Initialize Refactorer Agent."""
        config = AgentConfig(
            name="Refactorer",
            role=AgentRole.REFACTORER,
            description="Expert in refactoring code for better design, maintainability, and performance. Applies SOLID principles, design patterns, and industry best practices while preserving functionality.",
            system_prompt="""You are an expert software architect and refactoring specialist.

Your expertise includes:
- Design patterns and their applications
- SOLID principles
- Code organization and structure
- DRY (Don't Repeat Yourself)
- Separation of concerns
- Performance optimization
- Code maintainability
- Clean code principles

When refactoring:
1. Understand the current code and its purpose
2. Identify code smells and improvement opportunities
3. Plan refactoring steps carefully
4. Preserve existing functionality (no behavior changes)
5. Apply appropriate design patterns
6. Improve naming and clarity
7. Reduce duplication
8. Enhance testability

Refactoring principles:
- Make small, incremental changes
- Ensure tests pass after each change
- Improve one thing at a time
- Document significant structural changes
- Consider performance implications
- Maintain backward compatibility when needed

Always provide:
- Clear explanation of current issues
- Refactoring strategy
- Step-by-step changes
- Benefits of the refactoring
- Any risks or trade-offs
- How to verify correctness

Focus on making code more:
- Readable and understandable
- Maintainable and extensible
- Testable and modular
- Efficient and performant""",
            thinking_budget=20000,
            keywords=[
                "refactor",
                "restructure",
                "improve code",
                "clean up",
                "optimize",
                "reorganize",
                "better design",
                "rewrite",
                "simplify",
            ],
        )
        super().__init__(config)

    def can_handle(self, task_description: str) -> float:
        """Determine if this agent can handle the task."""
        task_lower = task_description.lower()

        # High confidence
        high_confidence = ["refactor", "restructure", "reorganize", "clean up", "improve code"]
        if any(keyword in task_lower for keyword in high_confidence):
            return 0.95

        # Medium confidence
        medium_confidence = [
            "optimize",
            "simplify",
            "rewrite",
            "better design",
            "improve structure",
            "make better",
        ]
        if any(keyword in task_lower for keyword in medium_confidence):
            return 0.75

        # Improvement-related
        if any(word in task_lower for word in ["improve", "better", "cleaner"]):
            return 0.5

        return 0.0
