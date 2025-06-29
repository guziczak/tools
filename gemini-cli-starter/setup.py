#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Setup script for Gemini CLI Docker image."""

import subprocess
import sys
import os
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass

# Enable BuildKit globally
os.environ['DOCKER_BUILDKIT'] = '1'
os.environ['COMPOSE_DOCKER_CLI_BUILD'] = '1'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'  # Simplified for user-facing output
)
logger = logging.getLogger(__name__)


class BuildTarget(Enum):
    """Build target options."""
    SLIM = "slim"
    FULL = "full"


@dataclass
class SetupConfig:
    """Configuration for setup process."""
    build_target: BuildTarget = BuildTarget.FULL
    no_cache: bool = False
    image_name: str = "gemini-cli-container"
    container_name: str = "gemini-persistent"


class CommandRunner:
    """Handles command execution with proper error handling."""

    @staticmethod
    def run(cmd: str, check: bool = True, show_output: bool = False) -> bool:
        """Execute command with optional output display."""
        try:
            # Force UTF-8 encoding
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'

            # Replace Unix redirections on Windows
            if sys.platform == "win32" and isinstance(cmd, str):
                cmd = cmd.replace(' > /dev/null 2>&1', ' >NUL 2>&1')
                cmd = cmd.replace(' 2>/dev/null', ' 2>NUL')
                cmd = cmd.replace(' >/dev/null', ' >NUL')

            if show_output:
                # For commands where we want to see output
                if sys.platform == "win32":
                    # Hide console window on Windows
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    result = subprocess.run(cmd, shell=True, env=env, startupinfo=startupinfo)
                else:
                    result = subprocess.run(cmd, shell=True, env=env)
                return result.returncode == 0
            else:
                # For silent commands
                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    env=env
                )
                if check and result.returncode != 0:
                    if result.stderr:
                        logger.error(f"Error: {result.stderr}")
                    return False
                return True
        except Exception as e:
            if check:
                logger.error(f"Command execution error: {e}")
            return False

    @staticmethod
    def run_list(cmd: List[str], check: bool = True) -> subprocess.CompletedProcess:
        """Run command as list (safer than shell=True)."""
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'

        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            env=env,
            check=check
        )


