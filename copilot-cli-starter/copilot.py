#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GitHub Copilot CLI Docker session launcher with project isolation."""

import subprocess
import os
import sys
import time
import logging
import hashlib
import tempfile
import json
import uuid
import secrets
import threading
import queue
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum

# Enable BuildKit globally
os.environ['DOCKER_BUILDKIT'] = '1'
os.environ['COMPOSE_DOCKER_CLI_BUILD'] = '1'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class ContainerStatus(Enum):
    """Container status enumeration."""
    RUNNING = "running"
    STOPPED = "stopped"
    NOT_EXISTS = "not_exists"
    ERROR = "error"


@dataclass
class ContainerInfo:
    """Container information."""
    status: ContainerStatus
    message: str


class DockerContainerError(Exception):
    """Custom exception for Docker container errors."""
    pass


class DockerManager:
    """Manages Docker container operations."""

    CONTAINER_NAME = "copilot-persistent"
    DEFAULT_TIMEOUT = 5
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds

    @staticmethod
    def _run_command(
        cmd: List[str],
        timeout: int = DEFAULT_TIMEOUT,
        check: bool = True
    ) -> subprocess.CompletedProcess:
        """Execute a command with proper encoding and error handling."""
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'

        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            env=env,
            timeout=timeout,
            check=check
        )

    @classmethod
    def check_image_exists(cls, image_name: str) -> bool:
        """Check if the Docker image exists."""
        try:
            result = cls._run_command(
                ["docker", "images", "-q", image_name],
                check=False
            )
            return bool(result.stdout.strip())
        except Exception:
            return False

    @classmethod
    def get_available_image(cls, extended_retry: bool = False) -> str:
        """Find available image.

        Args:
            extended_retry: If True, use extended retries (for post-build scenarios)
        """
        image_name = "copilot-cli-container:latest"

        # Quick check first - if image exists, return immediately
        if cls.check_image_exists(image_name):
            return image_name

        # If extended retry requested (after build), wait longer
        if extended_retry:
            max_attempts = 10
            for attempt in range(max_attempts):
                if cls.check_image_exists(image_name):
                    logger.debug(f"Found image: {image_name}")
                    return image_name
                if attempt < max_attempts - 1:
                    wait_time = min(2 * (attempt + 1), 10)
                    logger.info(f"Waiting for image to be available... ({attempt + 1}/{max_attempts})")
                    time.sleep(wait_time)

        # If image not found, raise error
        raise DockerContainerError(
            "No Copilot CLI image found!\n"
            "Expected: copilot-cli-container:latest\n"
            "Run: python setup.py"
        )

    @classmethod
    def check_docker_running(cls, retries: int = 3) -> bool:
        """Check if Docker daemon is running with retries."""
        for attempt in range(retries):
            try:
                result = cls._run_command(
                    ["docker", "version"],
                    timeout=5,
                    check=False
                )
                if result.returncode == 0:
                    return True
                # Check for Hyper-V socket error - worth retrying
                if "Hyper-V socket" in result.stderr or "timed out" in result.stderr.lower():
                    if attempt < retries - 1:
                        logger.warning(f"Docker connection issue, retrying... ({attempt + 1}/{retries})")
                        time.sleep(cls.RETRY_DELAY * (attempt + 1))
                        continue
            except subprocess.TimeoutExpired:
                if attempt < retries - 1:
                    logger.warning(f"Docker timeout, retrying... ({attempt + 1}/{retries})")
                    time.sleep(cls.RETRY_DELAY * (attempt + 1))
                    continue
            except Exception:
                pass
        return False

    @classmethod
    def container_status(cls) -> ContainerStatus:
        """Check container status."""
        try:
            result = cls._run_command(
                ["docker", "inspect", "-f", "{{.State.Running}}", cls.CONTAINER_NAME],
                check=False
            )
            if result.returncode != 0:
                return ContainerStatus.NOT_EXISTS

            is_running = result.stdout.strip().lower() == "true"
            return ContainerStatus.RUNNING if is_running else ContainerStatus.STOPPED
        except Exception:
            return ContainerStatus.ERROR

    @classmethod
    def start_container(cls, debug: bool = False) -> bool:
        """Start the persistent container with retries."""
        for attempt in range(cls.MAX_RETRIES):
            try:
                status = cls.container_status()

                if status == ContainerStatus.RUNNING:
                    logger.info("Container already running")
                    return True

                if status == ContainerStatus.NOT_EXISTS:
                    logger.info("Creating persistent container...")
                    if attempt == 0:
                        logger.info("First container creation may take 2-3 minutes...")
                    setup_dir = Path(__file__).parent
                    result = subprocess.run(
                        ["docker-compose", "-f", str(setup_dir / "docker-compose.yml"), "up", "-d"],
                        check=False,
                        capture_output=True,
                        text=True
                    )

                    # Check both returncode and stderr for errors
                    # docker-compose sometimes returns 0 but has errors in stderr
                    error_msg = result.stderr or ""
                    has_error = result.returncode != 0 or "Error" in error_msg or "error" in error_msg

                    if has_error:
                        error_msg = error_msg or result.stdout or "Unknown error"
                        # Check for retryable errors (volume issues, connection issues)
                        retryable = (
                            "Hyper-V socket" in error_msg or
                            "timed out" in error_msg.lower() or
                            "invalid volume specification" in error_msg.lower()
                        )
                        if retryable and attempt < cls.MAX_RETRIES - 1:
                            wait_time = cls.RETRY_DELAY * (attempt + 1)
                            logger.warning(f"Container creation failed, retrying in {wait_time}s... ({attempt + 1}/{cls.MAX_RETRIES})")
                            time.sleep(wait_time)
                            continue
                        logger.error(f"Failed to create container: {error_msg}")
                        return False

                elif status == ContainerStatus.STOPPED:
                    logger.info("Starting existing container...")
                    result = cls._run_command(
                        ["docker", "start", cls.CONTAINER_NAME],
                        timeout=30,
                        check=False
                    )
                    if result.returncode != 0:
                        if attempt < cls.MAX_RETRIES - 1:
                            wait_time = cls.RETRY_DELAY * (attempt + 1)
                            logger.warning(f"Container start failed, retrying in {wait_time}s... ({attempt + 1}/{cls.MAX_RETRIES})")
                            time.sleep(wait_time)
                            continue
                        logger.error("Failed to start container")
                        return False

                # Wait for container to be ready
                for wait_attempt in range(15):
                    if cls.container_status() == ContainerStatus.RUNNING:
                        logger.info("Container is ready")
                        # Ensure copilot symlink exists with retries
                        cls._ensure_copilot_symlink()
                        return True
                    time.sleep(1)

                # Container didn't become ready
                if attempt < cls.MAX_RETRIES - 1:
                    logger.warning(f"Container not ready, retrying... ({attempt + 1}/{cls.MAX_RETRIES})")
                    time.sleep(cls.RETRY_DELAY)
                    continue

            except subprocess.TimeoutExpired:
                if attempt < cls.MAX_RETRIES - 1:
                    logger.warning(f"Operation timed out, retrying... ({attempt + 1}/{cls.MAX_RETRIES})")
                    time.sleep(cls.RETRY_DELAY * (attempt + 1))
                    continue
            except Exception as e:
                if attempt < cls.MAX_RETRIES - 1:
                    logger.warning(f"Error: {e}, retrying... ({attempt + 1}/{cls.MAX_RETRIES})")
                    time.sleep(cls.RETRY_DELAY * (attempt + 1))
                    continue
                logger.error(f"Failed to start container: {e}")

        return False

    @classmethod
    def _ensure_copilot_symlink(cls) -> None:
        """Ensure copilot symlink exists in container (handles Copilot CLI updates)."""
        try:
            # Check if copilot command works
            result = cls._run_command(
                ["docker", "exec", cls.CONTAINER_NAME, "which", "copilot"],
                timeout=10,
                check=False
            )
            if result.returncode == 0:
                return  # Symlink exists and works

            # Try to create symlink for possible paths
            logger.info("Creating copilot symlink...")
            cls._run_command(
                ["docker", "exec", cls.CONTAINER_NAME, "bash", "-c",
                 "if [ -f /usr/local/lib/node_modules/@github/copilot/bin/copilot.js ]; then "
                 "ln -sf /usr/local/lib/node_modules/@github/copilot/bin/copilot.js /usr/local/bin/copilot && "
                 "chmod +x /usr/local/bin/copilot; "
                 "elif [ -f /usr/local/lib/node_modules/@github/copilot/dist/index.js ]; then "
                 "ln -sf /usr/local/lib/node_modules/@github/copilot/dist/index.js /usr/local/bin/copilot && "
                 "chmod +x /usr/local/bin/copilot; fi"],
                timeout=10,
                check=False
            )
        except Exception as e:
            logger.debug(f"Failed to ensure copilot symlink: {e}")

    @classmethod
    def _convert_path_for_docker(cls, path: str) -> str:
        """Convert path to Docker format for inside container use."""
        # On Windows, convert path format
        if sys.platform == "win32":
            # Convert Windows path to Unix format for Docker
            path = path.replace('\\', '/')
            if ':' in path:
                drive, rest = path.split(':', 1)
                # For use inside container with /host mount
                path = f"/{drive.lower()}{rest}"

        return path


