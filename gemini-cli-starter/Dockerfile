# Build stage for Node.js packages
FROM node:22-slim AS node-builder

# Install Gemini CLI and development tools
RUN npm install -g typescript eslint prettier && \
    npm install -g @google/gemini-cli && \
    npm cache clean --force

# Main image
FROM ubuntu:24.04

# Environment configuration
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONIOENCODING=utf-8 \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8 \
    GEMINI_MODEL=gemini-3.0-pro \
    PATH="/usr/local/lib/node_modules/.bin:${PATH}"

# Copy Node.js and packages from build stage
COPY --from=node-builder /usr/local/bin/node /usr/local/bin/
COPY --from=node-builder /usr/local/lib/node_modules /usr/local/lib/node_modules

# Create symlinks and install base packages
RUN ln -s /usr/local/bin/node /usr/local/bin/nodejs && \
    ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm && \
    # Create symlink for gemini
    if [ -f "/usr/local/lib/node_modules/@google/gemini-cli/build/cli.js" ]; then \
        ln -sf /usr/local/lib/node_modules/@google/gemini-cli/build/cli.js /usr/local/bin/gemini && \
        chmod +x /usr/local/bin/gemini && \
        echo "Gemini symlink created successfully"; \
    else \
        echo "Gemini CLI cli.js not found, trying alternative path"; \
        find /usr/local/lib/node_modules -name "cli.js" -path "*gemini*" 2>/dev/null || true; \
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

# Install Python 3.12.4 from deadsnakes PPA
RUN add-apt-repository ppa:deadsnakes/ppa -y && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    python3.12 python3.12-venv python3.12-dev python3.12-distutils && \
    # Set python3.12 as default python3 and python
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1 && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1 && \
    # Install pip 24.0
    curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12 && \
    python3.12 -m pip install --upgrade pip==24.0 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Eclipse Temurin JDK 17 from Adoptium repository
RUN apt-get update && apt-get install -y --no-install-recommends wget apt-transport-https gnupg && \
    wget -qO - https://packages.adoptium.net/artifactory/api/gpg/key/public | gpg --dearmor | tee /etc/apt/trusted.gpg.d/adoptium.gpg > /dev/null && \
    echo "deb https://packages.adoptium.net/artifactory/deb $(awk -F= '/^VERSION_CODENAME/{print$2}' /etc/os-release) main" | tee /etc/apt/sources.list.d/adoptium.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends temurin-17-jdk && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

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
    chmod 755 /var/run/gemini-sessions

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

# Python packages
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
RUN echo 'export CHROME_BIN=/usr/bin/chromium-browser' >> /etc/bash.bashrc && \
    echo 'export CHROME_DRIVER=/usr/bin/chromedriver' >> /etc/bash.bashrc

# Helper script for Gemini CLI installation + fix permissions for auto-update
RUN echo '#!/bin/bash' > /usr/local/bin/check-gemini && \
    echo 'if ! which gemini >/dev/null 2>&1; then' >> /usr/local/bin/check-gemini && \
    echo '    echo "Gemini CLI not found. Attempting to install..."' >> /usr/local/bin/check-gemini && \
    echo '    npm install -g @google/gemini-cli && \' >> /usr/local/bin/check-gemini && \
    echo '    echo "Gemini CLI installed successfully!" || \' >> /usr/local/bin/check-gemini && \
    echo '    echo "Failed to install Gemini CLI"' >> /usr/local/bin/check-gemini && \
    echo 'fi' >> /usr/local/bin/check-gemini && \
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