class DockerChecker:
    """Checks Docker availability and status."""

    @staticmethod
    def is_docker_running() -> bool:
        """Check if Docker is running."""
        try:
            result = subprocess.run(
                ["docker", "version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    @staticmethod
    def image_exists(image_name: str) -> bool:
        """Check if Docker image exists."""
        result = subprocess.run(
            ["docker", "images", "-q", image_name],
            capture_output=True,
            text=True
        )
        return bool(result.stdout.strip())

    @staticmethod
    def container_exists(container_name: str) -> bool:
        """Check if Docker container exists."""
        result = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )
        return container_name in result.stdout.splitlines()


class ImageSetup:
    """Main setup class for Gemini CLI Docker image."""

    def __init__(self, config: SetupConfig):
        self.config = config
        self.command_runner = CommandRunner()
        self.docker_checker = DockerChecker()

    def run(self) -> None:
        """Run the complete setup process."""
        logger.info("=== Gemini CLI Docker Image Setup ===\n")

        # Check Docker
        if not self._check_docker():
            return

        # Build or check image
        if not self._setup_image():
            return

        # Ensure container exists
        self._ensure_container()

        # Display final instructions
        self._display_instructions()

    def _check_docker(self) -> bool:
        """Check Docker availability."""
        logger.info("Checking Docker...")

        if not self.docker_checker.is_docker_running():
            logger.error("Docker is not installed or not running!")
            logger.error("Please ensure Docker Desktop is running.")
            return False

        logger.info("Docker is running")
        return True

    def _setup_image(self) -> bool:
        """Build or verify Docker image."""
        logger.info("\nChecking Docker image...")

        if self.docker_checker.image_exists(f"{self.config.image_name}:{self.config.build_target.value}"):
            logger.info("Image already exists")
            logger.info("  Tip: To rebuild with new dependencies use:")
            logger.info("       docker compose build --no-cache")
            logger.info("  To build different version, first remove image:")
            logger.info(f"       docker rmi {self.config.image_name}")
            return True

        return self._build_image()

    def _build_image(self) -> bool:
        """Build Docker image with user preferences."""
        logger.info("Building image (first run)...")

        # Get build preferences
        build_target = self._get_build_target()
        use_cache = self._get_cache_preference()

        # Set environment
        os.environ['DOCKER_TARGET'] = build_target.value

        # Build command
        build_cmd = "docker compose build"
        if not use_cache:
            build_cmd += " --no-cache"

        logger.info(f"\nBuilding {build_target.value} image...")
        logger.info("Docker BuildKit enabled for faster builds!")

        start_time = time.time()
        success = self.command_runner.run(build_cmd, show_output=True)

        if success:
            build_time = time.time() - start_time
            logger.info(f"\nBuild completed in {build_time:.0f} seconds ({build_time/60:.1f} minutes)")
        else:
            logger.error("Build failed!")

        return success

    def _ensure_container(self) -> None:
        """Ensure persistent container exists."""
        logger.info("\nChecking persistent container...")

        if self.docker_checker.container_exists(self.config.container_name):
            logger.info("Persistent container already exists")
        else:
            logger.info("Creating persistent container...")
            # Container will be created on first run of gemini.py
            logger.info("Container will be created on first Gemini session")

    def _get_build_target(self) -> BuildTarget:
        """Get build target from user."""
        logger.info("\n  Choose version:")
        logger.info("  1. Slim (Gemini CLI + Java/Maven) ~800MB")
        logger.info("  2. Full (all tools) ~3GB")

        choice = input("\nChoice (1-2) [2]: ").strip() or "2"

        if choice == "1":
            return BuildTarget.SLIM
        else:
            return BuildTarget.FULL

    def _get_cache_preference(self) -> bool:
        """Get cache preference from user."""
        logger.info("\n  Build options:")
        logger.info("  1. Normal (with cache) - faster")
        logger.info("  2. Full (--no-cache) - fresh packages")

        choice = input("\nChoice (1-2) [1]: ").strip() or "1"
        return choice == "1"

    def _display_instructions(self) -> None:
        """Display final setup instructions."""
        # Get script paths
        current_dir = Path(__file__).parent
        gemini_py_path = current_dir / "gemini.py"

        logger.info("\nImage built successfully!")
        logger.info("\n=== 🚀 Gemini CLI Container Architecture ===")
        logger.info("Gemini CLI uses a single persistent container where:")
        logger.info("  ✅ System packages (apt-get) are shared between sessions")
        logger.info("  ✅ Each project is isolated and sees only its own files")
        logger.info("  ✅ Tools installed in one session are available in all")
        logger.info("  ✅ FREE access to Gemini 2.5 Pro (1000 requests/day)")

        logger.info("\nIntelliJ IDEA Configuration:")
        logger.info("1. Settings -> Tools -> Terminal")
        logger.info("2. In 'Shell path' enter:\n")

        # Quote path if it contains spaces
        if ' ' in str(gemini_py_path):
            logger.info(f'   python "{gemini_py_path}"\n')
        else:
            logger.info(f"   python {gemini_py_path}\n")

        logger.info("3. OK -> new terminal")

        logger.info("\nUsage:")
        logger.info(f"  python {gemini_py_path}              # Run Gemini CLI in current directory")
        logger.info(f"  python {gemini_py_path} [command]    # With arguments")

        logger.info("\n✅ Project Isolation:")
        logger.info("  - Each Gemini session sees ONLY the current project directory")
        logger.info("  - Other projects on disk are completely hidden")
        logger.info("  - Full sudo access for installing tools as needed")
        logger.info("  - Installed tools persist and are shared between all sessions")

        # Display available tools based on version
        self._display_available_tools()

        logger.info("\nDocker volumes:")
        logger.info("  - gemini-shared-tools: User-installed packages")
        logger.info("  - gemini-apt-cache: APT package cache")
        logger.info("  - gemini-usr-local: System-wide installations")
        logger.info("  - gemini-node-modules: Node.js global packages")
        logger.info("  - Project directory: Mounted isolated in container")

        logger.info("\n🆓 FREE Gemini 2.5 Pro Features:")
        logger.info("  - 1 million token context window")
        logger.info("  - 60 requests per minute")
        logger.info("  - 1000 requests per day")
        logger.info("  - Google Search integration")
        logger.info("  - Model Context Protocol (MCP) support")

        logger.info("\nReady to use! Just run gemini.py from any project directory.")

    def _display_available_tools(self) -> None:
        """Display available tools based on build target."""
        # Check which version was built
        result = self.command_runner.run_list([
            "docker", "images", f"{self.config.image_name}",
            "--format", "{{.Tag}}"
        ])

        version = "full"  # default
        if "slim" in result.stdout:
            version = "slim"

        if version == "slim":
            logger.info("\n📦 SLIM Version - Available tools:")
            logger.info("  - Node.js 20 + npm")
            logger.info("  - Python 3 + pip (requests, beautifulsoup4, google-generativeai)")
            logger.info("  - Java 17 (OpenJDK) + Maven")
            logger.info("  - Git, vim, nano")
            logger.info("  - Sudo (full access)")
        else:
            logger.info("\n📦 FULL Version - Available tools:")
            logger.info("  Programming languages:")
            logger.info("  - Node.js 20 + npm")
            logger.info("  - Python 3 + pip")
            logger.info("  - Java 17 (OpenJDK) + Maven + Gradle")
            logger.info("  - Ruby")
            logger.info("  - PHP + Composer")
            logger.info("\n  Development tools:")
            logger.info("  - Git, vim, nano")
            logger.info("  - ripgrep, fd-find, fzf")
            logger.info("  - Docker CLI")
            logger.info("  - shellcheck")
            logger.info("\n  Python libraries:")
            logger.info("  - google-generativeai (official Gemini SDK)")
            logger.info("  - fastapi, uvicorn")
            logger.info("  - beautifulsoup4, requests, pytest, black")
            logger.info("  - pyyaml, lxml, rich")
            logger.info("\n  Other:")
            logger.info("  - ImageMagick, ffmpeg")
            logger.info("  - SQLite3, PostgreSQL/MySQL clients")
            logger.info("  - tmux, screen")


def main() -> None:
    """Main entry point."""
    try:
        config = SetupConfig()
        setup = ImageSetup(config)
        setup.run()
    except KeyboardInterrupt:
        logger.info("\nSetup interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()