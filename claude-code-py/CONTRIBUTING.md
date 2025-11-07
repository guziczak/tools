# Contributing to Claude Code Python

Thank you for considering contributing! This document outlines the development workflow and best practices.

## Development Setup

### 1. Clone and Install

```bash
git clone <repository-url>
cd claude-code-py

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
make install-dev
```

### 2. Set up Pre-commit Hooks

```bash
pre-commit install
```

This will automatically run linters and formatters before each commit.

## Development Workflow

### Running Tests

```bash
# All tests
make test

# Unit tests only (fast)
make test-unit

# Integration tests only
make test-integration

# Watch mode (re-run on file changes)
make test-watch

# Coverage report
make coverage
make coverage-open  # Open HTML report
```

### Code Quality

```bash
# Format code
make format

# Run linters
make lint

# Type checking
make type-check

# Security checks
make security

# Run all quality checks
make lint && make type-check && make security
```

### Before Committing

```bash
# Format, lint, and test
make format
make lint
make test

# Or use pre-commit
make pre-commit
```

## Code Standards

### 1. **Type Hints**

All functions should have type hints:

```python
from typing import Optional, List, Dict, Any

def process_data(
    input_data: str,
    config: Optional[Dict[str, Any]] = None
) -> List[str]:
    """Process input data.

    Args:
        input_data: The data to process
        config: Optional configuration dict

    Returns:
        List of processed strings
    """
    pass
```

### 2. **Docstrings**

Use Google-style docstrings:

```python
def calculate_result(x: int, y: int) -> int:
    """Calculate the sum of two numbers.

    Args:
        x: First number
        y: Second number

    Returns:
        The sum of x and y

    Raises:
        ValueError: If inputs are negative
    """
    if x < 0 or y < 0:
        raise ValueError("Inputs must be non-negative")
    return x + y
```

### 3. **Testing**

- Write tests for all new features
- Aim for >80% code coverage
- Use descriptive test names

```python
def test_read_tool_handles_nonexistent_file():
    """Test that ReadTool returns error for nonexistent file."""
    tool = ReadTool()
    result = tool.execute(file_path="/nonexistent.txt")

    assert result.status == ToolStatus.ERROR
    assert "not found" in result.error.lower()
```

### 4. **Logging**

Use structured logging:

```python
from utils.logging import get_logger

logger = get_logger(__name__)

def process_request(request_id: str):
    logger.info("Processing request", extra={"request_id": request_id})
    try:
        # ... do work
        logger.debug("Request processed successfully")
    except Exception as e:
        logger.error("Request failed", exc_info=True, extra={"request_id": request_id})
```

### 5. **Error Handling**

Use specific exceptions and provide context:

```python
class ToolExecutionError(Exception):
    """Raised when tool execution fails."""
    pass

def execute_tool(tool_name: str):
    try:
        # ... execute tool
        pass
    except FileNotFoundError as e:
        raise ToolExecutionError(f"Tool '{tool_name}' failed: {e}") from e
```

## Project Structure

```
claude-code-py/
├── src/                    # Source code
│   ├── core/              # Core functionality
│   ├── tools/             # Tool implementations
│   ├── ui/                # User interface
│   └── utils/             # Utility functions
├── tests/                 # Tests
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   ├── e2e/              # End-to-end tests
│   └── fixtures/         # Test fixtures
├── docs/                  # Documentation
└── .github/              # GitHub Actions workflows
```

## Pull Request Process

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write code
   - Add tests
   - Update documentation

3. **Run quality checks**
   ```bash
   make format
   make lint
   make test
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "Add feature: description"
   ```

5. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Wait for CI checks**
   - All tests must pass
   - Code coverage must not decrease
   - All linters must pass

## Commit Messages

Follow conventional commits:

```
feat: Add new search tool
fix: Handle edge case in file reading
docs: Update README with examples
test: Add tests for bash tool
refactor: Simplify error handling
chore: Update dependencies
```

## Questions?

Open an issue or start a discussion on GitHub!
