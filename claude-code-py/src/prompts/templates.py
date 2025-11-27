"""Prompt Templates.

Contains prompt templates and utilities for formatting prompts
for different AI tasks and scenarios.

Based on the TypeScript implementation from claude-code-source-code-deobfuscation-main.
"""

from dataclasses import dataclass
from typing import Dict, Any, Tuple, Optional
from pathlib import Path


# System prompts for different tasks

CODE_ASSISTANT_SYSTEM_PROMPT = """
You are Claude, an AI assistant with expertise in programming and software development.
Your task is to assist with coding-related questions, debugging, refactoring, and explaining code.

Guidelines:
- Provide clear, concise, and accurate responses
- Include code examples where helpful
- Prioritize modern best practices
- If you're unsure, acknowledge limitations instead of guessing
- Focus on understanding the user's intent, even if the question is ambiguous
"""

CODE_GENERATION_SYSTEM_PROMPT = """
You are Claude, an AI assistant focused on helping write high-quality code.
Your task is to generate code based on user requirements and specifications.

Guidelines:
- Write clean, efficient, and well-documented code
- Follow language-specific best practices and conventions
- Include helpful comments explaining complex sections
- Prioritize maintainability and readability
- Structure code logically with appropriate error handling
- Consider edge cases and potential issues
"""

CODE_REVIEW_SYSTEM_PROMPT = """
You are Claude, an AI code reviewer with expertise in programming best practices.
Your task is to analyze code, identify issues, and suggest improvements.

Guidelines:
- Look for bugs, security issues, and performance problems
- Suggest improvements for readability and maintainability
- Identify potential edge cases and error handling gaps
- Point out violations of best practices or conventions
- Provide constructive feedback with clear explanations
- Be thorough but prioritize important issues over minor stylistic concerns
"""

CODE_EXPLANATION_SYSTEM_PROMPT = """
You are Claude, an AI assistant that specializes in explaining code.
Your task is to break down and explain code in a clear, educational manner.

Guidelines:
- Explain the purpose and functionality of the code
- Break down complex parts step by step
- Define technical terms and concepts when relevant
- Use analogies or examples to illustrate concepts
- Focus on the core logic rather than trivial details
- Adjust explanation depth based on the apparent complexity of the question
"""


@dataclass
class PromptTemplate:
    """Prompt template definition."""

    template: str
    system: Optional[str] = None
    defaults: Optional[Dict[str, str]] = None


# Collection of prompt templates for common tasks
TEMPLATES: Dict[str, PromptTemplate] = {
    "explain_code": PromptTemplate(
        template="Please explain what this code does:\n\n```{language}\n{code}\n```",
        system=CODE_EXPLANATION_SYSTEM_PROMPT,
        defaults={"code": "// Paste code here", "language": ""},
    ),
    "refactor_code": PromptTemplate(
        template=(
            "Please refactor this code to improve {focus}:\n\n"
            "```{language}\n{code}\n```\n\n"
            "Additional context: {context}"
        ),
        system=CODE_GENERATION_SYSTEM_PROMPT,
        defaults={
            "focus": "readability and maintainability",
            "code": "// Paste code here",
            "language": "",
            "context": "None",
        },
    ),
    "debug_code": PromptTemplate(
        template=(
            "Please help me debug the following code:\n\n"
            "```{language}\n{code}\n```\n\n"
            "The issue I'm seeing is: {issue}\n\n"
            "Any error messages: {error_messages}"
        ),
        system=CODE_ASSISTANT_SYSTEM_PROMPT,
        defaults={
            "code": "// Paste code here",
            "language": "",
            "issue": "Describe the issue you're experiencing",
            "error_messages": "None",
        },
    ),
    "review_code": PromptTemplate(
        template="Please review this code and provide feedback:\n\n```{language}\n{code}\n```",
        system=CODE_REVIEW_SYSTEM_PROMPT,
        defaults={"code": "// Paste code here", "language": ""},
    ),
    "generate_code": PromptTemplate(
        template=(
            "Please write code to {task}.\n\n"
            "Language/Framework: {language}\n\n"
            "Requirements:\n{requirements}"
        ),
        system=CODE_GENERATION_SYSTEM_PROMPT,
        defaults={
            "task": "Describe what you want the code to do",
            "language": "Specify language or framework",
            "requirements": "- List your requirements here",
        },
    ),
    "document_code": PromptTemplate(
        template=(
            "Please add documentation to this code:\n\n"
            "```{language}\n{code}\n```\n\n"
            "Documentation style: {style}"
        ),
        system=CODE_GENERATION_SYSTEM_PROMPT,
        defaults={
            "code": "// Paste code here",
            "language": "",
            "style": "Standard comments and docstrings",
        },
    ),
    "test_code": PromptTemplate(
        template=(
            "Please write tests for this code:\n\n"
            "```{language}\n{code}\n```\n\n"
            "Testing framework: {framework}"
        ),
        system=CODE_GENERATION_SYSTEM_PROMPT,
        defaults={
            "code": "// Paste code here",
            "language": "",
            "framework": "Specify testing framework or 'standard'",
        },
    ),
    "fix_code": PromptTemplate(
        template=(
            "Please fix the issues in this code:\n\n"
            "```{language}\n{code}\n```\n\n"
            "Specific issue: {issue}"
        ),
        system=CODE_ASSISTANT_SYSTEM_PROMPT,
        defaults={
            "code": "// Paste code here",
            "language": "",
            "issue": "Describe what needs to be fixed",
        },
    ),
}