class PathValidator:
    """Handles path validation."""

    @classmethod
    def validate_project_path(cls, host_path: str) -> Path:
        """Validate project path."""
        try:
            path = Path(host_path).resolve()
        except Exception as e:
            raise DockerContainerError(
                f"Invalid path: {host_path}\nDetails: {e}"
            )

        # Validate path existence
        if not path.exists():
            raise DockerContainerError(f"Path does not exist: {path}")

        if not path.is_dir():
            raise DockerContainerError(f"Path is not a directory: {path}")

        # Check for UNC paths on Windows
        if sys.platform == "win32" and str(path).startswith('\\\\'):
            raise DockerContainerError(
                "UNC network paths are not supported!\n"
                "Please copy files locally or map a network drive."
            )

        return path

    @classmethod
    def generate_session_id(cls, project_path: Path) -> str:
        """Generate cryptographically secure session ID."""
        # Combine multiple sources of entropy
        timestamp = str(time.time_ns())
        random_bytes = secrets.token_hex(16)
        uuid_part = str(uuid.uuid4())
        project_hash = hashlib.sha256(str(project_path).encode()).hexdigest()[:8]

        # Create final session ID
        components = [project_hash, timestamp[-6:], random_bytes[:8], uuid_part[:8]]
        return "-".join(components)