# Create namespace launcher script
RUN echo '#!/bin/bash' > /usr/local/bin/gemini-namespace-launcher && \
    echo '# Gemini namespace launcher - creates isolated mount namespace per session' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '# Get project path from environment' >> /usr/local/bin/gemini-namespace-launcher && \
    echo 'PROJECT_PATH="${PROJECT_PATH}"' >> /usr/local/bin/gemini-namespace-launcher && \
    echo 'SESSION_ID="${SESSION_ID}"' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '# Check if project path provided' >> /usr/local/bin/gemini-namespace-launcher && \
    echo 'if [ -z "$PROJECT_PATH" ]; then' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    echo "Error: No project path provided"' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    exit 1' >> /usr/local/bin/gemini-namespace-launcher && \
    echo 'fi' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '# Cleanup function for unmounting' >> /usr/local/bin/gemini-namespace-launcher && \
    echo 'cleanup() {' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    # Unmount project directory' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    umount /project 2>/dev/null || true' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    # Unmount hidden directories' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    umount /host 2>/dev/null || true' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    umount /host_c 2>/dev/null || true' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    umount /host_d 2>/dev/null || true' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    # Clean temporary directories' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    rm -rf /tmp/empty 2>/dev/null || true' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '}' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '# Create new mount namespace and run Gemini' >> /usr/local/bin/gemini-namespace-launcher && \
    echo 'exec unshare --mount bash -c '"'"'' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    # Inside new namespace' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    ' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    # Set up trap for cleanup' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    trap cleanup EXIT INT TERM' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    ' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    # Check which host mount to use' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    if [ -d "/host${PROJECT_PATH}" ]; then' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '        # Linux style mount' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '        PROJECT_SOURCE="/host${PROJECT_PATH}"' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    elif [ -d "/host_c${PROJECT_PATH#/c}" ] && [[ "$PROJECT_PATH" == /c/* ]]; then' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '        # Windows C: drive' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '        PROJECT_SOURCE="/host_c${PROJECT_PATH#/c}"' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    elif [ -d "/host_d${PROJECT_PATH#/d}" ] && [[ "$PROJECT_PATH" == /d/* ]]; then' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '        # Windows D: drive' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '        PROJECT_SOURCE="/host_d${PROJECT_PATH#/d}"' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    else' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '        echo "Error: Cannot find project at any expected mount point"' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '        echo "Looking for: $PROJECT_PATH"' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '        echo "Tried: /host${PROJECT_PATH}, /host_c${PROJECT_PATH#/c}, /host_d${PROJECT_PATH#/d}"' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '        exit 1' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    fi' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    ' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    # Create project mount point' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    mkdir -p /project' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    ' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    # Bind mount the project' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    mount --bind "$PROJECT_SOURCE" /project' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    mount -o remount,rw /project' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    ' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    # Hide host mounts from the user' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    # Create empty directories to hide the mounts' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    mkdir -p /tmp/empty' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    mount --bind /tmp/empty /host 2>/dev/null || true' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    mount --bind /tmp/empty /host_c 2>/dev/null || true' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    mount --bind /tmp/empty /host_d 2>/dev/null || true' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    ' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    # Switch to gemini user and run gemini' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    cd /project' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    ' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    # Set default Gemini configuration for Gemini 3 Pro' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    if [ ! -f "/home/gemini/.gemini/settings.json" ]; then' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '        mkdir -p /home/gemini/.gemini' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '        cat > /home/gemini/.gemini/settings.json << GEMINI_CONFIG' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '{' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '  "theme": "Default",' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '  "selectedAuthType": "oauth-personal",' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '  "previewEnabled": true' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '}' >> /usr/local/bin/gemini-namespace-launcher && \
    echo 'GEMINI_CONFIG' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '        chown -R gemini:gemini /home/gemini/.gemini' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    fi' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    ' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    # Run gemini with Gemini 3 Pro model' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    exec sudo -u gemini -E HOME=/home/gemini bash -c "cd /project && gemini -m pro \$@"' >> /usr/local/bin/gemini-namespace-launcher && \
    echo ''"'"' "$@"' >> /usr/local/bin/gemini-namespace-launcher && \
    chmod +x /usr/local/bin/gemini-namespace-launcher

# Create enhanced session cleanup daemon with security measures
RUN cat > /usr/local/bin/gemini-cleanup-daemon << 'EOF'
#!/bin/bash
set -euo pipefail

# Configuration
readonly SESSION_DIR="/var/run/gemini-sessions"
readonly STALE_TIMEOUT=120
readonly CHECK_INTERVAL=30
readonly LOCK_FILE="/var/lock/gemini-cleanup.lock"
readonly LOG_FILE="/var/log/gemini-cleanup.log"
readonly MAX_LOG_SIZE=$((10 * 1024 * 1024))  # 10MB

# Ensure session directory exists with proper permissions
mkdir -p "$SESSION_DIR"
chown gemini-cleanup:gemini-cleanup "$SESSION_DIR"
chmod 755 "$SESSION_DIR"

# Log rotation
rotate_log() {
    if [[ -f "$LOG_FILE" ]] && [[ $(stat -c%s "$LOG_FILE") -gt $MAX_LOG_SIZE ]]; then
        mv "$LOG_FILE" "${LOG_FILE}.old"
        touch "$LOG_FILE"
        chown gemini-cleanup:gemini-cleanup "$LOG_FILE"
    fi
}

# Enhanced logging with levels
log() {
    local level="${1:-INFO}"
    local message="${2:-}"
    rotate_log
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] [${level}] ${message}" | tee -a "$LOG_FILE"
}

# Validate PID file content
validate_pid_file() {
    local pidfile="$1"
    local content

    # Read file with timeout
    if ! content=$(timeout 1s cat "$pidfile" 2>/dev/null); then
        return 1
    fi

    # Try to parse as JSON first (new format)
    if command -v jq >/dev/null && jq -e . >/dev/null 2>&1 <<< "$content"; then
        local pid=$(jq -r '.host_pid // empty' <<< "$content")
        if [[ "$pid" =~ ^[0-9]+$ ]]; then
            echo "$pid"
            return 0
        fi
    fi

    # Fallback to old format (first line is PID)
    local pid=$(echo "$content" | head -1)
    if [[ "$pid" =~ ^[0-9]+$ ]]; then
        echo "$pid"
        return 0
    fi

    return 1
}

