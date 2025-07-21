#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Claude Code Docker session launcher with project isolation."""

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
from pathlib import Path
from typing import Tuple, List, Optional, Dict
from dataclasses import dataclass
from enum import Enum
from kimi_config_checker import KimiConfigChecker

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

    CONTAINER_NAME = "claude-persistent"
    DEFAULT_TIMEOUT = 5

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
    def get_available_image(cls) -> str:
        """Find available image."""
        image_name = "claude-code-container:latest"
        
        if cls.check_image_exists(image_name):
            logger.debug(f"Found image: {image_name}")
            return image_name

        # If image not found, raise error
        raise DockerContainerError(
            "No Claude Code image found!\n"
            "Expected: claude-code-container:latest\n"
            "Run: python setup.py"
        )

    @classmethod
    def check_docker_running(cls) -> bool:
        """Check if Docker daemon is running."""
        try:
            result = cls._run_command(
                ["docker", "version"],
                timeout=2,
                check=False
            )
            return result.returncode == 0
        except Exception:
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
        """Start the persistent container."""
        status = cls.container_status()

        if status == ContainerStatus.RUNNING:
            logger.info("Container already running")
            return True

        if status == ContainerStatus.NOT_EXISTS:
            logger.info("Creating persistent container...")
            logger.info("First container creation may take 2-3 minutes...")
            setup_dir = Path(__file__).parent
            result = subprocess.run(
                ["docker-compose", "-f", str(setup_dir / "docker-compose.yml"), "up", "-d"],
                check=False,
                capture_output=False
            )
            if result.returncode != 0:
                logger.error("Failed to create container")
                return False

        elif status == ContainerStatus.STOPPED:
            logger.info("Starting existing container...")
            result = cls._run_command(
                ["docker", "start", cls.CONTAINER_NAME],
                check=False
            )
            if result.returncode != 0:
                logger.error("Failed to start container")
                return False

        # Wait for container to be ready
        for _ in range(10):
            if cls.container_status() == ContainerStatus.RUNNING:
                logger.info("Container is ready")
                return True
            time.sleep(1)

        return False

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


