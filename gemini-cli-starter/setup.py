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


@dataclass
class SetupConfig:
    """Configuration for setup process."""
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
            logger.error("Please ensure Docker Desktop or Rancher Desktop is running.")
            return False

        logger.info("Docker is running")

        # Check Docker backend (WSL vs Hyper-V) on Windows
        if sys.platform == "win32":
            if not self._check_docker_backend():
                return False

        return True

    def _check_docker_backend(self) -> bool:
        """Check if Docker is using WSL 2 instead of Hyper-V (Windows only)."""
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                timeout=10
            )
            docker_info = result.stdout + result.stderr

            # Check for Hyper-V indicators
            is_hyperv = any(indicator in docker_info for indicator in [
                "Operating System: Docker Desktop",
                "Hyper-V",
                "hyperv"
            ])

            # Check for WSL indicators
            is_wsl = any(indicator in docker_info for indicator in [
                "WSL",
                "rancher-desktop",
                "Rancher Desktop"
            ])

            if is_hyperv and not is_wsl:
                logger.warning("\n⚠️  Docker is using Hyper-V instead of WSL 2!")
                logger.warning("   This may cause performance issues and connection errors.\n")
                logger.info("   To fix, switch to WSL 2 backend:")
                logger.info("   - Docker Desktop: Settings → General → Use WSL 2 based engine")
                logger.info("   - Rancher Desktop: Settings → Virtual Machine → Type: WSL")
                logger.info("")

                response = input("Continue anyway? (y/n) [n]: ").strip().lower()
                if response != 'y':
                    logger.info("Setup cancelled. Please switch to WSL 2 and try again.")
                    return False

            elif is_wsl:
                logger.info("Docker backend: WSL 2 ✓")

            return True

        except Exception as e:
            logger.warning(f"Could not determine Docker backend: {e}")
            return True  # Continue anyway

    def _setup_image(self) -> bool:
        """Build or verify Docker image."""
        logger.info("\nChecking Docker image...")

        if self.docker_checker.image_exists(f"{self.config.image_name}:latest"):
            logger.info("Image already exists")
            logger.info("  Tip: To rebuild with new dependencies use:")
            logger.info("       docker compose build --no-cache")
            logger.info("  To remove and rebuild image:")
            logger.info(f"       docker rmi {self.config.image_name}:latest")
            return True

        return self._build_image()

    def _build_image(self) -> bool:
        """Build Docker image with user preferences."""
        logger.info("Building image (first run)...")

        # Get build preferences
        use_cache = self._get_cache_preference()

        # Build command
        build_cmd = "docker compose build"
        if not use_cache:
            build_cmd += " --no-cache"

        logger.info("\nBuilding full image...")
        logger.info("Docker BuildKit enabled for faster builds!")

        start_time = time.time()
        success = self.command_runner.run(build_cmd, show_output=True)

        if success:
            build_time = time.time() - start_time
            logger.info(f"\nBuild completed in {build_time:.0f} seconds ({build_time/60:.1f} minutes)")

            # Verify image was actually created
            logger.info("\nVerifying image...")
            if not self._verify_image_exists():
                return False
        else:
            logger.error("Build failed!")

        return success

    def _verify_image_exists(self) -> bool:
        """Verify that the image was created successfully."""
        image_name = f"{self.config.image_name}:latest"

        # Try multiple times with delay (Docker may need time to register)
        for attempt in range(5):
            if self.docker_checker.image_exists(image_name):
                logger.info(f"✓ Image verified: {image_name}")

                # Show image details
                result = subprocess.run(
                    ["docker", "images", image_name, "--format", "ID: {{.ID}} | Size: {{.Size}} | Created: {{.CreatedSince}}"],
                    capture_output=True,
                    text=True
                )
                if result.stdout.strip():
                    logger.info(f"  {result.stdout.strip()}")
                return True

            if attempt < 4:
                logger.info(f"  Waiting for image registration... (attempt {attempt + 1}/5)")
                time.sleep(2)

        # Image not found - show diagnostic info
        logger.error(f"\n✗ Image '{image_name}' not found after build!")
        logger.info("\nDiagnostic information:")

        # List all images
        result = subprocess.run(
            ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"],
            capture_output=True,
            text=True
        )
        if result.stdout.strip():
            logger.info("Available images:")
            for img in result.stdout.strip().split('\n')[:10]:
                logger.info(f"  - {img}")

        # Check docker info
        result = subprocess.run(
            ["docker", "info", "--format", "{{.Driver}}"],
            capture_output=True,
            text=True
        )
        if result.stdout.strip():
            logger.info(f"Docker storage driver: {result.stdout.strip()}")

        return False

    def _ensure_container(self) -> None:
        """Ensure persistent container exists."""
        logger.info("\nChecking persistent container...")

        if self.docker_checker.container_exists(self.config.container_name):
            logger.info("Persistent container already exists")
        else:
            logger.info("Creating persistent container...")
            # Container will be created on first run of gemini.py
            logger.info("Container will be created on first Gemini session")

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
        logger.info("\n=== Persistent Container Architecture ===")
        logger.info("Gemini CLI uses a single persistent container where:")
        logger.info("  - System packages (apt-get) are shared between sessions")
        logger.info("  - Each project is isolated and sees only its own files")
        logger.info("  - Tools installed in one session are available in all")

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

        logger.info("\nProject Isolation:")
        logger.info("  - Each Gemini session sees ONLY the current project directory")
        logger.info("  - Other projects on disk are completely hidden")
        logger.info("  - Full sudo access for installing tools as needed")
        logger.info("  - Installed tools persist and are shared between all sessions")

        # Display available tools
        self._display_available_tools()

        logger.info("\nDocker volumes:")
        logger.info("  - gemini-shared-tools: User-installed packages")
        logger.info("  - gemini-apt-cache: APT package cache")
        logger.info("  - gemini-usr-local: System-wide installations")
        logger.info("  - Project directory: Mounted isolated in container")

        logger.info("\nGemini 3 Pro Features:")
        logger.info("  - State-of-the-art reasoning and agentic coding")
        logger.info("  - 1 million token context window")
        logger.info("  - 60 requests per minute (free tier)")
        logger.info("  - 1000 requests per day (free tier)")
        logger.info("  - Google Search integration")
        logger.info("  - Model Context Protocol (MCP) support")

        logger.info("\nReady to use! Just run gemini.py from any project directory.")

    def _display_available_tools(self) -> None:
        """Display available tools."""
        logger.info("\nAvailable tools:")
        logger.info("  Programming languages:")
        logger.info("  - Node.js 22 LTS + npm")
        logger.info("  - Python 3.12.4 + pip 24.0")
        logger.info("  - Eclipse Temurin JDK 17 (HotSpot) + Maven + Gradle")
        logger.info("  - Ruby")
        logger.info("  - PHP + Composer")
        logger.info("\n  Development tools:")
        logger.info("  - Git, vim, nano")
        logger.info("  - ripgrep, fd-find, fzf")
        logger.info("  - Docker CLI")
        logger.info("  - shellcheck")
        logger.info("\n  Python libraries:")
        logger.info("  - google-generativeai (official Gemini SDK)")
        logger.info("  - PyTorch, seaborn, matplotlib, pandas, numpy, scipy")
        logger.info("  - fastapi, uvicorn")
        logger.info("  - beautifulsoup4, requests, pytest, black")
        logger.info("  - pyyaml, lxml, rich")
        logger.info("  - selenium + Chromium/ChromeDriver")
        logger.info("\n  Other:")
        logger.info("  - LaTeX (texlive with Polish support + XeTeX)")
        logger.info("  - Chromium + ChromeDriver (for Selenium)")
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
