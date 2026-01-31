"""Platform and shell detection as an immutable value object."""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class PlatformInfo:
    """Immutable platform and shell information.

    Single source of truth for OS/shell detection.
    Consumed by system prompt builder and BashTool.
    """

    os_name: str
    shell_type: str
    shell_name: str
    shell_command: tuple  # frozen — must be hashable

    @classmethod
    def detect(cls) -> PlatformInfo:
        """Auto-detect current platform and preferred shell."""
        if sys.platform.startswith("win"):
            return cls._detect_windows()
        return cls._detect_unix()

    @classmethod
    def _detect_windows(cls) -> PlatformInfo:
        if shutil.which("pwsh"):
            return cls(
                os_name="Windows",
                shell_type="powershell",
                shell_name="PowerShell Core",
                shell_command=("pwsh", "-Command"),
            )
        if shutil.which("powershell"):
            return cls(
                os_name="Windows",
                shell_type="powershell",
                shell_name="PowerShell",
                shell_command=("powershell", "-Command"),
            )
        return cls(
            os_name="Windows",
            shell_type="cmd",
            shell_name="CMD",
            shell_command=("cmd", "/c"),
        )

    @classmethod
    def _detect_unix(cls) -> PlatformInfo:
        return cls(
            os_name="macOS" if sys.platform == "darwin" else "Linux",
            shell_type="bash",
            shell_name="Bash",
            shell_command=("/bin/bash", "-c"),
        )

    @property
    def is_windows(self) -> bool:
        return self.os_name == "Windows"

    @property
    def is_powershell(self) -> bool:
        return self.shell_type == "powershell"

    def shell_hint_for_prompt(self) -> str:
        """Return a shell hint string for inclusion in system prompts."""
        if self.is_powershell:
            return (
                f"Shell: {self.shell_name}. "
                "Use PowerShell cmdlets (Get-ChildItem, Get-Content, Select-String), "
                "not CMD commands (dir, type, findstr)."
            )
        return f"Shell: {self.shell_name}."
