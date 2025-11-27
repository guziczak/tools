"""File Operations Manager.

Provides utilities for reading, writing, and manipulating files
with proper error handling and security considerations.

Based on the TypeScript implementation from claude-code-source-code-deobfuscation-main.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List
import os

logger = logging.getLogger(__name__)


@dataclass
class FileOperationResult:
    """Result of a file operation."""

    success: bool
    error: Optional[Exception] = None
    path: Optional[str] = None
    content: Optional[str] = None
    created: bool = False
    files: Optional[List[str]] = None


class FileOperationsManager:
    """Manager for file operations with security features."""

    def __init__(self, workspace_path: Optional[str] = None, max_read_size_bytes: int = 10 * 1024 * 1024):
        """Initialize file operations manager.

        Args:
            workspace_path: Root workspace directory (defaults to cwd)
            max_read_size_bytes: Maximum file size to read (default: 10MB)
        """
        self.workspace_path = Path(workspace_path or os.getcwd()).resolve()
        self.max_read_size_bytes = max_read_size_bytes

        logger.debug(f"File operations manager created with workspace: {self.workspace_path}")

    def initialize(self) -> None:
        """Initialize and verify workspace.

        Raises:
            ValueError: If workspace is invalid
        """
        logger.info("Initializing file operations manager")

        if not self.workspace_path.exists():
            raise ValueError(f"Workspace directory does not exist: {self.workspace_path}")

        if not self.workspace_path.is_dir():
            raise ValueError(f"Workspace path is not a directory: {self.workspace_path}")

        logger.info("File operations manager initialized")

    def get_absolute_path(self, relative_path: str) -> Path:
        """Get absolute path relative to workspace.

        This prevents directory traversal attacks by ensuring the path
        stays within the workspace directory.

        Args:
            relative_path: Relative path from workspace

        Returns:
            Absolute path within workspace

        Raises:
            ValueError: If path escapes workspace
        """
        # Resolve the path
        try:
            # Handle both relative and absolute paths
            if Path(relative_path).is_absolute():
                absolute_path = Path(relative_path).resolve()
            else:
                absolute_path = (self.workspace_path / relative_path).resolve()
        except (ValueError, OSError) as e:
            raise ValueError(f"Invalid path: {relative_path}") from e

        # Security check: ensure path is within workspace
        try:
            absolute_path.relative_to(self.workspace_path)
        except ValueError:
            raise ValueError(
                f"Access denied: Path '{relative_path}' is outside workspace '{self.workspace_path}'"
            )

        return absolute_path

    def get_relative_path(self, absolute_path: str) -> str:
        """Get relative path from workspace.

        Args:
            absolute_path: Absolute file path

        Returns:
            Relative path from workspace
        """
        abs_path = Path(absolute_path).resolve()
        try:
            return str(abs_path.relative_to(self.workspace_path))
        except ValueError:
            # Path is outside workspace, return as-is
            return str(abs_path)

    def read_file(self, file_path: str) -> FileOperationResult:
        """Read a file.

        Args:
            file_path: Path to file (relative or absolute)

        Returns:
            FileOperationResult with file content or error
        """
        try:
            absolute_path = self.get_absolute_path(file_path)

            logger.debug(f"Reading file: {file_path} -> {absolute_path}")

            # Verify file exists
            if not absolute_path.exists():
                return FileOperationResult(
                    success=False,
                    error=FileNotFoundError(f"File not found: {file_path}"),
                )

            # Verify it's a file
            if not absolute_path.is_file():
                return FileOperationResult(
                    success=False,
                    error=ValueError(f"Not a file: {file_path}"),
                )

            # Check file size
            file_size = absolute_path.stat().st_size
            if file_size > self.max_read_size_bytes:
                return FileOperationResult(
                    success=False,
                    error=ValueError(
                        f"File too large to read: {file_path} "
                        f"({file_size} bytes, max: {self.max_read_size_bytes})"
                    ),
                )

            # Read file content
            content = absolute_path.read_text(encoding="utf-8", errors="replace")

            return FileOperationResult(
                success=True,
                path=file_path,
                content=content,
            )

        except PermissionError as e:
            logger.error(f"Permission denied reading file: {file_path}")
            return FileOperationResult(
                success=False,
                error=PermissionError(f"Permission denied reading file: {file_path}"),
            )

        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return FileOperationResult(
                success=False,
                error=e,
            )

    def write_file(self, file_path: str, content: str, create_dirs: bool = False) -> FileOperationResult:
        """Write a file.

        Args:
            file_path: Path to file (relative or absolute)
            content: File content to write
            create_dirs: Whether to create parent directories

        Returns:
            FileOperationResult indicating success or failure
        """
        try:
            absolute_path = self.get_absolute_path(file_path)

            logger.debug(f"Writing file: {file_path} -> {absolute_path} (length: {len(content)})")

            # Check if file exists
            is_creating = not absolute_path.exists()

            # Create parent directories if requested
            if create_dirs and not absolute_path.parent.exists():
                absolute_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file content
            absolute_path.write_text(content, encoding="utf-8")

            return FileOperationResult(
                success=True,
                path=file_path,
                created=is_creating,
            )

        except PermissionError:
            logger.error(f"Permission denied writing file: {file_path}")
            return FileOperationResult(
                success=False,
                error=PermissionError(f"Permission denied writing file: {file_path}"),
            )

        except FileNotFoundError:
            logger.error(f"Directory does not exist: {Path(file_path).parent}")
            return FileOperationResult(
                success=False,
                error=FileNotFoundError(
                    f"Directory does not exist: {Path(file_path).parent}. "
                    f"Use create_dirs=True to create parent directories."
                ),
            )

        except Exception as e:
            logger.error(f"Error writing file {file_path}: {e}")
            return FileOperationResult(
                success=False,
                error=e,
            )

    def delete_file(self, file_path: str) -> FileOperationResult:
        """Delete a file.

        Args:
            file_path: Path to file (relative or absolute)

        Returns:
            FileOperationResult indicating success or failure
        """
        try:
            absolute_path = self.get_absolute_path(file_path)

            logger.debug(f"Deleting file: {file_path} -> {absolute_path}")

            # Verify file exists
            if not absolute_path.exists():
                return FileOperationResult(
                    success=False,
                    error=FileNotFoundError(f"File not found: {file_path}"),
                )

            # Verify it's a file
            if not absolute_path.is_file():
                return FileOperationResult(
                    success=False,
                    error=ValueError(f"Not a file: {file_path}"),
                )

            # Delete file
            absolute_path.unlink()

            return FileOperationResult(
                success=True,
                path=file_path,
            )

        except PermissionError:
            logger.error(f"Permission denied deleting file: {file_path}")
            return FileOperationResult(
                success=False,
                error=PermissionError(f"Permission denied deleting file: {file_path}"),
            )

        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {e}")
            return FileOperationResult(
                success=False,
                error=e,
            )

    def file_exists(self, file_path: str) -> bool:
        """Check if a file exists.

        Args:
            file_path: Path to file (relative or absolute)

        Returns:
            True if file exists, False otherwise
        """
        try:
            absolute_path = self.get_absolute_path(file_path)
            return absolute_path.exists() and absolute_path.is_file()
        except Exception:
            return False

    def create_directory(self, dir_path: str, recursive: bool = True) -> FileOperationResult:
        """Create a directory.

        Args:
            dir_path: Path to directory (relative or absolute)
            recursive: Whether to create parent directories

        Returns:
            FileOperationResult indicating success or failure
        """
        try:
            absolute_path = self.get_absolute_path(dir_path)

            logger.debug(f"Creating directory: {dir_path} -> {absolute_path} (recursive: {recursive})")

            # Create directory
            absolute_path.mkdir(parents=recursive, exist_ok=False)

            return FileOperationResult(
                success=True,
                path=dir_path,
            )

        except FileExistsError:
            logger.error(f"Directory already exists: {dir_path}")
            return FileOperationResult(
                success=False,
                error=FileExistsError(f"Directory already exists: {dir_path}"),
            )

        except PermissionError:
            logger.error(f"Permission denied creating directory: {dir_path}")
            return FileOperationResult(
                success=False,
                error=PermissionError(f"Permission denied creating directory: {dir_path}"),
            )

        except Exception as e:
            logger.error(f"Error creating directory {dir_path}: {e}")
            return FileOperationResult(
                success=False,
                error=e,
            )

    def list_directory(self, dir_path: str) -> FileOperationResult:
        """List directory contents.

        Args:
            dir_path: Path to directory (relative or absolute)

        Returns:
            FileOperationResult with list of files or error
        """
        try:
            absolute_path = self.get_absolute_path(dir_path)

            logger.debug(f"Listing directory: {dir_path} -> {absolute_path}")

            # Verify directory exists
            if not absolute_path.exists():
                return FileOperationResult(
                    success=False,
                    error=FileNotFoundError(f"Directory not found: {dir_path}"),
                )

            # Verify it's a directory
            if not absolute_path.is_dir():
                return FileOperationResult(
                    success=False,
                    error=ValueError(f"Not a directory: {dir_path}"),
                )

            # List directory contents
            files = [entry.name for entry in absolute_path.iterdir()]

            return FileOperationResult(
                success=True,
                path=dir_path,
                files=files,
            )

        except PermissionError:
            logger.error(f"Permission denied listing directory: {dir_path}")
            return FileOperationResult(
                success=False,
                error=PermissionError(f"Permission denied listing directory: {dir_path}"),
            )

        except Exception as e:
            logger.error(f"Error listing directory {dir_path}: {e}")
            return FileOperationResult(
                success=False,
                error=e,
            )

    def generate_diff(self, original: str, modified: str) -> str:
        """Generate a simple line-by-line diff.

        Args:
            original: Original content
            modified: Modified content

        Returns:
            Diff string with + for additions, - for deletions
        """
        original_lines = original.splitlines()
        modified_lines = modified.splitlines()

        diff_lines = []
        i, j = 0, 0

        while i < len(original_lines) or j < len(modified_lines):
            if i >= len(original_lines):
                # Remaining lines are additions
                diff_lines.append(f"+ {modified_lines[j]}")
                j += 1
            elif j >= len(modified_lines):
                # Remaining lines are deletions
                diff_lines.append(f"- {original_lines[i]}")
                i += 1
            elif original_lines[i] == modified_lines[j]:
                # Lines are the same
                diff_lines.append(f"  {original_lines[i]}")
                i += 1
                j += 1
            else:
                # Lines differ
                diff_lines.append(f"- {original_lines[i]}")
                diff_lines.append(f"+ {modified_lines[j]}")
                i += 1
                j += 1

        return "\n".join(diff_lines)


def init_file_operations(workspace_path: Optional[str] = None, max_read_size_bytes: int = 10 * 1024 * 1024) -> FileOperationsManager:
    """Initialize the file operations system.

    Args:
        workspace_path: Root workspace directory (defaults to cwd)
        max_read_size_bytes: Maximum file size to read (default: 10MB)

    Returns:
        Initialized FileOperationsManager

    Raises:
        ValueError: If initialization fails
    """
    logger.info("Initializing file operations system")

    try:
        file_ops = FileOperationsManager(workspace_path, max_read_size_bytes)
        file_ops.initialize()

        logger.info("File operations system initialized successfully")

        return file_ops

    except Exception as e:
        logger.error(f"Failed to initialize file operations system: {e}")
        # Return a basic manager even if initialization failed
        return FileOperationsManager(workspace_path, max_read_size_bytes)
