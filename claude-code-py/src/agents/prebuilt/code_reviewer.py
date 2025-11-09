"""Code Review Agent - specialized in reviewing code quality."""

from ..base import BaseAgent, AgentConfig, AgentRole


class CodeReviewerAgent(BaseAgent):
    """Agent specialized in code review and quality assessment."""

    def __init__(self):
        """Initialize Code Reviewer Agent."""
        config = AgentConfig(
            name="Code Reviewer",
            role=AgentRole.CODE_REVIEWER,
            description="Expert in code review, identifying bugs, security issues, performance problems, and code quality improvements. Provides constructive feedback following industry best practices.",
            system_prompt="""You are an expert code reviewer with deep knowledge of software engineering best practices.

Your expertise includes:
- Code quality assessment
- Security vulnerability detection
- Performance optimization opportunities
- Design pattern recognition
- Best practices enforcement
- Bug identification
- Code maintainability analysis

When reviewing code:
1. Check for bugs and logical errors
2. Identify security vulnerabilities
3. Look for performance issues
4. Assess code readability and maintainability
5. Verify proper error handling
6. Check for code smells and anti-patterns
7. Suggest improvements with explanations
8. Be constructive and specific

Provide clear, actionable feedback with:
- Issue severity (Critical/High/Medium/Low)
- Specific location (file:line)
- Clear explanation of the problem
- Suggested fix or improvement
- Why the change matters

Focus on making the code better, safer, and more maintainable.""",
            thinking_budget=20000,
            keywords=[
                "review",
                "code review",
                "check code",
                "look at",
                "analyze code",
                "feedback on",
                "is this correct",
                "anything wrong",
                "improve this",
            ],
        )
        super().__init__(config)

    def can_handle(self, task_description: str) -> float:
        """Determine if this agent can handle the task."""
        task_lower = task_description.lower()

        # High confidence
        high_confidence = ["review", "code review", "check this", "look at this", "feedback on"]
        if any(keyword in task_lower for keyword in high_confidence):
            return 0.9

        # Medium confidence
        medium_confidence = [
            "is this correct",
            "anything wrong",
            "improve this",
            "better way",
            "what do you think",
        ]
        if any(keyword in task_lower for keyword in medium_confidence):
            return 0.7

        # Questions about code quality
        if "?" in task_description and any(
            word in task_lower for word in ["code", "function", "class", "this"]
        ):
            return 0.5

        return 0.0
