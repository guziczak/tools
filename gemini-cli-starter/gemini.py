#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gemini CLI Docker session launcher with project isolation."""

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

    CONTAINER_NAME = "gemini-persistent"
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
        image_name = "gemini-cli-container:latest"

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
            "No Gemini CLI image found!\n"
            "Expected: gemini-cli-container:latest\n"
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
                        # Ensure gemini symlink exists with retries
                        cls._ensure_gemini_symlink()
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
    def _ensure_gemini_symlink(cls) -> None:
        """Ensure gemini symlink exists in container (handles Gemini CLI updates)."""
        try:
            # Check if gemini command works
            result = cls._run_command(
                ["docker", "exec", cls.CONTAINER_NAME, "which", "gemini"],
                timeout=10,
                check=False
            )
            if result.returncode == 0:
                return  # Symlink exists and works

            # Try to create symlink for new path (dist/index.js)
            logger.info("Creating gemini symlink...")
            cls._run_command(
                ["docker", "exec", cls.CONTAINER_NAME, "bash", "-c",
                 "if [ -f /usr/local/lib/node_modules/@google/gemini-cli/dist/index.js ]; then "
                 "ln -sf /usr/local/lib/node_modules/@google/gemini-cli/dist/index.js /usr/local/bin/gemini && "
                 "chmod +x /usr/local/bin/gemini; "
                 "elif [ -f /usr/local/lib/node_modules/@google/gemini-cli/build/cli.js ]; then "
                 "ln -sf /usr/local/lib/node_modules/@google/gemini-cli/build/cli.js /usr/local/bin/gemini && "
                 "chmod +x /usr/local/bin/gemini; fi"],
                timeout=10,
                check=False
            )
        except Exception as e:
            logger.debug(f"Failed to ensure gemini symlink: {e}")

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


