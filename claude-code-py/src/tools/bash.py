"""Bash/shell command execution tool (cross-platform)."""

import sys
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from .base import BaseTool, ToolResult, ToolStatus


class BashTool(BaseTool):
    """Tool for executing shell commands (cross-platform)."""

    def __init__(self):
        """Initialize Bash tool with platform detection."""
        self._detect_shell()  # Must be called BEFORE super().__init__()
        super().__init__()

    def _detect_shell(self):
        """Detect available shell based on platform."""
        self.platform = sys.platform
        self.is_windows = self.platform.startswith("win")

        if self.is_windows:
            # Windows: prefer PowerShell, fallback to cmd
            if shutil.which("pwsh"):  # PowerShell Core
                self.shell = ["pwsh", "-Command"]
                self.shell_name = "PowerShell Core"
            elif shutil.which("powershell"):  # Windows PowerShell
                self.shell = ["powershell", "-Command"]
                self.shell_name = "PowerShell"
            else:  # CMD fallback
                self.shell = ["cmd", "/c"]
                self.shell_name = "CMD"
        else:
            # Linux/Mac: use bash
            self.shell = ["/bin/bash", "-c"]
            self.shell_name = "Bash"

    def get_name(self) -> str:
        return "bash"

    def get_aliases(self) -> list[str]:
        """Return aliases for claude.ai compatibility."""
        return ["bash_tool", "Bash"]

    def get_description(self) -> str:
        if self.is_windows:
            return f"Execute a shell command using {self.shell_name}. Commands are executed in {self.shell_name} environment."
        else:
            return "Execute a bash command. Commands are executed in a bash shell."

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "command": {"type": "string", "description": "The shell command to execute"},
            "cwd": {
                "type": "string",
                "description": "Working directory for command execution (optional)",
            },
        }

    def validate_parameters(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate parameters (cwd is optional)."""
        if "command" not in kwargs:
            return False, "Missing required parameter: command"
        return True, None

    def execute(
        self, command: str, cwd: Optional[str] = None, description: Optional[str] = None, **kwargs
    ) -> ToolResult:
        """Execute shell command.

        Args:
            command: Shell command to execute
            cwd: Working directory (optional)
            description: Description of what this command does (optional, ignored - for claude.ai compatibility)

        Returns:
            ToolResult with command output
        """
        # Ignore description parameter (claude.ai sends it, but we don't need it)
        try:
            # Prepare working directory
            work_dir = None
            if cwd:
                work_dir = Path(cwd).expanduser().resolve()
                if not work_dir.exists() or not work_dir.is_dir():
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        output="",
                        error=f"Invalid working directory: {cwd}",
                    )

            # Build command based on platform
            # On Windows, prepend chcp 65001 to force UTF-8 encoding
            if sys.platform == "win32":
                # Wrap command to set UTF-8 codepage
                command = f"chcp 65001 > nul && {command}"

            full_command = self.shell + [command]

            # Execute command
            result = subprocess.run(
                full_command,
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=30,  # 30 second timeout
                encoding="utf-8",
                errors="replace",
            )

            # Combine stdout and stderr
            output = result.stdout
            if result.stderr:
                output += f"\n[stderr]\n{result.stderr}"

            # Determine status
            if result.returncode == 0:
                status = ToolStatus.SUCCESS
                error = None
            else:
                status = ToolStatus.ERROR
                error = f"Command exited with code {result.returncode}"

            return ToolResult(
                status=status,
                output=output.strip() if output else "(no output)",
                error=error,
                metadata={
                    "return_code": result.returncode,
                    "shell": self.shell_name,
                    "cwd": str(work_dir) if work_dir else None,
                },
            )

        except subprocess.TimeoutExpired:
            return ToolResult(
                status=ToolStatus.ERROR, output="", error="Command timed out (30 second limit)"
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR, output="", error=f"Command execution failed: {str(e)}"
            )


class BashInteractiveTool(BaseTool):
    """Tool for executing commands that might need user interaction (advanced)."""

    def __init__(self):
        """Initialize interactive bash tool."""
        super().__init__()
        self.bash_tool = BashTool()

    def get_name(self) -> str:
        return "bash_interactive"

    def get_description(self) -> str:
        return "Execute an interactive shell command that may require user input."

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "command": {"type": "string", "description": "The shell command to execute"},
            "input": {"type": "string", "description": "Input to send to the command (optional)"},
        }

    def validate_parameters(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate parameters (input is optional)."""
        if "command" not in kwargs:
            return False, "Missing required parameter: command"
        return True, None

    def execute(self, command: str, input: Optional[str] = None, **kwargs) -> ToolResult:
        """Execute interactive command.

        Args:
            command: Shell command to execute
            input: Input to send to command

        Returns:
            ToolResult with command output
        """
        try:
            # On Windows, prepend chcp 65001 to force UTF-8 encoding
            if sys.platform == "win32":
                command = f"chcp 65001 > nul && {command}"

            full_command = self.bash_tool.shell + [command]

            # Execute with input
            result = subprocess.run(
                full_command,
                input=input,
                capture_output=True,
                text=True,
                timeout=30,
                encoding="utf-8",
                errors="replace",
            )

            output = result.stdout
            if result.stderr:
                output += f"\n[stderr]\n{result.stderr}"

            status = ToolStatus.SUCCESS if result.returncode == 0 else ToolStatus.ERROR
            error = (
                None if result.returncode == 0 else f"Command exited with code {result.returncode}"
            )

            return ToolResult(
                status=status,
                output=output.strip() if output else "(no output)",
                error=error,
                metadata={"return_code": result.returncode, "shell": self.bash_tool.shell_name},
            )

        except subprocess.TimeoutExpired:
            return ToolResult(
                status=ToolStatus.ERROR, output="", error="Command timed out (30 second limit)"
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR, output="", error=f"Command execution failed: {str(e)}"
            )
