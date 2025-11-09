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
        return ["Read", "view"]

    def get_description(self) -> str:
        return "Read contents of a file. Returns the file contents as text."

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "file_path": {
                "type": "string",
                "description": "Path to the file to read (absolute or relative)",
            }
        }

    def execute(self, file_path: str = None, path: str = None, **kwargs) -> ToolResult:
        """Read file contents.

        Args:
            file_path: Path to file to read (or use 'path')
            path: Alternative parameter name for file_path (claude.ai compatibility)

        Returns:
            ToolResult with file contents
        """
        # Map claude.ai parameter names to our names
        if path and not file_path:
            file_path = path

        # Validate required parameter
        if not file_path:
            return ToolResult(
                status=ToolStatus.ERROR, output="", error="Missing required parameter: file_path"
            )

        try:
            print(f"📖 [ReadTool] Executing with file_path='{file_path}'")

            # Map claude.ai virtual paths to local paths
            # Claude.ai uses /mnt/user-data/outputs/ but we're in working directory
            import os

            if file_path.startswith("/mnt/user-data/outputs/"):
                # Extract relative path after /mnt/user-data/outputs/
                relative_path = file_path[len("/mnt/user-data/outputs/") :]
                file_path = os.path.join(os.getcwd(), relative_path)
                print(f"📍 [ReadTool] Mapped claude.ai path to: {file_path}")
            elif file_path == "/mnt/user-data/outputs":
                # User asked about directory - use current working directory
                file_path = os.getcwd()
                print(f"📍 [ReadTool] Mapped claude.ai outputs dir to CWD: {file_path}")

            # Resolve path (handles relative paths, ~, etc)
            resolved_path = Path(file_path).expanduser().resolve()
            print(f"📁 [ReadTool] Resolved to: {resolved_path}")

            # Check if file exists
            if not resolved_path.exists():
                return ToolResult(
                    status=ToolStatus.ERROR,
                    output="",
                    error=f"File not found: {resolved_path}\n\nTip: Make sure the path is correct and the file exists.",
                )

            # Check if it's a directory - if so, list contents instead of error
            if resolved_path.is_dir():
                import os

                try:
                    files = os.listdir(resolved_path)
                    if not files:
                        content = f"Directory is empty: {resolved_path}"
                    else:
                        file_list = "\n".join(f"  - {f}" for f in sorted(files))
                        content = f"This is a directory, not a file.\n\nContents of {resolved_path}:\n{file_list}\n\nTo read a file, specify the full path, e.g.:\n  {os.path.join(resolved_path, files[0])}"

                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        output=content,
                        metadata={"is_directory": True, "file_count": len(files), "files": files},
                    )
                except PermissionError:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        output="",
                        error=f"Permission denied to read directory: {resolved_path}",
                    )

            # Read file contents
            with open(resolved_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            return ToolResult(
                status=ToolStatus.SUCCESS,
                output=content,
                metadata={
                    "file_path": str(resolved_path),
                    "size": len(content),
                    "lines": content.count("\n") + 1,
                },
            )

        except PermissionError:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error=f"Permission denied: {file_path}\n\nTip: Check if you have read permissions for this file.",
            )
        except UnicodeDecodeError:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error=f"File is not a text file or has unsupported encoding: {file_path}\n\nTip: This might be a binary file (image, executable, etc.). Try a different tool or viewer.",
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error=f"Failed to read file: {str(e)}\n\nFile path attempted: {file_path}",
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
                "description": "Path to the file to write (absolute or relative)",
            },
            "content": {"type": "string", "description": "Content to write to the file"},
        }

    def execute(
        self,
        file_path: str = None,
        content: str = None,
        path: str = None,
        file_text: str = None,
        **kwargs,
    ) -> ToolResult:
        """Write content to file.

        Args:
            file_path: Path to file to write (or use 'path')
            content: Content to write (or use 'file_text')
            path: Alternative parameter name for file_path (claude.ai compatibility)
            file_text: Alternative parameter name for content (claude.ai compatibility)

        Returns:
            ToolResult with operation status
        """
        # Map claude.ai parameter names to our names
        if path and not file_path:
            file_path = path
        if file_text and not content:
            content = file_text

        # Validate required parameters
        if not file_path or not content:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error=f"Missing required parameters: file_path={bool(file_path)}, content={bool(content)}",
            )

        try:
            print(
                f"📝 [WriteTool] Executing with file_path='{file_path}', content_len={len(content)}"
            )

            # Map claude.ai virtual paths to local paths
            import os

            if file_path.startswith("/mnt/user-data/outputs/"):
                relative_path = file_path[len("/mnt/user-data/outputs/") :]
                file_path = os.path.join(os.getcwd(), relative_path)
                print(f"📍 [WriteTool] Mapped claude.ai path to: {file_path}")

            # Resolve path
            resolved_path = Path(file_path).expanduser().resolve()
            print(f"📁 [WriteTool] Resolved to: {resolved_path}")

            # Create parent directories if they don't exist
            resolved_path.parent.mkdir(parents=True, exist_ok=True)

            # Check if we're overwriting
            is_overwrite = resolved_path.exists()

            # Write file
            with open(resolved_path, "w", encoding="utf-8") as f:
                f.write(content)

            action = "overwrote" if is_overwrite else "created"

            return ToolResult(
                status=ToolStatus.SUCCESS,
                output=f"Successfully {action} file: {resolved_path}",
                metadata={
                    "file_path": str(resolved_path),
                    "size": len(content),
                    "lines": content.count("\n") + 1,
                    "overwrite": is_overwrite,
                },
            )

        except PermissionError:
            return ToolResult(
                status=ToolStatus.ERROR, output="", error=f"Permission denied: {file_path}"
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR, output="", error=f"Failed to write file: {str(e)}"
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
            "file_path": {"type": "string", "description": "Path to the file to edit"},
            "old_text": {"type": "string", "description": "Text to find and replace"},
            "new_text": {"type": "string", "description": "Text to replace with"},
        }

    def execute(
        self,
        file_path: str = None,
        old_text: str = None,
        new_text: str = None,
        path: str = None,
        **kwargs,
    ) -> ToolResult:
        """Edit file by replacing text.

        Args:
            file_path: Path to file to edit (or use 'path')
            old_text: Text to find
            new_text: Text to replace with
            path: Alternative parameter name for file_path (claude.ai compatibility)

        Returns:
            ToolResult with operation status
        """
        # Map claude.ai parameter names to our names
        if path and not file_path:
            file_path = path

        # Validate required parameters
        if not file_path or old_text is None or new_text is None:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error=f"Missing required parameters: file_path={bool(file_path)}, old_text={old_text is not None}, new_text={new_text is not None}",
            )

        try:
            print(
                f"✏️  [EditTool] Executing with file_path='{file_path}', old_text_len={len(old_text)}, new_text_len={len(new_text)}"
            )

            # Map claude.ai virtual paths to local paths
            import os

            if file_path.startswith("/mnt/user-data/outputs/"):
                relative_path = file_path[len("/mnt/user-data/outputs/") :]
                file_path = os.path.join(os.getcwd(), relative_path)
                print(f"📍 [EditTool] Mapped claude.ai path to: {file_path}")

            # Resolve path
            resolved_path = Path(file_path).expanduser().resolve()
            print(f"📁 [EditTool] Resolved to: {resolved_path}")

            # Check if file exists
            if not resolved_path.exists():
                return ToolResult(
                    status=ToolStatus.ERROR, output="", error=f"File not found: {resolved_path}"
                )

            # Read current content
            with open(resolved_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            # Check if old_text exists
            if old_text not in content:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    output="",
                    error=f"Text not found in file: '{old_text[:50]}...'",
                )

            # Count occurrences
            count = content.count(old_text)

            # Replace
            new_content = content.replace(old_text, new_text)

            # Write back
            with open(resolved_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            return ToolResult(
                status=ToolStatus.SUCCESS,
                output=f"Successfully replaced {count} occurrence(s) in {resolved_path}",
                metadata={"file_path": str(resolved_path), "replacements": count},
            )

        except PermissionError:
            return ToolResult(
                status=ToolStatus.ERROR, output="", error=f"Permission denied: {file_path}"
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR, output="", error=f"Failed to edit file: {str(e)}"
            )