class GeminiLauncher:
    """Main launcher for Gemini CLI sessions."""

    def __init__(self, debug: bool = False):
        self.docker_manager = DockerManager()
        self.path_validator = PathValidator()
        self.image_name = None  # Will be set dynamically
        self.debug = debug
        # Session tracking - use platform-appropriate temp directory
        if sys.platform == "win32":
            self.host_session_dir = Path(os.environ.get("TEMP", "C:/Temp")) / "gemini-sessions"
        else:
            self.host_session_dir = Path("/tmp/gemini-sessions")
        self.container_session_dir = Path("/var/run/gemini-sessions")

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

        # Check for API key configuration
        self._check_api_key_setup()

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
                    logger.warning("⚠️  Docker appears to be using Hyper-V instead of WSL 2!")
                    logger.warning("   This may cause connection errors.")
                    logger.warning("")
                    logger.info("   To fix, switch to WSL 2 backend:")
                    logger.info("   - Docker Desktop: Settings → General → Use WSL 2 based engine")
                    logger.info("   - Rancher Desktop: Settings → Virtual Machine → Type: WSL")
                    logger.warning("")

        except Exception as e:
            logger.debug(f"Could not check Docker backend: {e}")

    def _check_api_key_setup(self) -> None:
        """Check if GEMINI_API_KEY is configured."""
        env_file = Path(__file__).parent / ".env"

        # Check if .env exists and contains GEMINI_API_KEY
        api_key_exists = False
        if env_file.exists():
            with open(env_file, 'r') as f:
                content = f.read()
                if 'GEMINI_API_KEY=' in content and not content.strip().endswith('GEMINI_API_KEY='):
                    api_key_exists = True

        if not api_key_exists:
            logger.warning("\nGEMINI_API_KEY not found in .env file!")
            logger.info("\nTo use Gemini CLI with API Key authentication:")
            logger.info("1. Go to: https://aistudio.google.com/apikey")
            logger.info("2. Click 'Create API Key'")
            logger.info("3. Copy the generated key")

            response = input("\nDo you want to set up API key now? (y/n): ")
            if response.lower() == 'y':
                api_key = input("Paste your Gemini API key: ").strip()
                if api_key:
                    # Create or update .env file
                    env_content = ""
                    if env_file.exists():
                        with open(env_file, 'r') as f:
                            env_content = f.read()
                            # Remove existing GEMINI_API_KEY if present
                            lines = env_content.split('\n')
                            lines = [line for line in lines if not line.startswith('GEMINI_API_KEY=')]
                            env_content = '\n'.join(lines).strip()

                    # Add new API key
                    if env_content and not env_content.endswith('\n'):
                        env_content += '\n'
                    env_content += f"GEMINI_API_KEY={api_key}\n"

                    with open(env_file, 'w') as f:
                        f.write(env_content)

                    logger.info("API key saved to .env file!")
                    logger.info("You can now use Gemini CLI without browser authentication.")
                else:
                    logger.warning("No API key provided. You'll need to authenticate via browser.")
            else:
                logger.info("\nYou can add GEMINI_API_KEY to .env file later.")
                logger.info("Without it, you'll need to authenticate via browser each time.")

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

    def launch_gemini(self, args: List[str]) -> None:
        """Launch Gemini CLI in isolated container using docker exec."""
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

        # Pass GEMINI_API_KEY from .env file if exists
        env_file = Path(__file__).parent / ".env"
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    if line.startswith('GEMINI_API_KEY='):
                        api_key = line.strip().split('=', 1)[1]
                        if api_key:
                            docker_cmd.extend(["-e", f"GEMINI_API_KEY={api_key}"])
                        break

        # Run gemini directly (namespace-launcher loses TTY on Windows)
        # docker_project_path is like /c/Users/... so we need /host_c/Users/...
        if docker_project_path.startswith("/c/"):
            container_path = "/host_c" + docker_project_path[2:]  # Remove /c, keep /Users/...
        elif docker_project_path.startswith("/d/"):
            container_path = "/host_d" + docker_project_path[2:]
        else:
            container_path = docker_project_path

        docker_cmd.extend([
            self.docker_manager.CONTAINER_NAME,
            "sudo", "-u", "gemini", "-E", "HOME=/home/gemini",
            "sh", "-c", f"cd '{container_path}' && exec gemini"
        ])

        # Check if this is first run (no OAuth credentials in container)
        env_file = Path(__file__).parent / ".env"
        first_run = self._check_first_run()

        # Always perform OAuth on first run (API key alone may not work for all features)
        if first_run:
            logger.info("")
            logger.info("=" * 60)
            logger.info("  FIRST RUN - Authentication Required")
            logger.info("=" * 60)
            if not self._perform_oauth_authorization():
                # OAuth failed - offer API key as alternative
                logger.warning("")
                logger.warning("OAuth authorization failed or unavailable.")
                logger.info("")
                logger.info("You can use API key authentication instead:")
                logger.info("1. Go to: https://aistudio.google.com/apikey")
                logger.info("2. Click 'Create API Key'")
                logger.info("3. Copy the generated key")
                logger.info("")

                response = input("Set up API key now? (y/n): ").strip().lower()
                if response == 'y':
                    api_key = input("Paste your Gemini API key: ").strip()
                    if api_key:
                        self._save_api_key(env_file, api_key)
                        logger.info("API key saved! Continuing...")
                        # Update docker_cmd to include the API key
                        docker_cmd.insert(-2, "-e")
                        docker_cmd.insert(-2, f"GEMINI_API_KEY={api_key}")
                    else:
                        logger.error("No API key provided. Cannot continue without authentication.")
                        sys.exit(1)
                else:
                    logger.error("Authentication required. Please try again later.")
                    sys.exit(1)
            logger.info("=" * 60)
            logger.info("")

        logger.info(f"Starting Gemini session in: {project_path}")
        if self.debug:
            logger.debug(f"Session ID: {session_id}")
            logger.debug(f"Docker project path: {docker_project_path}")
            logger.debug(f"Docker command: {' '.join(docker_cmd)}")

        try:
            # Run Gemini in isolated environment using winpty on Windows
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
                    self._handle_gemini_not_found()
            else:
                result = subprocess.run(docker_cmd, check=False)
                if result.returncode in (126, 127):
                    self._handle_gemini_not_found()

        except KeyboardInterrupt:
            logger.info("\nGoodbye!")
        except Exception as e:
            logger.error(f"Error: {e}")
            sys.exit(1)
        finally:
            # Clean up session file when done
            if session_file:
                self._remove_session_file(session_file)

    def _has_api_key(self, env_file: Path) -> bool:
        """Check if API key is configured in .env file."""
        if not env_file.exists():
            return False
        try:
            with open(env_file, 'r') as f:
                content = f.read()
                for line in content.split('\n'):
                    if line.startswith('GEMINI_API_KEY='):
                        key = line.split('=', 1)[1].strip()
                        return bool(key)
        except Exception:
            pass
        return False

    def _save_api_key(self, env_file: Path, api_key: str) -> None:
        """Save API key to .env file."""
        env_content = ""
        if env_file.exists():
            with open(env_file, 'r') as f:
                env_content = f.read()
                # Remove existing GEMINI_API_KEY if present
                lines = env_content.split('\n')
                lines = [line for line in lines if not line.startswith('GEMINI_API_KEY=')]
                env_content = '\n'.join(lines).strip()

        # Add new API key
        if env_content and not env_content.endswith('\n'):
            env_content += '\n'
        env_content += f"GEMINI_API_KEY={api_key}\n"

        with open(env_file, 'w') as f:
            f.write(env_content)

    def _perform_oauth_authorization(self) -> bool:
        """Perform OAuth authorization keeping single process alive.

        OAuth PKCE requires the same process throughout - code_challenge is tied
        to the session. We keep the process alive, get user input, then send it.

        Returns True if authorization succeeded, False otherwise.
        """
        logger.info("")
        logger.info("Starting authorization process...")
        logger.info("")

        # First verify Gemini CLI is accessible
        for attempt in range(self.docker_manager.MAX_RETRIES):
            try:
                version_cmd = [
                    "docker", "exec", "-i",
                    self.docker_manager.CONTAINER_NAME,
                    "sudo", "-u", "gemini", "-E",
                    "HOME=/home/gemini",
                    "gemini", "--version"
                ]
                result = subprocess.run(version_cmd, capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    logger.info(f"Gemini CLI version: {result.stdout.strip()}")
                    break
                if attempt < self.docker_manager.MAX_RETRIES - 1:
                    wait_time = self.docker_manager.RETRY_DELAY * (attempt + 1)
                    logger.warning(f"Gemini CLI not accessible, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error("Gemini CLI not accessible in container")
                    return False
            except subprocess.TimeoutExpired:
                if attempt >= self.docker_manager.MAX_RETRIES - 1:
                    logger.error("Timeout accessing Gemini CLI")
                    return False
                time.sleep(self.docker_manager.RETRY_DELAY)
            except Exception as e:
                if attempt >= self.docker_manager.MAX_RETRIES - 1:
                    logger.error(f"Failed to access Gemini CLI: {e}")
                    return False
                time.sleep(self.docker_manager.RETRY_DELAY)

        try:
            # Run Gemini with stdin kept open for auth code input
            auth_cmd = [
                "docker", "exec", "-i",
                self.docker_manager.CONTAINER_NAME,
                "sudo", "-u", "gemini", "-E",
                "HOME=/home/gemini",
                "gemini"
            ]

            process = subprocess.Popen(
                auth_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            url_found = False
            waiting_for_code = False
            output_queue = queue.Queue()

            def read_output(proc: subprocess.Popen, q: queue.Queue) -> None:
                """Read process output in background thread."""
                try:
                    for line in iter(proc.stdout.readline, ''):
                        if line:
                            q.put(line)
                        if proc.poll() is not None:
                            break
                except Exception:
                    pass

            reader_thread = threading.Thread(target=read_output, args=(process, output_queue))
            reader_thread.daemon = True
            reader_thread.start()

            # Read output until we see the auth code prompt or process exits
            start_time = time.time()
            while time.time() - start_time < 30:
                try:
                    line = output_queue.get(timeout=0.5)
                    print(line, end='', flush=True)

                    if "accounts.google.com" in line:
                        url_found = True

                    if "authorization code" in line.lower():
                        waiting_for_code = True
                        break

                except queue.Empty:
                    if process.poll() is not None:
                        # Process exited - drain remaining output
                        while not output_queue.empty():
                            try:
                                line = output_queue.get_nowait()
                                print(line, end='', flush=True)
                                if "accounts.google.com" in line:
                                    url_found = True
                                if "authorization code" in line.lower():
                                    waiting_for_code = True
                            except queue.Empty:
                                break
                        break

            if not url_found:
                try:
                    process.terminate()
                except Exception:
                    pass
                logger.info("No authorization URL found - may already be authorized.")
                return True

            # Get auth code from user
            logger.info("")
            logger.info("=" * 60)
            logger.info("  Open the URL above in your browser and authorize access.")
            logger.info("  Then paste the authorization code below.")
            logger.info("=" * 60)

            auth_code = input("\nAuthorization code: ").strip()

            if not auth_code:
                logger.error("No authorization code provided")
                try:
                    process.terminate()
                except Exception:
                    pass
                return False

            # Send auth code to the SAME process (important for PKCE!)
            logger.info("Submitting authorization code...")

            if process.poll() is None:
                # Process still alive - send code directly
                try:
                    process.stdin.write(auth_code + "\n")
                    process.stdin.flush()

                    # Read response with timeout
                    response_start = time.time()
                    while time.time() - response_start < 30:
                        try:
                            line = output_queue.get(timeout=1)
                            print(line, end='', flush=True)
                            if "success" in line.lower() or "authenticated" in line.lower():
                                break
                            if "error" in line.lower() or "failed" in line.lower():
                                break
                        except queue.Empty:
                            if process.poll() is not None:
                                break

                    process.stdin.close()
                except Exception as e:
                    logger.debug(f"Error sending auth code: {e}")
            else:
                # Process already exited - this is the problem case
                # Gemini CLI exits without TTY before we can send the code
                logger.warning("Process exited before auth code could be sent.")
                logger.info("Gemini CLI requires an interactive terminal for OAuth.")
                logger.info("")
                logger.info("Alternative: Run authorization manually:")
                logger.info(f"  docker exec -it {self.docker_manager.CONTAINER_NAME} sudo -u gemini gemini")
                return False

            # Wait for process to finish
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.terminate()

            # Verify authorization succeeded
            time.sleep(2)
            if not self._check_first_run():
                logger.info("")
                logger.info("Authorization successful!")
                return True
            else:
                logger.warning("Authorization may not have completed.")
                return False

        except Exception as e:
            logger.error(f"Authorization error: {e}")
            return False

    def _check_first_run(self) -> bool:
        """Check if this is first run (no Gemini auth yet in container)."""
        try:
            result = subprocess.run(
                ["docker", "exec", self.docker_manager.CONTAINER_NAME,
                 "test", "-f", "/home/gemini/.gemini/oauth_creds.json"],
                capture_output=True,
                timeout=5
            )
            # If file exists, not first run
            return result.returncode != 0
        except Exception:
            return True  # Assume first run if we can't check

    def _handle_gemini_not_found(self) -> None:
        """Handle case when Gemini is not found."""
        logger.error("Gemini command not found in container.")
        logger.info("\nTry rebuilding the image:")
        logger.info("  docker compose build --no-cache")
        logger.info("\nOr check if Gemini is installed:")
        logger.info(f"  docker run -it {self.image_name} npm list -g @google/gemini-cli")


def main() -> None:
    """Main entry point."""
    # Check for debug flag
    debug = "--debug" in sys.argv or "-v" in sys.argv or "--verbose" in sys.argv
    if debug:
        # Remove debug flag from args
        sys.argv = [arg for arg in sys.argv if arg not in ["--debug", "-v", "--verbose"]]
        logging.getLogger().setLevel(logging.DEBUG)

    launcher = GeminiLauncher(debug=debug)

    try:
        # Ensure prerequisites
        launcher.ensure_prerequisites()

        # Get command line arguments
        args = sys.argv[1:] if len(sys.argv) > 1 else []

        # Launch Gemini
        launcher.launch_gemini(args)

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
