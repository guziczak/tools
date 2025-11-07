"""Pytest configuration and shared fixtures."""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock
import tempfile
import shutil

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp = tempfile.mkdtemp()
    yield Path(temp)
    shutil.rmtree(temp)


@pytest.fixture
def sample_file(temp_dir):
    """Create a sample file for testing."""
    file_path = temp_dir / "test.txt"
    file_path.write_text("Hello, World!\nThis is a test.")
    return file_path


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client for testing."""
    mock_client = Mock()

    # Mock streaming response
    mock_stream = MagicMock()
    mock_stream.__enter__ = Mock(return_value=mock_stream)
    mock_stream.__exit__ = Mock(return_value=False)

    mock_client.messages.stream.return_value = mock_stream

    return mock_client


@pytest.fixture
def mock_console():
    """Mock Rich console for UI testing."""
    from unittest.mock import Mock
    console = Mock()
    console.print = Mock()
    return console


@pytest.fixture
def tool_registry():
    """Create a tool registry with default tools."""
    from tools import create_default_registry
    return create_default_registry()