def format_prompt(
    template: str,
    values: Dict[str, Any],
    defaults: Optional[Dict[str, str]] = None,
) -> str:
    """Format a prompt by replacing placeholders with values.

    Args:
        template: The prompt template with {placeholders}
        values: Values to replace placeholders with
        defaults: Default values for placeholders not in values

    Returns:
        Formatted prompt string
    """
    # Merge defaults and provided values
    merged_values = {}
    if defaults:
        merged_values.update(defaults)
    merged_values.update(values)

    # Replace placeholders
    result = template
    for key, value in merged_values.items():
        placeholder = f"{{{key}}}"
        if placeholder in result:
            result = result.replace(placeholder, str(value))

    return result


def use_template(template_name: str, **values: Any) -> Tuple[str, Optional[str]]:
    """Format a prompt using a predefined template.

    Args:
        template_name: Name of the template from TEMPLATES
        **values: Values to replace placeholders with

    Returns:
        Tuple of (formatted prompt, system message)

    Raises:
        KeyError: If template not found
    """
    template = TEMPLATES.get(template_name)

    if not template:
        raise KeyError(f"Prompt template '{template_name}' not found")

    prompt = format_prompt(template.template, values, template.defaults)

    return prompt, template.system


def get_language_from_filepath(filepath: str) -> str:
    """Get language identifier from file path.

    Args:
        filepath: Path to the file

    Returns:
        Language identifier (e.g., 'python', 'javascript')
    """
    path = Path(filepath)
    extension = path.suffix.lower().lstrip(".")

    language_map = {
        "js": "javascript",
        "ts": "typescript",
        "jsx": "javascript",
        "tsx": "typescript",
        "py": "python",
        "rb": "ruby",
        "java": "java",
        "c": "c",
        "cpp": "cpp",
        "cc": "cpp",
        "cxx": "cpp",
        "cs": "csharp",
        "go": "go",
        "rs": "rust",
        "php": "php",
        "swift": "swift",
        "kt": "kotlin",
        "scala": "scala",
        "sh": "bash",
        "bash": "bash",
        "html": "html",
        "css": "css",
        "scss": "scss",
        "sass": "sass",
        "less": "less",
        "md": "markdown",
        "json": "json",
        "yml": "yaml",
        "yaml": "yaml",
        "toml": "toml",
        "sql": "sql",
        "graphql": "graphql",
        "xml": "xml",
    }

    return language_map.get(extension, "")


def create_file_context_message(filepath: str, content: str, language: Optional[str] = None) -> str:
    """Create a message with file context.

    Args:
        filepath: Path to the file
        content: File content
        language: Optional language identifier

    Returns:
        Formatted message with file context
    """
    if language is None:
        language = get_language_from_filepath(filepath)

    return f"File: {filepath}\n\n```{language}\n{content}\n```"
