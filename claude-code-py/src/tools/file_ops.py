"""File operation tools (Read, Write, Edit)."""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from .base import BaseTool, ToolResult, ToolStatus


class ReadTool(BaseTool):
    """Tool for reading file contents."""

    def get_name(self) -> str:
        return "read_file"

    def get_aliases(self) -> list[str]:
        """Return aliases for claude.ai compatibility."""
        return ["Read"]

    def get_description(self) -> str:
        return "Read contents of a file. Returns the file contents as text."

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "file_path": {
                "type": "string",
                "description": "Path to the file to read (absolute or relative)"
            }
        }

    def execute(self, file_path: str, **kwargs) -> ToolResult:
        """Read file contents.

        Args:
            file_path: Path to file to read

        Returns:
            ToolResult with file contents
        """
        try:
            # Resolve path (handles relative paths, ~, etc)
            path = Path(file_path).expanduser().resolve()

            # Check if file exists
            if not path.exists():
                return ToolResult(
                    status=ToolStatus.ERROR,
                    output="",
                    error=f"File not found: {path}"
                )

            # Check if it's a file (not directory)
            if not path.is_file():
                return ToolResult(
                    status=ToolStatus.ERROR,
                    output="",
                    error=f"Path is not a file: {path}"
                )

            # Read file contents
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            return ToolResult(
                status=ToolStatus.SUCCESS,
                output=content,
                metadata={
                    "file_path": str(path),
                    "size": len(content),
                    "lines": content.count('\n') + 1
                }
            )

        except PermissionError:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error=f"Permission denied: {file_path}"
            )
        except UnicodeDecodeError:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error=f"File is not a text file or has unsupported encoding: {file_path}"
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error=f"Failed to read file: {str(e)}"
            )


class WriteTool(BaseTool):
    """Tool for writing file contents."""

    def get_name(self) -> str:
        return "write_file"

    def get_aliases(self) -> list[str]:
        """Return aliases for claude.ai compatibility."""
        return ["create_file", "Write"]

    def get_description(self) -> str:
        return "Write content to a file. Creates file if it doesn't exist, overwrites if it does."

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "file_path": {
                "type": "string",
                "description": "Path to the file to write (absolute or relative)"
            },
            "content": {
                "type": "string",
                "description": "Content to write to the file"
            }
        }

    def execute(self, file_path: str, content: str, **kwargs) -> ToolResult:
        """Write content to file.

        Args:
            file_path: Path to file to write
            content: Content to write

        Returns:
            ToolResult with operation status
        """
        try:
            # Resolve path
            path = Path(file_path).expanduser().resolve()

            # Create parent directories if they don't exist
            path.parent.mkdir(parents=True, exist_ok=True)

            # Check if we're overwriting
            is_overwrite = path.exists()

            # Write file
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)

            action = "overwrote" if is_overwrite else "created"

            return ToolResult(
                status=ToolStatus.SUCCESS,
                output=f"Successfully {action} file: {path}",
                metadata={
                    "file_path": str(path),
                    "size": len(content),
                    "lines": content.count('\n') + 1,
                    "overwrite": is_overwrite
                }
            )

        except PermissionError:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error=f"Permission denied: {file_path}"
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error=f"Failed to write file: {str(e)}"
            )


class EditTool(BaseTool):
    """Tool for editing file contents (find and replace)."""

    def get_name(self) -> str:
        return "edit_file"

    def get_aliases(self) -> list[str]:
        """Return aliases for claude.ai compatibility."""
        return ["Edit"]

    def get_description(self) -> str:
        return "Edit a file by replacing old_text with new_text. Finds and replaces text in file."

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "file_path": {
                "type": "string",
                "description": "Path to the file to edit"
            },
            "old_text": {
                "type": "string",
                "description": "Text to find and replace"
            },
            "new_text": {
                "type": "string",
                "description": "Text to replace with"
            }
        }

    def execute(self, file_path: str, old_text: str, new_text: str, **kwargs) -> ToolResult:
        """Edit file by replacing text.

        Args:
            file_path: Path to file to edit
            old_text: Text to find
            new_text: Text to replace with

        Returns:
            ToolResult with operation status
        """
        try:
            # Resolve path
            path = Path(file_path).expanduser().resolve()

            # Check if file exists
            if not path.exists():
                return ToolResult(
                    status=ToolStatus.ERROR,
                    output="",
                    error=f"File not found: {path}"
                )

            # Read current content
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            # Check if old_text exists
            if old_text not in content:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    output="",
                    error=f"Text not found in file: '{old_text[:50]}...'"
                )

            # Count occurrences
            count = content.count(old_text)

            # Replace
            new_content = content.replace(old_text, new_text)

            # Write back
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            return ToolResult(
                status=ToolStatus.SUCCESS,
                output=f"Successfully replaced {count} occurrence(s) in {path}",
                metadata={
                    "file_path": str(path),
                    "replacements": count
                }
            )

        except PermissionError:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error=f"Permission denied: {file_path}"
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error=f"Failed to edit file: {str(e)}"
            )
