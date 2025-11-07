"""Search tools (Grep, Glob)."""

import os
import re
import glob as glob_module
from pathlib import Path
from typing import Dict, Any, Optional, List
from .base import BaseTool, ToolResult, ToolStatus


class GrepTool(BaseTool):
    """Tool for searching text in files (like grep)."""

    def get_name(self) -> str:
        return "grep"

    def get_description(self) -> str:
        return "Search for text pattern in files. Supports regex patterns."

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "pattern": {
                "type": "string",
                "description": "Text pattern to search for (supports regex)"
            },
            "path": {
                "type": "string",
                "description": "File or directory to search in"
            },
            "recursive": {
                "type": "boolean",
                "description": "Search recursively in directories (default: false)"
            },
            "case_sensitive": {
                "type": "boolean",
                "description": "Case sensitive search (default: true)"
            }
        }

    def validate_parameters(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate parameters (some are optional)."""
        if "pattern" not in kwargs:
            return False, "Missing required parameter: pattern"
        if "path" not in kwargs:
            return False, "Missing required parameter: path"
        return True, None

    def execute(
        self,
        pattern: str,
        path: str,
        recursive: bool = False,
        case_sensitive: bool = True,
        **kwargs
    ) -> ToolResult:
        """Search for pattern in files.

        Args:
            pattern: Pattern to search for
            path: File or directory to search in
            recursive: Search recursively
            case_sensitive: Case sensitive search

        Returns:
            ToolResult with search results
        """
        try:
            # Compile regex pattern
            flags = 0 if case_sensitive else re.IGNORECASE
            try:
                regex = re.compile(pattern, flags)
            except re.error as e:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    output="",
                    error=f"Invalid regex pattern: {e}"
                )

            # Resolve path
            search_path = Path(path).expanduser().resolve()

            if not search_path.exists():
                return ToolResult(
                    status=ToolStatus.ERROR,
                    output="",
                    error=f"Path not found: {path}"
                )

            # Collect files to search
            files_to_search = []

            if search_path.is_file():
                files_to_search = [search_path]
            elif search_path.is_dir():
                if recursive:
                    # Recursive search
                    for root, dirs, files in os.walk(search_path):
                        for file in files:
                            files_to_search.append(Path(root) / file)
                else:
                    # Non-recursive
                    files_to_search = [f for f in search_path.iterdir() if f.is_file()]
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    output="",
                    error=f"Invalid path: {path}"
                )

            # Search in files
            matches = []
            files_searched = 0
            files_with_matches = 0

            for file_path in files_to_search:
                files_searched += 1
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        for line_num, line in enumerate(f, 1):
                            if regex.search(line):
                                matches.append({
                                    "file": str(file_path),
                                    "line": line_num,
                                    "content": line.rstrip()
                                })
                                if line_num == 1 or matches[-2]["file"] != str(file_path):
                                    files_with_matches += 1
                except Exception:
                    # Skip files that can't be read
                    continue

            # Format output
            if not matches:
                output = f"No matches found for '{pattern}' in {files_searched} file(s)"
            else:
                output_lines = [f"Found {len(matches)} match(es) in {files_with_matches} file(s):\n"]
                for match in matches[:100]:  # Limit to 100 matches
                    output_lines.append(f"{match['file']}:{match['line']}: {match['content']}")

                if len(matches) > 100:
                    output_lines.append(f"\n... and {len(matches) - 100} more matches")

                output = "\n".join(output_lines)

            return ToolResult(
                status=ToolStatus.SUCCESS,
                output=output,
                metadata={
                    "matches": len(matches),
                    "files_searched": files_searched,
                    "files_with_matches": files_with_matches
                }
            )

        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error=f"Search failed: {str(e)}"
            )


class GlobTool(BaseTool):
    """Tool for finding files by pattern (like glob)."""

    def get_name(self) -> str:
        return "glob"

    def get_description(self) -> str:
        return "Find files matching a pattern. Supports wildcards like *, **, ?, [abc], etc."

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "pattern": {
                "type": "string",
                "description": "File pattern to match (e.g., '*.py', '**/*.txt', 'src/**/test_*.py')"
            },
            "cwd": {
                "type": "string",
                "description": "Working directory for pattern matching (default: current directory)"
            }
        }

    def validate_parameters(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate parameters (cwd is optional)."""
        if "pattern" not in kwargs:
            return False, "Missing required parameter: pattern"
        return True, None

    def execute(self, pattern: str, cwd: Optional[str] = None, **kwargs) -> ToolResult:
        """Find files matching pattern.

        Args:
            pattern: Glob pattern to match
            cwd: Working directory

        Returns:
            ToolResult with matching files
        """
        try:
            # Resolve working directory
            if cwd:
                work_dir = Path(cwd).expanduser().resolve()
                if not work_dir.exists() or not work_dir.is_dir():
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        output="",
                        error=f"Invalid working directory: {cwd}"
                    )
            else:
                work_dir = Path.cwd()

            # Change to working directory for glob
            original_cwd = os.getcwd()
            os.chdir(work_dir)

            try:
                # Use glob with recursive support
                if '**' in pattern:
                    matches = glob_module.glob(pattern, recursive=True)
                else:
                    matches = glob_module.glob(pattern)

                # Convert to absolute paths and sort
                matches = sorted([str((work_dir / m).resolve()) for m in matches])

                # Filter out directories if we want only files
                file_matches = [m for m in matches if Path(m).is_file()]

            finally:
                # Restore original working directory
                os.chdir(original_cwd)

            # Format output
            if not file_matches:
                output = f"No files found matching pattern: {pattern}"
            else:
                output_lines = [f"Found {len(file_matches)} file(s) matching '{pattern}':\n"]
                for match in file_matches[:100]:  # Limit to 100 files
                    output_lines.append(match)

                if len(file_matches) > 100:
                    output_lines.append(f"\n... and {len(file_matches) - 100} more files")

                output = "\n".join(output_lines)

            return ToolResult(
                status=ToolStatus.SUCCESS,
                output=output,
                metadata={
                    "matches": len(file_matches),
                    "pattern": pattern,
                    "cwd": str(work_dir)
                }
            )

        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error=f"Glob search failed: {str(e)}"
            )
