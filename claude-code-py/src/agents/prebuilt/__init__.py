"""Pre-built specialized agents."""

from .test_writer import TestWriterAgent
from .code_reviewer import CodeReviewerAgent
from .bug_fixer import BugFixerAgent
from .refactorer import RefactorerAgent


def create_default_agents():
    """Create all default pre-built agents.

    Returns:
        List of agent instances
    """
    return [
        TestWriterAgent(),
        CodeReviewerAgent(),
        BugFixerAgent(),
        RefactorerAgent(),
    ]


__all__ = [
    "TestWriterAgent",
    "CodeReviewerAgent",
    "BugFixerAgent",
    "RefactorerAgent",
    "create_default_agents",
]