# Check if process belongs to Gemini session
is_gemini_process() {
    local pid="$1"

    # Check if process exists and belongs to gemini session
    if [[ -r "/proc/$pid/environ" ]]; then
        # Check for Gemini session markers
        if grep -q "GEMINI_SESSION\|SESSION_ID" "/proc/$pid/environ" 2>/dev/null; then
            return 0
        fi
    fi

    return 1
}

# Cleanup function with enhanced safety
cleanup_sessions() {
    local cleanup_count=0
    local error_count=0

    # Acquire exclusive lock with timeout
    exec 200>"$LOCK_FILE"
    if ! flock -w 5 -x 200; then
        log "WARN" "Failed to acquire lock within 5 seconds"
        return
    fi

    log "DEBUG" "Starting cleanup cycle"

    # Process each PID file
    find "$SESSION_DIR" -name "*.pid" -type f -print0 | while IFS= read -r -d '' pidfile; do
        local basename=$(basename "$pidfile")

        # Skip temporary files
        if [[ "$basename" =~ ^\.tmp_ ]]; then
            continue
        fi

        # Validate and extract PID
        local pid
        if ! pid=$(validate_pid_file "$pidfile"); then
            log "WARN" "Invalid PID file format: $pidfile"
            rm -f "$pidfile"
            ((error_count++))
            continue
        fi

        # Check if process exists
        if ! kill -0 "$pid" 2>/dev/null; then
            log "INFO" "Removing PID file for dead process: $basename (PID: $pid)"
            rm -f "$pidfile"
            ((cleanup_count++))
            continue
        fi

        # Verify it's actually a Gemini process
        if ! is_gemini_process "$pid"; then
            log "WARN" "PID $pid is not a Gemini process, removing stale PID file"
            rm -f "$pidfile"
            ((error_count++))
            continue
        fi

        # Check if terminal is attached (active session)
        if find /proc/$pid/fd -type l -exec readlink {} \; 2>/dev/null | grep -q "pts/"; then
            log "DEBUG" "Skipping active session: $basename (PID: $pid)"
            continue
        fi

        # Check session age
        local file_age=$(( $(date +%s) - $(stat -c %Y "$pidfile" 2>/dev/null || echo 0) ))
        if [[ $file_age -gt $STALE_TIMEOUT ]]; then
            log "INFO" "Terminating stale session: $basename (PID: $pid, age: ${file_age}s)"

            # Send SIGTERM first, then SIGKILL if needed
            if kill -TERM "$pid" 2>/dev/null; then
                sleep 2
                if kill -0 "$pid" 2>/dev/null; then
                    log "WARN" "Process $pid didn't terminate, sending SIGKILL"
                    kill -KILL "$pid" 2>/dev/null || true
                fi
            fi

            rm -f "$pidfile"
            ((cleanup_count++))
        fi
    done

    # Release lock
    flock -u 200

    if [[ $cleanup_count -gt 0 ]] || [[ $error_count -gt 0 ]]; then
        log "INFO" "Cleanup cycle completed: $cleanup_count sessions cleaned, $error_count errors"
    fi
}

# Health monitoring file
update_health() {
    echo "$(date +%s)" > /var/run/gemini-cleanup.health
}

# Signal handlers
trap 'log "INFO" "Received SIGTERM, shutting down..."; exit 0' TERM
trap 'log "INFO" "Received SIGINT, shutting down..."; exit 0' INT

# Main loop with health monitoring
log "INFO" "Gemini cleanup daemon started (PID: $$)"

while true; do
    update_health

    # Run cleanup
    if ! cleanup_sessions; then
        log "ERROR" "Cleanup cycle failed"
    fi

    sleep "$CHECK_INTERVAL"
done
EOF

RUN chmod +x /usr/local/bin/gemini-cleanup-daemon && \
    chown root:root /usr/local/bin/gemini-cleanup-daemon && \
    # Simple session starter script
    printf '#!/bin/bash\ncd "${1:-/project}"\nshift\nexec gemini "$@"\n' > /usr/local/bin/gemini-session && \
    chmod +x /usr/local/bin/gemini-session && \
    # Configuration for shared tools
    echo 'export PATH="/opt/gemini-shared/bin:$PATH"' >> /etc/bash.bashrc && \
    echo 'export PYTHONPATH="/opt/gemini-shared/lib/python3/site-packages:$PYTHONPATH"' >> /etc/bash.bashrc && \
    echo 'export NODE_PATH="/opt/gemini-shared/lib/node_modules:$NODE_PATH"' >> /etc/bash.bashrc && \
    echo 'export PIP_TARGET="/opt/gemini-shared/lib/python3/site-packages"' >> /etc/bash.bashrc && \
    echo 'export NPM_CONFIG_PREFIX="/opt/gemini-shared"' >> /etc/bash.bashrc && \
    echo 'export GEMINI_MODEL="gemini-3.0-pro"' >> /etc/bash.bashrc

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
