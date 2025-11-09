"""Bug Fixing Agent - specialized in debugging and fixing issues."""

from ..base import BaseAgent, AgentConfig, AgentRole


class BugFixerAgent(BaseAgent):
    """Agent specialized in debugging and fixing bugs."""

    def __init__(self):
        """Initialize Bug Fixer Agent."""
        config = AgentConfig(
            name="Bug Fixer",
            role=AgentRole.BUG_FIXER,
            description="Expert debugger specializing in identifying root causes of bugs, tracing execution paths, and implementing robust fixes. Experienced with common bug patterns and debugging techniques.",
            system_prompt="""You are an expert debugger with exceptional problem-solving skills.

Your expertise includes:
- Root cause analysis
- Debugging techniques and strategies
- Common bug patterns recognition
- Stack trace analysis
- Edge case identification
- Error reproduction
- Fix implementation
- Regression prevention

When fixing bugs:
1. Understand the bug symptoms and reproduction steps
2. Analyze the code and identify root cause
3. Consider edge cases and related issues
4. Implement a minimal, focused fix
5. Explain why the bug occurred
6. Verify the fix doesn't introduce new issues
7. Suggest tests to prevent regression
8. Document the fix clearly

Debugging methodology:
- Read error messages carefully
- Trace execution paths
- Check assumptions and invariants
- Look for common patterns (off-by-one, null checks, race conditions)
- Test edge cases
- Verify fix with examples

Always provide:
- Clear explanation of the bug
- Root cause analysis
- The fix with explanation
- How to test the fix
- Prevention strategies""",
            thinking_budget=25000,
            keywords=[
                "bug",
                "error",
                "fix",
                "broken",
                "not working",
                "issue",
                "problem",
                "crash",
                "exception",
                "debug",
                "fails",
                "doesn't work",
            ],
        )
        super().__init__(config)

    def can_handle(self, task_description: str) -> float:
        """Determine if this agent can handle the task."""
        task_lower = task_description.lower()

        # High confidence
        high_confidence = [
            "fix bug",
            "debug",
            "not working",
            "broken",
            "error",
            "exception",
            "crash",
            "fails",
        ]
        if any(keyword in task_lower for keyword in high_confidence):
            return 0.95

        # Medium confidence
        medium_confidence = ["issue", "problem", "doesn't work", "wrong", "incorrect", "unexpected"]
        if any(keyword in task_lower for keyword in medium_confidence):
            return 0.75

        # Bug-related words
        if any(word in task_lower for word in ["bug", "fix", "error"]):
            return 0.6

        return 0.0
