# Build stage for Node.js packages
FROM node:22-slim AS node-builder

# Install Gemini CLI and development tools
RUN npm install -g typescript eslint prettier && \
    npm install -g @google/gemini-cli && \
    npm cache clean --force

# Build stage for Python 3.12.4
FROM ubuntu:24.04 AS python-builder

ENV DEBIAN_FRONTEND=noninteractive

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential wget ca-certificates \
    libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev \
    libncursesw5-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev \
    && rm -rf /var/lib/apt/lists/*

# Download and compile Python 3.12.4
RUN wget -q https://www.python.org/ftp/python/3.12.4/Python-3.12.4.tgz && \
    tar xzf Python-3.12.4.tgz && \
    cd Python-3.12.4 && \
    ./configure --enable-optimizations --prefix=/opt/python3.12 && \
    make -j$(nproc) && \
    make install && \
    cd .. && rm -rf Python-3.12.4 Python-3.12.4.tgz

# Install pip 24.0
RUN /opt/python3.12/bin/python3 -m pip install --upgrade pip==24.0

# Main image
FROM ubuntu:24.04

# Environment configuration
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONIOENCODING=utf-8 \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8 \
    PATH="/usr/local/lib/node_modules/.bin:${PATH}" \
    # Python paths - change these when upgrading Python version
    PYTHON_HOME=/opt/python3.12 \
    PYTHON_BIN=/opt/python3.12/bin/python3

# Copy Node.js and packages from build stage
COPY --from=node-builder /usr/local/bin/node /usr/local/bin/
COPY --from=node-builder /usr/local/lib/node_modules /usr/local/lib/node_modules

# Copy Python 3.12.4 from build stage
COPY --from=python-builder /opt/python3.12 /opt/python3.12

# Create symlinks and install base packages
RUN ln -s /usr/local/bin/node /usr/local/bin/nodejs && \
    ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm && \
    # Create symlink for gemini (handles both old build/cli.js and new dist/index.js paths)
    if [ -f "/usr/local/lib/node_modules/@google/gemini-cli/dist/index.js" ]; then \
        ln -sf /usr/local/lib/node_modules/@google/gemini-cli/dist/index.js /usr/local/bin/gemini && \
        chmod +x /usr/local/bin/gemini && \
        echo "Gemini symlink created (dist/index.js)"; \
    elif [ -f "/usr/local/lib/node_modules/@google/gemini-cli/build/cli.js" ]; then \
        ln -sf /usr/local/lib/node_modules/@google/gemini-cli/build/cli.js /usr/local/bin/gemini && \
        chmod +x /usr/local/bin/gemini && \
        echo "Gemini symlink created (build/cli.js)"; \
    else \
        echo "ERROR: Gemini CLI entry point not found!"; \
        ls -la /usr/local/lib/node_modules/@google/gemini-cli/ 2>/dev/null || true; \
    fi && \
    # Symlinks for other tools
    ln -s /usr/local/lib/node_modules/typescript/bin/tsc /usr/local/bin/tsc 2>/dev/null || true && \
    ln -s /usr/local/lib/node_modules/eslint/bin/eslint.js /usr/local/bin/eslint 2>/dev/null || true && \
    ln -s /usr/local/lib/node_modules/prettier/bin/prettier.cjs /usr/local/bin/prettier 2>/dev/null || true && \
    # Base packages
    apt-get update && apt-get install -y --no-install-recommends \
    sudo util-linux \
    curl wget \
    gnupg lsb-release \
    software-properties-common apt-transport-https \
    git vim nano zip unzip xz-utils \
    build-essential pkg-config \
    # Supervisor for process management
    supervisor \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set up Python 3.12.4 symlinks and install runtime dependencies
RUN ln -sf /opt/python3.12/bin/python3 /usr/local/bin/python3 && \
    ln -sf /opt/python3.12/bin/python3 /usr/local/bin/python && \
    ln -sf /opt/python3.12/bin/pip3 /usr/local/bin/pip3 && \
    ln -sf /opt/python3.12/bin/pip3 /usr/local/bin/pip && \
    # Install runtime dependencies for compiled Python
    apt-get update && apt-get install -y --no-install-recommends \
    libssl3 zlib1g libbz2-1.0 libreadline8 libsqlite3-0 \
    libncursesw6 libxml2 libxmlsec1 libffi8 liblzma5 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Eclipse Temurin JDK 17 from direct download (more reliable than apt repository)
RUN apt-get update && apt-get install -y --no-install-recommends wget ca-certificates && \
    mkdir -p /opt/java && \
    wget -q --timeout=60 --tries=3 -O /tmp/temurin17.tar.gz \
        "https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.13%2B11/OpenJDK17U-jdk_x64_linux_hotspot_17.0.13_11.tar.gz" && \
    tar -xzf /tmp/temurin17.tar.gz -C /opt/java --strip-components=1 && \
    rm /tmp/temurin17.tar.gz && \
    ln -s /opt/java/bin/java /usr/local/bin/java && \
    ln -s /opt/java/bin/javac /usr/local/bin/javac && \
    ln -s /opt/java/bin/jar /usr/local/bin/jar && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set JAVA_HOME environment variable
ENV JAVA_HOME=/opt/java
ENV PATH="${JAVA_HOME}/bin:${PATH}"

# Create gemini user with sudo and appropriate permissions
RUN useradd -m -s /bin/bash gemini && \
    usermod -aG sudo gemini && \
    usermod -aG root gemini && \
    echo "gemini ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/gemini && \
    chmod 0440 /etc/sudoers.d/gemini && \
    # Permissions for apt - gemini can install packages
    chmod -R g+w /var/lib/apt /var/cache/apt && \
    chgrp -R root /var/lib/apt /var/cache/apt && \
    # Permissions for other system directories
    chmod g+w /usr/local/bin /usr/local/lib && \
    chgrp root /usr/local/bin /usr/local/lib && \
    # Create dedicated user for cleanup daemon
    useradd -r -s /bin/false -d /nonexistent -c "Gemini Cleanup Daemon" gemini-cleanup && \
    mkdir -p /var/log /var/run/gemini-sessions && \
    chown gemini-cleanup:gemini-cleanup /var/run/gemini-sessions && \
    chmod 755 /var/run/gemini-sessions && \
    # Create default Gemini settings with preview features, Gemini 3 Pro model, and HIGH thinking
    mkdir -p /home/gemini/.gemini && \
    echo '{"model":{"name":"gemini-3-pro-preview"},"security":{"auth":{"selectedType":"oauth-personal"}},"ui":{"theme":"Default"},"general":{"previewFeatures":true},"thinkingConfig":{"includeThoughts":true,"thinkingLevel":"HIGH"}}' > /home/gemini/.gemini/settings.json && \
    chown -R gemini:gemini /home/gemini/.gemini

# Install additional packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Maven and Gradle
    maven gradle \
    # Ruby
    ruby-full \
    # PHP
    php php-cli php-mbstring php-xml php-zip \
    # Development tools
    tree jq net-tools iputils-ping htop \
    ripgrep fd-find fzf shellcheck \
    # Chrome for Selenium
    chromium-browser chromium-chromedriver \
    # Docker CLI
    docker.io \
    # Media
    imagemagick ffmpeg \
    # Database
    sqlite3 postgresql-client mysql-client \
    # Terminal multiplexers
    tmux screen \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install LaTeX - full version with Polish support and XeTeX
RUN apt-get update && apt-get install -y \
    texlive texlive-latex-extra texlive-fonts-recommended \
    texlive-lang-polish biber latexmk \
    texlive-xetex texlive-fonts-extra fonts-roboto \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Composer for PHP
RUN curl -sS https://getcomposer.org/installer | php -- --install-dir=/usr/local/bin --filename=composer

# Python packages (using compiled Python 3.12.4)
RUN python3 -m pip install --no-cache-dir \
    requests beautifulsoup4 \
    pytest black flake8 \
    selenium==4.18.1 fastapi==0.109.2 uvicorn==0.27.1 \
    pydantic==2.6.1 pyyaml==6.0.1 \
    lxml==5.1.0 aiofiles==23.2.1 python-multipart==0.0.9 \
    httpx==0.26.0 websockets==12.0 rich==13.7.0 \
    google-generativeai \
    # Data science packages
    seaborn matplotlib pandas numpy scipy

# PyTorch CPU version
RUN python3 -m pip install --no-cache-dir \
    torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu || \
    echo "Warning: PyTorch installation failed, continuing without it"

# Chrome environment variables
RUN cat >> /etc/bash.bashrc << 'EOF'
export CHROME_BIN=/usr/bin/chromium-browser
export CHROME_DRIVER=/usr/bin/chromedriver
EOF

# Helper script for Gemini CLI installation
RUN cat > /usr/local/bin/check-gemini << 'EOF'
#!/bin/bash
if ! which gemini >/dev/null 2>&1; then
    echo "Gemini CLI not found. Attempting to install..."
    npm install -g @google/gemini-cli && \
        echo "Gemini CLI installed successfully!" || \
        echo "Failed to install Gemini CLI"
fi
EOF

# Fix line endings for check-gemini script
RUN sed -i 's/\r$//' /usr/local/bin/check-gemini && \
    chmod +x /usr/local/bin/check-gemini && \
    # Fix npm permissions for gemini user to allow auto-updates
    chown -R gemini:gemini /usr/local/lib/node_modules/@google 2>/dev/null || true && \
    chmod -R 755 /usr/local/lib/node_modules/@google 2>/dev/null || true && \
    # Create npm cache directory with correct permissions
    mkdir -p /home/gemini/.npm && \
    chown -R gemini:gemini /home/gemini/.npm && \
    # Allow gemini to run npm commands as root for global updates
    echo "gemini ALL=(root) NOPASSWD: /usr/bin/npm" >> /etc/sudoers.d/gemini

# Create directory structure for shared tools
RUN mkdir -p /opt/gemini-shared/{bin,lib,share} \
    /opt/gemini-shared/lib/{python3/site-packages,node_modules} && \
    chown -R gemini:gemini /opt/gemini-shared && \
    chmod -R g+w /opt/gemini-shared && \
    chgrp -R root /opt/gemini-shared

# Create namespace launcher script with session management and heartbeat
RUN cat > /usr/local/bin/gemini-namespace-launcher << 'LAUNCHER_EOF'
#!/bin/bash
# Gemini namespace launcher - creates isolated mount namespace per session
# Features:
# - Session registration with SQLite-based session manager
# - Background heartbeat process for liveness detection
# - Clean session unregistration on exit
# - Preserves stdin for interactive Gemini CLI usage

set -e

# Generate unique session ID (validate UUID format)
generate_session_id() {
    local uuid
    uuid=$(cat /proc/sys/kernel/random/uuid 2>/dev/null || date +%s%N)
    # Validate UUID-like format or numeric timestamp
    if [[ "$uuid" =~ ^[a-f0-9-]+$ ]] || [[ "$uuid" =~ ^[0-9]+$ ]]; then
        echo "$uuid"
    else
        date +%s%N
    fi
}

SESSION_ID="${SESSION_ID:-$(generate_session_id)}"

# Validate session ID format (alphanumeric, hyphens only)
if [[ ! "$SESSION_ID" =~ ^[a-zA-Z0-9-]+$ ]]; then
    echo "Error: Invalid SESSION_ID format"
    exit 1
fi

export SESSION_ID

# Check if project path provided
if [ -z "$PROJECT_PATH" ]; then
    echo "Error: No project path provided via PROJECT_PATH environment variable"
    exit 1
fi

# Validate PROJECT_PATH - no null bytes, shell metacharacters
if [[ "$PROJECT_PATH" =~ [\'\"\`\$\;\&\|\<\>] ]]; then
    echo "Error: PROJECT_PATH contains invalid characters"
    exit 1
fi

# Determine project source based on mount point
if [ -d "/host${PROJECT_PATH}" ]; then
    PROJECT_SOURCE="/host${PROJECT_PATH}"
elif [ -d "/host_c${PROJECT_PATH#/c}" ] && [[ "$PROJECT_PATH" == /c/* ]]; then
    PROJECT_SOURCE="/host_c${PROJECT_PATH#/c}"
elif [ -d "/host_d${PROJECT_PATH#/d}" ] && [[ "$PROJECT_PATH" == /d/* ]]; then
    PROJECT_SOURCE="/host_d${PROJECT_PATH#/d}"
else
    echo "Error: Cannot find project at any expected mount point"
    echo "Looking for: $PROJECT_PATH"
    echo "Tried: /host${PROJECT_PATH}, /host_c${PROJECT_PATH#/c}, /host_d${PROJECT_PATH#/d}"
    exit 1
fi

# Export variables for child process (safer than string interpolation)
export PROJECT_SOURCE

# Create mount namespace with private propagation
# --propagation private prevents mount changes from leaking to parent namespace
exec unshare --mount --propagation private /bin/bash << 'NAMESPACE_SCRIPT'
#!/bin/bash
set -e

# Variables are inherited from parent via export

# Use PYTHON_BIN from environment (set in Dockerfile ENV)
PYTHON="${PYTHON_BIN:-/opt/python3.12/bin/python3}"

# Heartbeat function - runs in background
heartbeat_loop() {
    while true; do
        "$PYTHON" /usr/local/bin/session_manager.py heartbeat "$SESSION_ID" 2>/dev/null || true
        sleep 30
    done
}

# Cleanup function - unregister session and stop heartbeat
cleanup() {
    # Kill heartbeat process
    if [ -n "$HEARTBEAT_PID" ]; then
        kill $HEARTBEAT_PID 2>/dev/null || true
        wait $HEARTBEAT_PID 2>/dev/null || true
    fi

    # Unregister session
    "$PYTHON" /usr/local/bin/session_manager.py unregister "$SESSION_ID" 2>/dev/null || true

    # Unmount
    umount /project 2>/dev/null || true
    umount /host 2>/dev/null || true
    umount /host_c 2>/dev/null || true
    umount /host_d 2>/dev/null || true
    rm -rf /tmp/empty 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Create and mount project directory
mkdir -p /project
mount --bind "$PROJECT_SOURCE" /project
mount -o remount,rw /project

# Hide host mounts from the user for security
mkdir -p /tmp/empty
mount --bind /tmp/empty /host 2>/dev/null || true
mount --bind /tmp/empty /host_c 2>/dev/null || true
mount --bind /tmp/empty /host_d 2>/dev/null || true

cd /project

# Register session with session manager
"$PYTHON" /usr/local/bin/session_manager.py register "$SESSION_ID" $$ "$PROJECT_PATH" 2>/dev/null || true

# Start heartbeat in background
heartbeat_loop &
HEARTBEAT_PID=$!

# Run gemini as gemini user
# Using exec to replace shell, preserving stdin/stdout/stderr
exec sudo -u gemini -E HOME=/home/gemini gemini
NAMESPACE_SCRIPT
LAUNCHER_EOF

# Fix line endings and set executable
RUN sed -i 's/\r$//' /usr/local/bin/gemini-namespace-launcher && \
    chmod +x /usr/local/bin/gemini-namespace-launcher

# Python session manager daemon (replaces old bash daemon)
# Uses SQLite + heartbeat for reliable session tracking
RUN cat > /usr/local/bin/session_manager.py << 'SESSIONMGR_EOF'
#!/usr/bin/env python3
"""
Gemini Session Manager - Advanced session cleanup daemon with heartbeat and SQLite.

This daemon manages Gemini CLI sessions using:
- SQLite database for atomic session tracking
- Heartbeat mechanism for accurate liveness detection
- Process group killing for clean termination
- Graceful shutdown with SIGTERM -> SIGKILL escalation

Better than bash-based solutions because:
- Atomic database operations (no race conditions)
- Proper error handling and logging
- Easy to test and maintain
- Cross-platform process management
"""

import os
import sys
import time
import signal
import sqlite3
import logging
from pathlib import Path
from contextlib import contextmanager
from typing import Optional

# Configuration
DB_PATH = Path("/var/run/gemini-sessions/sessions.db")
HEARTBEAT_TIMEOUT = 300  # 5 minutes - session considered dead if no heartbeat
CHECK_INTERVAL = 60  # Check every minute
GRACEFUL_KILL_TIMEOUT = 5  # Seconds to wait after SIGTERM before SIGKILL
LOG_FILE = Path("/var/log/gemini-session-manager.log")
HEALTH_FILE = Path("/var/run/gemini-cleanup.health")

# Setup logging - only to file, supervisor captures stdout separately
def setup_logging():
    """Configure logging based on run mode."""
    log_dir = LOG_FILE.parent
    log_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%SZ',
        handlers=[logging.FileHandler(LOG_FILE)]
    )
    return logging.getLogger(__name__)

logger = setup_logging()


class SessionDatabase:
    """SQLite-based session tracking with atomic operations."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._ensure_db_dir()
        self._init_db()

    def _ensure_db_dir(self):
        """Ensure database directory exists."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _connection(self):
        """Context manager for database connections with proper locking."""
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=30.0,
            isolation_level='EXCLUSIVE'
        )
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        """Initialize database schema."""
        with self._connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    pid INTEGER NOT NULL,
                    pgid INTEGER,
                    project_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active'
                )
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_last_heartbeat
                ON sessions(last_heartbeat)
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_status
                ON sessions(status)
            ''')

    def register_session(self, session_id: str, pid: int, pgid: Optional[int],
                         project_path: str) -> bool:
        """Register a new session. Returns True if successful."""
        try:
            with self._connection() as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO sessions
                    (session_id, pid, pgid, project_path, created_at, last_heartbeat, status)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'active')
                ''', (session_id, pid, pgid, project_path))
            logger.info(f"Registered session {session_id} (PID: {pid}, PGID: {pgid})")
            return True
        except Exception as e:
            logger.error(f"Failed to register session {session_id}: {e}")
            return False

    def heartbeat(self, session_id: str) -> bool:
        """Update heartbeat for a session. Returns True if session exists."""
        try:
            with self._connection() as conn:
                cursor = conn.execute('''
                    UPDATE sessions
                    SET last_heartbeat = CURRENT_TIMESTAMP
                    WHERE session_id = ? AND status = 'active'
                ''', (session_id,))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to update heartbeat for {session_id}: {e}")
            return False

    def unregister_session(self, session_id: str) -> bool:
        """Mark session as ended. Returns True if successful."""
        try:
            with self._connection() as conn:
                conn.execute('''
                    UPDATE sessions SET status = 'ended'
                    WHERE session_id = ?
                ''', (session_id,))
            logger.info(f"Unregistered session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to unregister session {session_id}: {e}")
            return False

    def get_stale_sessions(self, timeout_seconds: int) -> list:
        """Get sessions that haven't sent heartbeat within timeout."""
        try:
            with self._connection() as conn:
                cursor = conn.execute('''
                    SELECT session_id, pid, pgid, project_path, last_heartbeat
                    FROM sessions
                    WHERE status = 'active'
                    AND datetime(last_heartbeat, '+' || ? || ' seconds') < datetime('now')
                ''', (timeout_seconds,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get stale sessions: {e}")
            return []

    def mark_session_killed(self, session_id: str):
        """Mark session as killed by daemon."""
        try:
            with self._connection() as conn:
                conn.execute('''
                    UPDATE sessions SET status = 'killed'
                    WHERE session_id = ?
                ''', (session_id,))
        except Exception as e:
            logger.error(f"Failed to mark session {session_id} as killed: {e}")

    def cleanup_old_records(self, days: int = 7):
        """Remove records older than specified days."""
        try:
            with self._connection() as conn:
                cursor = conn.execute('''
                    DELETE FROM sessions
                    WHERE datetime(last_heartbeat, '+' || ? || ' days') < datetime('now')
                    AND status != 'active'
                ''', (days,))
                if cursor.rowcount > 0:
                    logger.info(f"Cleaned up {cursor.rowcount} old session records")
        except Exception as e:
            logger.error(f"Failed to cleanup old records: {e}")

    def get_active_session_count(self) -> int:
        """Get count of active sessions."""
        try:
            with self._connection() as conn:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM sessions WHERE status = 'active'"
                )
                return cursor.fetchone()[0]
        except Exception:
            return 0


class ProcessKiller:
    """Safe process termination with escalation."""

    @staticmethod
    def is_process_alive(pid: int) -> bool:
        """Check if process exists."""
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    @staticmethod
    def is_gemini_process(pid: int) -> bool:
        """Verify this is actually a Gemini-related process."""
        try:
            cmdline_path = Path(f"/proc/{pid}/cmdline")
            if cmdline_path.exists():
                cmdline = cmdline_path.read_text()
                gemini_indicators = ['gemini', 'node', 'npm']
                return any(ind in cmdline.lower() for ind in gemini_indicators)
        except Exception:
            pass
        return False

    @staticmethod
    def kill_process_group(pgid: int, graceful_timeout: int = 5) -> bool:
        """Kill entire process group with SIGTERM then SIGKILL."""
        if pgid is None or pgid <= 0:
            return False

        try:
            os.killpg(pgid, signal.SIGTERM)
            logger.info(f"Sent SIGTERM to process group {pgid}")

            for _ in range(graceful_timeout * 10):
                time.sleep(0.1)
                try:
                    os.killpg(pgid, 0)
                except OSError:
                    logger.info(f"Process group {pgid} terminated gracefully")
                    return True

            try:
                os.killpg(pgid, signal.SIGKILL)
                logger.warning(f"Sent SIGKILL to process group {pgid}")
                return True
            except OSError:
                return True

        except OSError as e:
            if e.errno == 3:  # No such process
                return True
            logger.error(f"Failed to kill process group {pgid}: {e}")
            return False

    @staticmethod
    def kill_process(pid: int, graceful_timeout: int = 5) -> bool:
        """Kill single process with SIGTERM then SIGKILL."""
        if pid is None or pid <= 0:
            return False

        try:
            os.kill(pid, signal.SIGTERM)
            logger.info(f"Sent SIGTERM to PID {pid}")

            for _ in range(graceful_timeout * 10):
                time.sleep(0.1)
                if not ProcessKiller.is_process_alive(pid):
                    logger.info(f"Process {pid} terminated gracefully")
                    return True

            try:
                os.kill(pid, signal.SIGKILL)
                logger.warning(f"Sent SIGKILL to PID {pid}")
                return True
            except OSError:
                return True

        except OSError as e:
            if e.errno == 3:  # No such process
                return True
            logger.error(f"Failed to kill process {pid}: {e}")
            return False


class SessionManager:
    """Main session manager daemon."""

    def __init__(self):
        self.db = SessionDatabase(DB_PATH)
        self.killer = ProcessKiller()
        self.running = True
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Setup graceful shutdown handlers."""
        signal.signal(signal.SIGTERM, self._shutdown_handler)
        signal.signal(signal.SIGINT, self._shutdown_handler)

    def _shutdown_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False

    def _update_health(self):
        """Update health file for Docker healthcheck."""
        try:
            HEALTH_FILE.write_text(str(int(time.time())))
        except Exception as e:
            logger.error(f"Failed to update health file: {e}")

    def cleanup_stale_sessions(self):
        """Find and kill stale sessions."""
        stale_sessions = self.db.get_stale_sessions(HEARTBEAT_TIMEOUT)

        for session in stale_sessions:
            session_id = session['session_id']
            pid = session['pid']
            pgid = session['pgid']
            last_hb = session['last_heartbeat']

            logger.info(
                f"Stale session detected: {session_id} "
                f"(PID: {pid}, last heartbeat: {last_hb})"
            )

            # Check if process is still alive
            if not pid or not self.killer.is_process_alive(pid):
                logger.info(f"Session {session_id} process already dead, cleaning up record")
                self.db.mark_session_killed(session_id)
                continue

            # Verify it's actually a Gemini process before killing
            if not self.killer.is_gemini_process(pid):
                logger.warning(
                    f"PID {pid} doesn't appear to be a Gemini process, "
                    f"marking as ended without killing"
                )
                self.db.mark_session_killed(session_id)
                continue

            # Kill the process - try process group first, then individual PID
            killed = False
            if pgid:
                killed = self.killer.kill_process_group(pgid, GRACEFUL_KILL_TIMEOUT)

            if not killed:
                killed = self.killer.kill_process(pid, GRACEFUL_KILL_TIMEOUT)

            self.db.mark_session_killed(session_id)

            if killed:
                logger.info(f"Successfully terminated stale session {session_id}")
            else:
                logger.error(f"Failed to terminate session {session_id}")

    def run(self):
        """Main daemon loop."""
        logger.info(f"Gemini Session Manager started (PID: {os.getpid()})")
        logger.info(f"Heartbeat timeout: {HEARTBEAT_TIMEOUT}s, Check interval: {CHECK_INTERVAL}s")

        cleanup_counter = 0

        while self.running:
            try:
                self._update_health()
                self.cleanup_stale_sessions()

                cleanup_counter += 1
                if cleanup_counter >= 60:
                    self.db.cleanup_old_records(days=7)
                    cleanup_counter = 0

                active = self.db.get_active_session_count()
                if active > 0:
                    logger.debug(f"Active sessions: {active}")

            except Exception as e:
                logger.error(f"Error in cleanup cycle: {e}")

            for _ in range(CHECK_INTERVAL):
                if not self.running:
                    break
                time.sleep(1)

        logger.info("Gemini Session Manager stopped")


# Client functions for use by session launcher
def register_session(session_id: str, pid: int, project_path: str):
    """Register a new session (called by launcher)."""
    try:
        pgid = os.getpgid(pid)
    except OSError:
        pgid = None
    db = SessionDatabase(DB_PATH)
    return db.register_session(session_id, pid, pgid, project_path)


def send_heartbeat(session_id: str):
    """Send heartbeat for session (called periodically by launcher)."""
    db = SessionDatabase(DB_PATH)
    return db.heartbeat(session_id)


def unregister_session(session_id: str):
    """Unregister session on clean exit (called by launcher)."""
    db = SessionDatabase(DB_PATH)
    return db.unregister_session(session_id)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == 'register' and len(sys.argv) >= 5:
            session_id, pid, project_path = sys.argv[2], int(sys.argv[3]), sys.argv[4]
            success = register_session(session_id, pid, project_path)
            sys.exit(0 if success else 1)

        elif cmd == 'heartbeat' and len(sys.argv) >= 3:
            session_id = sys.argv[2]
            success = send_heartbeat(session_id)
            sys.exit(0 if success else 1)

        elif cmd == 'unregister' and len(sys.argv) >= 3:
            session_id = sys.argv[2]
            success = unregister_session(session_id)
            sys.exit(0 if success else 1)

        else:
            print("Usage:")
            print("  session_manager.py                    # Run daemon")
            print("  session_manager.py register ID PID PATH")
            print("  session_manager.py heartbeat ID")
            print("  session_manager.py unregister ID")
            sys.exit(1)
    else:
        manager = SessionManager()
        manager.run()
SESSIONMGR_EOF

RUN sed -i 's/\r$//' /usr/local/bin/session_manager.py && \
    chmod +x /usr/local/bin/session_manager.py && \
    chown root:root /usr/local/bin/session_manager.py && \
    # Ensure sessions directory exists with correct permissions
    mkdir -p /var/run/gemini-sessions && \
    chown gemini-cleanup:gemini-cleanup /var/run/gemini-sessions && \
    chmod 755 /var/run/gemini-sessions

# Simple session starter script
RUN cat > /usr/local/bin/gemini-session << 'EOF'
#!/bin/bash
cd "${1:-/project}"
shift
exec gemini "$@"
EOF

# Fix line endings and set executable
RUN sed -i 's/\r$//' /usr/local/bin/gemini-session && \
    chmod +x /usr/local/bin/gemini-session

# Configuration for shared tools - append to bash.bashrc
RUN cat >> /etc/bash.bashrc << 'EOF'

# Gemini shared tools configuration
export PATH="/opt/gemini-shared/bin:$PATH"
export PYTHONPATH="/opt/gemini-shared/lib/python3/site-packages:$PYTHONPATH"
export NODE_PATH="/opt/gemini-shared/lib/node_modules:$NODE_PATH"
export PIP_TARGET="/opt/gemini-shared/lib/python3/site-packages"
export NPM_CONFIG_PREFIX="/opt/gemini-shared"
EOF

# Create entrypoint script to handle volume-mounted /usr/local
# This ensures symlinks are recreated after volume mount overwrites them
RUN cat > /entrypoint.sh << 'ENTRYPOINT_EOF'
#!/bin/bash
set -e

# Restore essential symlinks if they're missing (volume mount may overwrite them)
# This runs once at container start

# Node.js symlinks
[ ! -f /usr/local/bin/node ] && [ -f /usr/local/bin/nodejs ] || {
    # If node binary exists in node_modules, create symlink
    if [ -f "/usr/local/lib/node_modules/.bin/node" ]; then
        ln -sf /usr/local/lib/node_modules/.bin/node /usr/local/bin/node 2>/dev/null || true
    fi
}

[ ! -L /usr/local/bin/nodejs ] && [ -f /usr/local/bin/node ] && \
    ln -sf /usr/local/bin/node /usr/local/bin/nodejs 2>/dev/null || true

# npm symlink
[ ! -L /usr/local/bin/npm ] && [ -f /usr/local/lib/node_modules/npm/bin/npm-cli.js ] && \
    ln -sf /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm 2>/dev/null || true

# Gemini CLI symlink - check both possible paths
if [ ! -L /usr/local/bin/gemini ] || [ ! -e /usr/local/bin/gemini ]; then
    if [ -f "/usr/local/lib/node_modules/@google/gemini-cli/dist/index.js" ]; then
        ln -sf /usr/local/lib/node_modules/@google/gemini-cli/dist/index.js /usr/local/bin/gemini
        chmod +x /usr/local/bin/gemini
    elif [ -f "/usr/local/lib/node_modules/@google/gemini-cli/build/cli.js" ]; then
        ln -sf /usr/local/lib/node_modules/@google/gemini-cli/build/cli.js /usr/local/bin/gemini
        chmod +x /usr/local/bin/gemini
    fi
fi

# Python symlinks
[ ! -L /usr/local/bin/python3 ] && [ -f /opt/python3.12/bin/python3 ] && \
    ln -sf /opt/python3.12/bin/python3 /usr/local/bin/python3 2>/dev/null || true
[ ! -L /usr/local/bin/python ] && [ -f /opt/python3.12/bin/python3 ] && \
    ln -sf /opt/python3.12/bin/python3 /usr/local/bin/python 2>/dev/null || true
[ ! -L /usr/local/bin/pip3 ] && [ -f /opt/python3.12/bin/pip3 ] && \
    ln -sf /opt/python3.12/bin/pip3 /usr/local/bin/pip3 2>/dev/null || true
[ ! -L /usr/local/bin/pip ] && [ -f /opt/python3.12/bin/pip3 ] && \
    ln -sf /opt/python3.12/bin/pip3 /usr/local/bin/pip 2>/dev/null || true

# TypeScript/ESLint/Prettier symlinks
[ ! -L /usr/local/bin/tsc ] && [ -f /usr/local/lib/node_modules/typescript/bin/tsc ] && \
    ln -sf /usr/local/lib/node_modules/typescript/bin/tsc /usr/local/bin/tsc 2>/dev/null || true
[ ! -L /usr/local/bin/eslint ] && [ -f /usr/local/lib/node_modules/eslint/bin/eslint.js ] && \
    ln -sf /usr/local/lib/node_modules/eslint/bin/eslint.js /usr/local/bin/eslint 2>/dev/null || true
[ ! -L /usr/local/bin/prettier ] && [ -f /usr/local/lib/node_modules/prettier/bin/prettier.cjs ] && \
    ln -sf /usr/local/lib/node_modules/prettier/bin/prettier.cjs /usr/local/bin/prettier 2>/dev/null || true

# Ensure session manager script is executable
chmod +x /usr/local/bin/session_manager.py 2>/dev/null || true
chmod +x /usr/local/bin/gemini-namespace-launcher 2>/dev/null || true

# Execute the main command (supervisord)
exec "$@"
ENTRYPOINT_EOF

RUN chmod +x /entrypoint.sh && \
    sed -i 's/\r$//' /entrypoint.sh

# Configure supervisord with enhanced settings
RUN mkdir -p /var/log/supervisor && \
    chmod 755 /var/log/supervisor && \
    cat > /etc/supervisor/conf.d/supervisord.conf << 'EOF'
[unix_http_server]
file=/var/run/supervisor.sock
chmod=0700

[supervisord]
nodaemon=true
logfile=/var/log/supervisor/supervisord.log
pidfile=/var/run/supervisord.pid
childlogdir=/var/log/supervisor
user=root

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

[supervisorctl]
serverurl=unix:///var/run/supervisor.sock

[program:gemini-session-manager]
command=%(ENV_PYTHON_BIN)s /usr/local/bin/session_manager.py
autostart=true
autorestart=unexpected
startsecs=10
startretries=3
stopasgroup=true
killasgroup=true
stopsignal=TERM
stopwaitsecs=10
stdout_logfile=/var/log/gemini-session-manager.log
stdout_logfile_maxbytes=10MB
stdout_logfile_backups=3
stderr_logfile=/var/log/gemini-session-manager.err
stderr_logfile_maxbytes=10MB
stderr_logfile_backups=3
user=root
priority=100
environment=PATH="%(ENV_PYTHON_HOME)s/bin:/usr/local/bin:/usr/bin:/bin",PYTHON_BIN="%(ENV_PYTHON_BIN)s"
EOF

# Switch back to root for supervisord
USER root
WORKDIR /

# Entrypoint handles symlink restoration after volume mounts
ENTRYPOINT ["/entrypoint.sh"]

# Start supervisord (healthcheck defined in docker-compose.yml only to avoid duplication)
CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]
