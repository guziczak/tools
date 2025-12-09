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
    PATH="/usr/local/lib/node_modules/.bin:${PATH}"

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
    # Create default Gemini settings with preview features and Gemini 3 Pro model (new format)
    mkdir -p /home/gemini/.gemini && \
    echo '{"model":{"name":"gemini-3-pro-preview"},"security":{"auth":{"selectedType":"oauth-personal"}},"ui":{"theme":"Default"},"general":{"previewFeatures":true}}' > /home/gemini/.gemini/settings.json && \
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

# Create namespace launcher script - uses bash -c to avoid heredoc stdin issues
RUN cat > /usr/local/bin/gemini-namespace-launcher << 'LAUNCHER_EOF'
#!/bin/bash
# Gemini namespace launcher - creates isolated mount namespace per session
# This script preserves stdin for interactive Gemini CLI usage

set -e

# Check if project path provided
if [ -z "$PROJECT_PATH" ]; then
    echo "Error: No project path provided via PROJECT_PATH environment variable"
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

# Create mount namespace and set up isolated environment
# Using unshare with bash -c preserves stdin for interactive use
exec unshare --mount bash -c '
    # Cleanup function
    cleanup() {
        umount /project 2>/dev/null || true
        umount /host 2>/dev/null || true
        umount /host_c 2>/dev/null || true
        umount /host_d 2>/dev/null || true
        rm -rf /tmp/empty 2>/dev/null || true
    }
    trap cleanup EXIT INT TERM

    # Create and mount project directory
    mkdir -p /project
    mount --bind "'"$PROJECT_SOURCE"'" /project
    mount -o remount,rw /project

    # Hide host mounts from the user for security
    mkdir -p /tmp/empty
    mount --bind /tmp/empty /host 2>/dev/null || true
    mount --bind /tmp/empty /host_c 2>/dev/null || true
    mount --bind /tmp/empty /host_d 2>/dev/null || true

    cd /project

    # Run gemini as gemini user - Auto mode will use Gemini 3 Pro when available
    # Using exec to replace shell, preserving stdin/stdout/stderr
    exec sudo -u gemini -E HOME=/home/gemini gemini
'
LAUNCHER_EOF

# Fix line endings and set executable
RUN sed -i 's/\r$//' /usr/local/bin/gemini-namespace-launcher && \
    chmod +x /usr/local/bin/gemini-namespace-launcher

# Create session cleanup daemon - cleans up stale session files based on file age
RUN cat > /usr/local/bin/gemini-cleanup-daemon << 'EOF'
#!/bin/bash
set -euo pipefail

# Configuration
readonly SESSION_DIR="/var/run/gemini-sessions"
readonly STALE_TIMEOUT=300  # 5 minutes - session file not updated means session ended
readonly CHECK_INTERVAL=60
readonly LOCK_FILE="/var/lock/gemini-cleanup.lock"
readonly LOG_FILE="/var/log/gemini-cleanup.log"
readonly MAX_LOG_SIZE=$((10 * 1024 * 1024))  # 10MB

# Log rotation
rotate_log() {
    if [[ -f "$LOG_FILE" ]] && [[ $(stat -c%s "$LOG_FILE" 2>/dev/null || echo 0) -gt $MAX_LOG_SIZE ]]; then
        mv "$LOG_FILE" "${LOG_FILE}.old"
        touch "$LOG_FILE"
    fi
}

# Logging function
log() {
    local level="${1:-INFO}"
    local message="${2:-}"
    rotate_log
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] [${level}] ${message}" >> "$LOG_FILE" 2>/dev/null || true
}

# Cleanup stale session files based on modification time
cleanup_sessions() {
    local cleanup_count=0

    # Ensure session directory exists
    if [[ ! -d "$SESSION_DIR" ]]; then
        return 0
    fi

    # Acquire exclusive lock with timeout
    exec 200>"$LOCK_FILE"
    if ! flock -w 5 -x 200; then
        log "WARN" "Failed to acquire lock"
        return 1
    fi

    # Find and remove stale session files
    # Session files are removed by the host when session ends normally
    # This daemon only cleans up orphaned files (e.g., after crash)
    while IFS= read -r -d '' session_file; do
        local basename
        basename=$(basename "$session_file")

        # Skip temporary files
        if [[ "$basename" =~ ^\.tmp_ ]]; then
            continue
        fi

        # Check file age based on modification time
        local file_mtime file_age
        file_mtime=$(stat -c %Y "$session_file" 2>/dev/null || echo 0)
        file_age=$(( $(date +%s) - file_mtime ))

        if [[ $file_age -gt $STALE_TIMEOUT ]]; then
            log "INFO" "Removing stale session file: $basename (age: ${file_age}s)"
            rm -f "$session_file"
            ((cleanup_count++)) || true
        fi
    done < <(find "$SESSION_DIR" -name "*.session" -type f -print0 2>/dev/null)

    # Release lock
    flock -u 200

    if [[ $cleanup_count -gt 0 ]]; then
        log "INFO" "Cleanup completed: $cleanup_count stale sessions removed"
    fi

    return 0
}

# Health monitoring
update_health() {
    echo "$(date +%s)" > /var/run/gemini-cleanup.health 2>/dev/null || true
}

# Signal handlers
trap 'log "INFO" "Shutting down..."; exit 0' TERM INT

# Main loop
log "INFO" "Gemini cleanup daemon started (PID: $$)"

while true; do
    update_health
    cleanup_sessions || log "WARN" "Cleanup cycle had issues"
    sleep "$CHECK_INTERVAL"
done
EOF

# Fix line endings and set executable
RUN sed -i 's/\r$//' /usr/local/bin/gemini-cleanup-daemon && \
    chmod +x /usr/local/bin/gemini-cleanup-daemon && \
    chown root:root /usr/local/bin/gemini-cleanup-daemon

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

[program:gemini-cleanup]
command=/usr/local/bin/gemini-cleanup-daemon
autostart=true
autorestart=unexpected
startsecs=10
startretries=3
stopasgroup=true
killasgroup=true
stopsignal=TERM
stopwaitsecs=10
stdout_logfile=/var/log/gemini-cleanup.log
stdout_logfile_maxbytes=10MB
stdout_logfile_backups=3
stderr_logfile=/var/log/gemini-cleanup.err
stderr_logfile_maxbytes=10MB
stderr_logfile_backups=3
user=gemini-cleanup
priority=100
environment=PATH="/usr/local/bin:/usr/bin:/bin"
EOF

# Switch back to root for supervisord
USER root
WORKDIR /

# Enhanced healthcheck - verify both supervisord and cleanup daemon are functioning
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD bash -c 'supervisorctl status gemini-cleanup | grep -q RUNNING && \
               [ -f /var/run/gemini-cleanup.health ] && \
               [ $(($(date +%s) - $(cat /var/run/gemini-cleanup.health))) -lt 120 ]'

# Start supervisord
CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]