class CopilotLauncher:
    """Main launcher for Copilot CLI sessions."""

    def __init__(self, debug: bool = False):
        self.docker_manager = DockerManager()
        self.path_validator = PathValidator()
        self.image_name = None  # Will be set dynamically
        self.debug = debug
        # Session tracking - use platform-appropriate temp directory
        if sys.platform == "win32":
            self.host_session_dir = Path(os.environ.get("TEMP", "C:/Temp")) / "copilot-sessions"
        else:
            self.host_session_dir = Path("/tmp/copilot-sessions")
        self.container_session_dir = Path("/var/run/copilot-sessions")

    def ensure_prerequisites(self) -> None:
        """Ensure Docker is running and image exists."""
        if not self.docker_manager.check_docker_running():
            raise DockerContainerError(
                "Docker is not running!\n"
                "Please start Docker Desktop or Rancher Desktop and try again."
            )

        # Check Docker backend on Windows
        if sys.platform == "win32":
            self._check_docker_backend()

        try:
            # Try to find available image (quick check)
            self.image_name = self.docker_manager.get_available_image(extended_retry=False)
            logger.info(f"Using image: {self.image_name}")
        except DockerContainerError:
            logger.error("Docker image not found!")
            logger.info("Run: python setup.py")

            response = input("\nRun setup now? (y/n): ")
            if response.lower() == 'y':
                self._run_setup()

                # Check again after setup with extended retries (image may take time to register)
                try:
                    self.image_name = self.docker_manager.get_available_image(extended_retry=True)
                    logger.info(f"Using image: {self.image_name}")
                except DockerContainerError:
                    raise DockerContainerError("Image still not found after setup")
            else:
                raise

        # Check for GitHub authentication
        self._check_github_auth()

    def _check_docker_backend(self) -> None:
        """Check if Docker is using WSL 2 instead of Hyper-V (Windows only)."""
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                timeout=10
            )
            docker_info = result.stdout + result.stderr

            # Check for Hyper-V socket errors or indicators
            if "Hyper-V socket" in docker_info or "hyperv" in docker_info.lower():
                if "WSL" not in docker_info and "rancher" not in docker_info.lower():
                    logger.warning("")
                    logger.warning("Docker appears to be using Hyper-V instead of WSL 2!")
                    logger.warning("   This may cause connection errors.")
                    logger.warning("")
                    logger.info("   To fix, switch to WSL 2 backend:")
                    logger.info("   - Docker Desktop: Settings -> General -> Use WSL 2 based engine")
                    logger.info("   - Rancher Desktop: Settings -> Virtual Machine -> Type: WSL")
                    logger.warning("")

        except Exception as e:
            logger.debug(f"Could not check Docker backend: {e}")

    def _check_github_auth(self) -> None:
        """Check if GitHub authentication is set up in the container."""
        # Copilot CLI uses OAuth via gh auth login, not tokens
        # We just inform the user on first run
        pass

    def _run_setup(self) -> None:
        """Run setup script."""
        setup_path = Path(__file__).parent / "setup.py"
        subprocess.run([sys.executable, str(setup_path)])

    def _create_session_file(self, session_id: str, project_path: Path) -> Optional[Path]:
        """Create session file for tracking. Updated periodically to show activity."""
        try:
            # Ensure host session directory exists
            self.host_session_dir.mkdir(parents=True, exist_ok=True)

            session_file = self.host_session_dir / f"{session_id}.session"

            # Create session data in JSON format
            session_data = {
                "session_id": session_id,
                "project_path": str(project_path),
                "started_at": time.time(),
                "last_active": time.time(),
                "user": os.getenv("USERNAME", os.getenv("USER", "unknown")),
            }

            # Atomic write using temporary file
            with tempfile.NamedTemporaryFile(
                mode='w',
                dir=self.host_session_dir,
                delete=False,
                prefix='.tmp_',
                suffix='.session'
            ) as tmp_file:
                json.dump(session_data, tmp_file, indent=2)
                tmp_file.flush()
                os.fsync(tmp_file.fileno())

            # Atomic rename
            os.rename(tmp_file.name, session_file)

            logger.debug(f"Created session file: {session_file}")
            return session_file

        except Exception as e:
            logger.error(f"Failed to create session file: {e}")
            return None

    def _remove_session_file(self, session_file: Path) -> None:
        """Remove session file."""
        try:
            if session_file and session_file.exists():
                session_file.unlink()
                logger.debug(f"Removed session file: {session_file}")
        except Exception as e:
            logger.warning(f"Failed to remove session file: {e}")

    def launch_copilot(self, args: List[str]) -> None:
        """Launch Copilot CLI in isolated container using docker exec."""
        # Validate current working directory (where user runs the command)
        try:
            project_path = self.path_validator.validate_project_path(os.getcwd())
        except DockerContainerError as e:
            logger.error(str(e))
            sys.exit(1)

        # Generate unique session ID
        session_id = self.path_validator.generate_session_id(project_path)

        # Create session file for tracking
        session_file = self._create_session_file(session_id, project_path)

        # Convert project path for Docker - this will be used inside container
        docker_project_path = self.docker_manager._convert_path_for_docker(str(project_path))

        # Ensure container is running
        if not self.docker_manager.start_container(self.debug):
            logger.error("Failed to start container")
            sys.exit(1)

        # Build docker exec command - pass project path via environment
        docker_cmd = [
            "docker", "exec",
            "-it",
            "-e", f"PROJECT_PATH={docker_project_path}",
            "-e", f"SESSION_ID={session_id}",
            "-e", f"HOST_PROJECT_PATH={str(project_path)}",
        ]

        # Check if this is first run (no GitHub auth yet in container)
        first_run = self._check_first_run()

        if first_run:
            logger.info("")
            logger.info("=" * 60)
            logger.info("  FIRST RUN - GitHub Authentication")
            logger.info("=" * 60)
            logger.info("")
            logger.info("Copilot CLI will open a browser for GitHub OAuth login.")
            logger.info("Just follow the prompts - no tokens needed!")
            logger.info("")
            logger.info("=" * 60)
            logger.info("")

        # Use namespace-launcher for proper session isolation
        # The launcher handles mount namespace, session tracking, and security
        docker_cmd.extend([
            self.docker_manager.CONTAINER_NAME,
            "/usr/local/bin/copilot-namespace-launcher"
        ])

        logger.info(f"Starting Copilot session in: {project_path}")
        if self.debug:
            logger.debug(f"Session ID: {session_id}")
            logger.debug(f"Docker project path: {docker_project_path}")
            logger.debug(f"Docker command: {' '.join(docker_cmd)}")

        try:
            # Run Copilot in isolated environment using winpty on Windows
            if sys.platform == "win32":
                # Use winpty if available, otherwise fallback
                import shutil
                winpty_path = shutil.which("winpty")

                if winpty_path:
                    # winpty provides proper PTY emulation on Windows
                    cmd_str = f'winpty {" ".join(docker_cmd)}'
                    exit_code = os.system(cmd_str)
                else:
                    # Fallback: run directly and hope for the best
                    # For interactive sessions, subprocess with inherited handles works better
                    import subprocess
                    process = subprocess.Popen(
                        docker_cmd,
                        stdin=sys.stdin,
                        stdout=sys.stdout,
                        stderr=sys.stderr,
                        shell=False
                    )
                    exit_code = process.wait()

                if exit_code in (126, 127):
                    self._handle_copilot_not_found()
            else:
                result = subprocess.run(docker_cmd, check=False)
                if result.returncode in (126, 127):
                    self._handle_copilot_not_found()

        except KeyboardInterrupt:
            logger.info("\nGoodbye!")
        except Exception as e:
            logger.error(f"Error: {e}")
            sys.exit(1)
        finally:
            # Clean up session file when done
            if session_file:
                self._remove_session_file(session_file)

    def _check_first_run(self) -> bool:
        """Check if this is first run (no GitHub auth yet in container)."""
        try:
            # Check for GitHub CLI config or Copilot config
            result = subprocess.run(
                ["docker", "exec", self.docker_manager.CONTAINER_NAME,
                 "test", "-d", "/home/copilot/.config/gh"],
                capture_output=True,
                timeout=5
            )
            # If directory exists, not first run
            return result.returncode != 0
        except Exception:
            return True  # Assume first run if we can't check

    def _handle_copilot_not_found(self) -> None:
        """Handle case when Copilot is not found."""
        logger.error("Copilot command not found in container.")
        logger.info("\nTry rebuilding the image:")
        logger.info("  docker compose build --no-cache")
        logger.info("\nOr check if Copilot is installed:")
        logger.info(f"  docker run -it {self.image_name} npm list -g @github/copilot")


def main() -> None:
    """Main entry point."""
    # Check for debug flag
    debug = "--debug" in sys.argv or "-v" in sys.argv or "--verbose" in sys.argv
    if debug:
        # Remove debug flag from args
        sys.argv = [arg for arg in sys.argv if arg not in ["--debug", "-v", "--verbose"]]
        logging.getLogger().setLevel(logging.DEBUG)

    launcher = CopilotLauncher(debug=debug)

    try:
        # Ensure prerequisites
        launcher.ensure_prerequisites()

        # Get command line arguments
        args = sys.argv[1:] if len(sys.argv) > 1 else []

        # Launch Copilot
        launcher.launch_copilot(args)

    except DockerContainerError as e:
        logger.error(str(e))
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
