"""Unit tests for tools."""

import pytest
from pathlib import Path
from tools.file_ops import ReadTool, WriteTool, EditTool
from tools.bash import BashTool
from tools.search import GrepTool, GlobTool
from tools.base import ToolStatus


class TestReadTool:
    """Tests for ReadTool."""

    def test_read_existing_file(self, sample_file):
        """Test reading an existing file."""
        tool = ReadTool()
        result = tool.execute(file_path=str(sample_file))

        assert result.status == ToolStatus.SUCCESS
        assert "Hello, World!" in result.output
        assert result.metadata["lines"] == 2

    def test_read_nonexistent_file(self, temp_dir):
        """Test reading a file that doesn't exist."""
        tool = ReadTool()
        result = tool.execute(file_path=str(temp_dir / "nonexistent.txt"))

        assert result.status == ToolStatus.ERROR
        assert "not found" in result.error.lower()

    def test_read_directory(self, temp_dir):
        """Test reading a directory (should fail)."""
        tool = ReadTool()
        result = tool.execute(file_path=str(temp_dir))

        assert result.status == ToolStatus.ERROR
        assert "not a file" in result.error.lower()


class TestWriteTool:
    """Tests for WriteTool."""

    def test_write_new_file(self, temp_dir):
        """Test writing a new file."""
        tool = WriteTool()
        file_path = temp_dir / "new_file.txt"
        content = "Test content"

        result = tool.execute(file_path=str(file_path), content=content)

        assert result.status == ToolStatus.SUCCESS
        assert file_path.exists()
        assert file_path.read_text() == content
        assert result.metadata["overwrite"] is False

    def test_overwrite_existing_file(self, sample_file):
        """Test overwriting an existing file."""
        tool = WriteTool()
        new_content = "New content"

        result = tool.execute(file_path=str(sample_file), content=new_content)

        assert result.status == ToolStatus.SUCCESS
        assert sample_file.read_text() == new_content
        assert result.metadata["overwrite"] is True

    def test_write_creates_parent_dirs(self, temp_dir):
        """Test that write creates parent directories."""
        tool = WriteTool()
        file_path = temp_dir / "subdir" / "file.txt"

        result = tool.execute(file_path=str(file_path), content="test")

        assert result.status == ToolStatus.SUCCESS
        assert file_path.exists()


class TestEditTool:
    """Tests for EditTool."""

    def test_edit_replace_text(self, sample_file):
        """Test replacing text in a file."""
        tool = EditTool()

        result = tool.execute(
            file_path=str(sample_file),
            old_text="Hello",
            new_text="Goodbye"
        )

        assert result.status == ToolStatus.SUCCESS
        assert "Goodbye" in sample_file.read_text()
        assert "Hello" not in sample_file.read_text()

    def test_edit_text_not_found(self, sample_file):
        """Test editing when text is not found."""
        tool = EditTool()

        result = tool.execute(
            file_path=str(sample_file),
            old_text="NonexistentText",
            new_text="Replacement"
        )

        assert result.status == ToolStatus.ERROR
        assert "not found" in result.error.lower()


class TestBashTool:
    """Tests for BashTool."""

    def test_simple_command(self):
        """Test executing a simple command."""
        tool = BashTool()
        result = tool.execute(command="echo 'test'")

        assert result.status == ToolStatus.SUCCESS
        assert "test" in result.output

    def test_command_with_error(self):
        """Test command that exits with error."""
        tool = BashTool()
        result = tool.execute(command="exit 1")

        assert result.status == ToolStatus.ERROR
        assert result.metadata["return_code"] == 1

    def test_working_directory(self, temp_dir):
        """Test command execution in specific directory."""
        tool = BashTool()

        # Create a file in temp_dir
        (temp_dir / "marker.txt").touch()

        # List files in that directory
        result = tool.execute(
            command="ls marker.txt",
            cwd=str(temp_dir)
        )

        assert result.status == ToolStatus.SUCCESS
        assert "marker.txt" in result.output


class TestGrepTool:
    """Tests for GrepTool."""

    def test_grep_finds_pattern(self, sample_file):
        """Test grep finds pattern in file."""
        tool = GrepTool()

        result = tool.execute(
            pattern="Hello",
            path=str(sample_file)
        )

        assert result.status == ToolStatus.SUCCESS
        assert "Hello" in result.output
        assert result.metadata["matches"] == 1

    def test_grep_no_matches(self, sample_file):
        """Test grep with no matches."""
        tool = GrepTool()

        result = tool.execute(
            pattern="NonexistentPattern",
            path=str(sample_file)
        )

        assert result.status == ToolStatus.SUCCESS
        assert result.metadata["matches"] == 0

    def test_grep_case_insensitive(self, sample_file):
        """Test case-insensitive grep."""
        tool = GrepTool()

        result = tool.execute(
            pattern="hello",
            path=str(sample_file),
            case_sensitive=False
        )

        assert result.status == ToolStatus.SUCCESS
        assert result.metadata["matches"] == 1


class TestGlobTool:
    """Tests for GlobTool."""

    def test_glob_finds_files(self, temp_dir):
        """Test glob finds matching files."""
        # Create test files
        (temp_dir / "test1.txt").touch()
        (temp_dir / "test2.txt").touch()
        (temp_dir / "other.md").touch()

        tool = GlobTool()
        result = tool.execute(
            pattern="*.txt",
            cwd=str(temp_dir)
        )

        assert result.status == ToolStatus.SUCCESS
        assert result.metadata["matches"] == 2

    def test_glob_recursive(self, temp_dir):
        """Test recursive glob."""
        # Create nested structure
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        (temp_dir / "root.py").touch()
        (subdir / "nested.py").touch()

        tool = GlobTool()
        result = tool.execute(
            pattern="**/*.py",
            cwd=str(temp_dir)
        )

        assert result.status == ToolStatus.SUCCESS
        assert result.metadata["matches"] == 2


class TestToolValidation:
    """Tests for tool parameter validation."""

    def test_missing_required_parameter(self):
        """Test validation catches missing required parameters."""
        tool = ReadTool()

        is_valid, error = tool.validate_parameters()

        assert not is_valid
        assert "file_path" in error

    def test_valid_parameters(self):
        """Test validation passes with valid parameters."""
        tool = ReadTool()

        is_valid, error = tool.validate_parameters(file_path="/some/path")

        assert is_valid
        assert error is None