class ClaudeLauncher:
    """Main launcher for Claude Code sessions."""

    def __init__(self, debug: bool = False):
        self.docker_manager = DockerManager()
        self.path_validator = PathValidator()
        self.image_name = None  # Will be set dynamically
        self.debug = debug
        self.session_dir = Path("/var/run/claude-sessions")
        self.host_session_dir = Path("/tmp/claude-sessions")
        self.kimi_checker = KimiConfigChecker()

    def ensure_prerequisites(self) -> None:
        """Ensure Docker is running and image exists."""
        if not self.docker_manager.check_docker_running():
            raise DockerContainerError(
                "Docker is not running!\n"
                "Please start Docker Desktop and try again."
            )

        try:
            # Try to find available image
            self.image_name = self.docker_manager.get_available_image()
            logger.info(f"Using image: {self.image_name}")
        except DockerContainerError:
            logger.error("Docker image not found!")
            logger.info("Run: python setup.py")

            response = input("\nRun setup now? (y/n): ")
            if response.lower() == 'y':
                self._run_setup()

                # Check again after setup
                try:
                    self.image_name = self.docker_manager.get_available_image()
                    logger.info(f"Using image: {self.image_name}")
                except DockerContainerError:
                    raise DockerContainerError("Image still not found after setup")
            else:
                raise

    def _run_setup(self) -> None:
        """Run setup script."""
        setup_path = Path(__file__).parent / "setup.py"
        subprocess.run([sys.executable, str(setup_path)])

    def _create_session_pid_file(self, session_id: str, project_path: Path) -> Optional[Path]:
        """Create PID file for session tracking using volume mount."""
        try:
            # Ensure host session directory exists
            self.host_session_dir.mkdir(parents=True, exist_ok=True)
            
            pid_file = self.host_session_dir / f"{session_id}.pid"
            
            # Create PID data in JSON format
            pid_data = {
                "host_pid": os.getpid(),
                "timestamp": time.time(),
                "project_path": str(project_path),
                "session_id": session_id,
                "user": os.getenv("USER", "unknown"),
                "claude_version": os.getenv("CLAUDE_VERSION", "unknown")
            }
            
            # Atomic write using temporary file
            with tempfile.NamedTemporaryFile(
                mode='w', 
                dir=self.host_session_dir, 
                delete=False, 
                prefix='.tmp_',
                suffix='.pid'
            ) as tmp_file:
                json.dump(pid_data, tmp_file, indent=2)
                tmp_file.flush()
                os.fsync(tmp_file.fileno())
            
            # Atomic rename
            os.rename(tmp_file.name, pid_file)
            os.chmod(pid_file, 0o644)
            
            logger.debug(f"Created PID file: {pid_file}")
            return pid_file
            
        except Exception as e:
            logger.error(f"Failed to create PID file: {e}")
            return None

    def _remove_session_pid_file(self, pid_file: Path) -> None:
        """Remove PID file for session."""
        try:
            if pid_file and pid_file.exists():
                pid_file.unlink()
                logger.debug(f"Removed PID file: {pid_file}")
        except Exception as e:
            logger.warning(f"Failed to remove PID file: {e}")

    def launch_claude(self, args: List[str]) -> None:
        """Launch Claude Code in isolated container using docker exec."""
        # Validate current directory
        try:
            project_path = self.path_validator.validate_project_path(os.getcwd())
        except DockerContainerError as e:
            logger.error(str(e))
            sys.exit(1)

        # Generate unique session ID
        session_id = self.path_validator.generate_session_id(project_path)
        
        # Create PID file for session tracking
        pid_file = self._create_session_pid_file(session_id, project_path)

        # Convert project path for Docker - this will be used inside container
        docker_project_path = self.docker_manager._convert_path_for_docker(str(project_path))

        # Check for Kimi configuration
        kimi_config = self.kimi_checker.check_kimi_config(project_path)
        if kimi_config:
            logger.info("Kimi API configuration detected - switching to Kimi mode")
            self.kimi_checker.export_kimi_env(kimi_config)
        else:
            logger.info("Using default Claude Opus configuration")
        
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
        
        # Add Kimi environment variables if configured
        if kimi_config:
            docker_cmd.extend([
                "-e", f"ANTHROPIC_BASE_URL={os.environ.get('ANTHROPIC_BASE_URL', '')}",
                "-e", f"ANTHROPIC_API_KEY={os.environ.get('ANTHROPIC_API_KEY', '')}",
                "-e", f"CLAUDE_DEFAULT_MODEL={os.environ.get('CLAUDE_DEFAULT_MODEL', '')}",
                "-e", "CLAUDE_PROVIDER=kimi",
                "-e", "CLAUDE_MODE=kimi"
            ])
        
        docker_cmd.extend([
            self.docker_manager.CONTAINER_NAME,
            "/usr/local/bin/claude-namespace-launcher"
        ] + args)

        logger.info(f"Starting {'Kimi' if kimi_config else 'Claude'} session in: {project_path}")
        if self.debug:
            logger.debug(f"Session ID: {session_id}")
            logger.debug(f"Docker project path: {docker_project_path}")
            logger.debug(f"Docker command: {' '.join(docker_cmd)}")
            if kimi_config:
                logger.debug("Kimi mode enabled")

        try:
            # Run Claude in isolated environment
            result = subprocess.run(docker_cmd, check=False)

            # Handle command not found
            if result.returncode in (126, 127):
                self._handle_claude_not_found()

        except KeyboardInterrupt:
            logger.info("\nGoodbye!")
        except Exception as e:
            logger.error(f"Error: {e}")
            sys.exit(1)
        finally:
            # Clean up PID file when done
            if pid_file:
                self._remove_session_pid_file(pid_file)

    def _handle_claude_not_found(self) -> None:
        """Handle case when Claude is not found."""
        logger.error("Claude command not found in container.")
        logger.info("\nTry rebuilding the image:")
        logger.info("  docker compose build --no-cache")
        logger.info("\nOr check if Claude is installed:")
        logger.info(f"  docker run -it {self.image_name} npm list -g")


def main() -> None:
    """Main entry point."""
    # Check for debug flag
    debug = "--debug" in sys.argv or "-v" in sys.argv or "--verbose" in sys.argv
    if debug:
        # Remove debug flag from args
        sys.argv = [arg for arg in sys.argv if arg not in ["--debug", "-v", "--verbose"]]
        logging.getLogger().setLevel(logging.DEBUG)

    launcher = ClaudeLauncher(debug=debug)

    try:
        # Ensure prerequisites
        launcher.ensure_prerequisites()

        # Get command line arguments
        args = sys.argv[1:] if len(sys.argv) > 1 else []

        # Launch Claude
        launcher.launch_claude(args)

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