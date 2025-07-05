# Build stage for Node.js packages
FROM node:20-slim AS node-builder

# Install Claude Code and development tools
RUN npm install -g typescript eslint prettier && \
    npm install -g @anthropic-ai/claude-code || \
    (echo "WARNING: Claude Code not available in npm registry" && \
     echo "Container will work as dev environment") && \
    npm cache clean --force

# Main image
FROM ubuntu:24.04

# Environment configuration
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONIOENCODING=utf-8 \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8 \
    CLAUDE_DEFAULT_MODEL=opus \
    CLAUDE_MODEL=opus \
    ANTHROPIC_MODEL=opus \
    PATH="/usr/local/lib/node_modules/.bin:${PATH}"

# Copy Node.js and packages from build stage
COPY --from=node-builder /usr/local/bin/node /usr/local/bin/
COPY --from=node-builder /usr/local/lib/node_modules /usr/local/lib/node_modules

# Create symlinks and install base packages
RUN ln -s /usr/local/bin/node /usr/local/bin/nodejs && \
    ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm && \
    # Tworzenie symlinku dla claude
    if [ -f "/usr/local/lib/node_modules/@anthropic-ai/claude-code/cli.js" ]; then \
        ln -sf /usr/local/lib/node_modules/@anthropic-ai/claude-code/cli.js /usr/local/bin/claude && \
        chmod +x /usr/local/bin/claude && \
        echo "Claude symlink created successfully"; \
    else \
        echo "Claude Code cli.js not found"; \
    fi && \
    # Symlinki dla innych narzędzi
    ln -s /usr/local/lib/node_modules/typescript/bin/tsc /usr/local/bin/tsc 2>/dev/null || true && \
    ln -s /usr/local/lib/node_modules/eslint/bin/eslint.js /usr/local/bin/eslint 2>/dev/null || true && \
    ln -s /usr/local/lib/node_modules/prettier/bin/prettier.cjs /usr/local/bin/prettier 2>/dev/null || true && \
    # Podstawowe pakiety - instalujemy tylko to czego nie ma
    apt-get update && apt-get install -y --no-install-recommends \
    sudo util-linux \
    curl wget \
    gnupg lsb-release \
    software-properties-common apt-transport-https \
    git vim nano zip unzip xz-utils \
    python3 python3-pip python3-venv python3-dev \
    build-essential pkg-config \
    # Java i Maven
    openjdk-17-jdk-headless maven \
    # Supervisor for process management
    supervisor \
    && ln -s /usr/bin/python3 /usr/bin/python \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Tworzenie użytkownika claude z sudo i odpowiednimi uprawnieniami
RUN useradd -m -s /bin/bash claude && \
    usermod -aG sudo claude && \
    usermod -aG root claude && \
    echo "claude ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/claude && \
    chmod 0440 /etc/sudoers.d/claude && \
    # Uprawnienia dla apt - claude może instalować pakiety
    chmod -R g+w /var/lib/apt /var/cache/apt && \
    chgrp -R root /var/lib/apt /var/cache/apt && \
    # Uprawnienia dla innych katalogów systemowych które mogą być potrzebne
    chmod g+w /usr/local/bin /usr/local/lib && \
    chgrp root /usr/local/bin /usr/local/lib && \
    # Create dedicated user for cleanup daemon
    useradd -r -s /bin/false -d /nonexistent -c "Claude Cleanup Daemon" claude-cleanup && \
    mkdir -p /var/log /var/run/claude-sessions && \
    chown claude-cleanup:claude-cleanup /var/run/claude-sessions && \
    chmod 755 /var/run/claude-sessions

# Instalacja dodatkowych pakietów
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Gradle
    gradle \
    # Pozostałe języki
    ruby \
    php php-cli php-mbstring php-xml php-curl php-zip composer \
    # Narzędzia deweloperskie
    tree jq net-tools iputils-ping htop \
    ripgrep fd-find fzf shellcheck \
    # Chrome dla Selenium
    chromium-browser chromium-chromedriver \
    # Docker CLI
    docker.io \
    # Media
    imagemagick ffmpeg \
    # Database
    sqlite3 \
    # LaTeX - pełny zestaw z dodatkami
    texlive texlive-latex-extra texlive-fonts-recommended \
    texlive-lang-polish biber latexmk \
    texlive-xetex texlive-fonts-extra fonts-roboto \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Python packages - dla Ubuntu 24.04, nie aktualizujemy systemowych pakietów
RUN python3 -m pip install --break-system-packages --no-cache-dir \
    requests beautifulsoup4 anthropic \
    pytest black flake8 \
    selenium==4.18.1 fastapi==0.109.2 uvicorn==0.27.1 \
    pydantic==2.6.1 pyyaml==6.0.1 \
    lxml==5.1.0 aiofiles==23.2.1 python-multipart==0.0.9 \
    httpx==0.26.0 websockets==12.0 rich==13.7.0 \
    seaborn matplotlib pandas numpy scipy

# PyTorch osobno z własnym indeksem - opcjonalne, może się nie udać
RUN python3 -m pip install --break-system-packages --no-cache-dir \
    torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu || \
    echo "Warning: PyTorch installation failed, continuing without it"

# Chrome environment variables
RUN echo 'export CHROME_BIN=/usr/bin/chromium-browser' >> /etc/bash.bashrc && \
    echo 'export CHROME_DRIVER=/usr/bin/chromedriver' >> /etc/bash.bashrc

# Skrypt pomocniczy do instalacji Claude Code + fix permissions dla auto-update
RUN echo '#!/bin/bash' > /usr/local/bin/check-claude && \
    echo 'if ! which claude >/dev/null 2>&1; then' >> /usr/local/bin/check-claude && \
    echo '    echo "Claude Code not found. Attempting to install..."' >> /usr/local/bin/check-claude && \
    echo '    npm install -g @anthropic-ai/claude-code && \' >> /usr/local/bin/check-claude && \
    echo '    echo "Claude Code installed successfully!" || \' >> /usr/local/bin/check-claude && \
    echo '    echo "Failed to install Claude Code"' >> /usr/local/bin/check-claude && \
    echo 'fi' >> /usr/local/bin/check-claude && \
    chmod +x /usr/local/bin/check-claude && \
    # Fix npm permissions for claude user to allow auto-updates
    # Give claude ownership of the entire @anthropic-ai directory
    chown -R claude:claude /usr/local/lib/node_modules/@anthropic-ai && \
    chmod -R 755 /usr/local/lib/node_modules/@anthropic-ai && \
    # Create npm cache directory with correct permissions
    mkdir -p /home/claude/.npm && \
    chown -R claude:claude /home/claude/.npm && \
    # Allow claude to run npm commands as root for global updates
    echo "claude ALL=(root) NOPASSWD: /usr/bin/npm" >> /etc/sudoers.d/claude

# Create directory structure for shared tools
RUN mkdir -p /opt/claude-shared/{bin,lib,share} \
    /opt/claude-shared/lib/{python3/site-packages,node_modules} && \
    chown -R claude:claude /opt/claude-shared && \
    chmod -R g+w /opt/claude-shared && \
    chgrp -R root /opt/claude-shared

# Create namespace launcher script
RUN echo '#!/bin/bash' > /usr/local/bin/claude-namespace-launcher && \
    echo '# Claude namespace launcher - creates isolated mount namespace per session' >> /usr/local/bin/claude-namespace-launcher && \
    echo '' >> /usr/local/bin/claude-namespace-launcher && \
    echo '# Get project path from environment' >> /usr/local/bin/claude-namespace-launcher && \
    echo 'PROJECT_PATH="${PROJECT_PATH}"' >> /usr/local/bin/claude-namespace-launcher && \
    echo 'SESSION_ID="${SESSION_ID}"' >> /usr/local/bin/claude-namespace-launcher && \
    echo '' >> /usr/local/bin/claude-namespace-launcher && \
    echo '# Check if project path provided' >> /usr/local/bin/claude-namespace-launcher && \
    echo 'if [ -z "$PROJECT_PATH" ]; then' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    echo "Error: No project path provided"' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    exit 1' >> /usr/local/bin/claude-namespace-launcher && \
    echo 'fi' >> /usr/local/bin/claude-namespace-launcher && \
    echo '' >> /usr/local/bin/claude-namespace-launcher && \
    echo '# Cleanup function for unmounting' >> /usr/local/bin/claude-namespace-launcher && \
    echo 'cleanup() {' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    # Unmount project directory' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    umount /project 2>/dev/null || true' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    # Unmount hidden directories' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    umount /host 2>/dev/null || true' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    umount /host_c 2>/dev/null || true' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    umount /host_d 2>/dev/null || true' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    # Clean temporary directories' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    rm -rf /tmp/empty 2>/dev/null || true' >> /usr/local/bin/claude-namespace-launcher && \
    echo '}' >> /usr/local/bin/claude-namespace-launcher && \
    echo '' >> /usr/local/bin/claude-namespace-launcher && \
    echo '# Create new mount namespace and run Claude' >> /usr/local/bin/claude-namespace-launcher && \
    echo 'exec unshare --mount bash -c '"'"'' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    # Inside new namespace' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    ' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    # Set up trap for cleanup' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    trap cleanup EXIT INT TERM' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    ' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    # Check which host mount to use' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    if [ -d "/host${PROJECT_PATH}" ]; then' >> /usr/local/bin/claude-namespace-launcher && \
    echo '        # Linux style mount' >> /usr/local/bin/claude-namespace-launcher && \
    echo '        PROJECT_SOURCE="/host${PROJECT_PATH}"' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    elif [ -d "/host_c${PROJECT_PATH#/c}" ] && [[ "$PROJECT_PATH" == /c/* ]]; then' >> /usr/local/bin/claude-namespace-launcher && \
    echo '        # Windows C: drive' >> /usr/local/bin/claude-namespace-launcher && \
    echo '        PROJECT_SOURCE="/host_c${PROJECT_PATH#/c}"' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    elif [ -d "/host_d${PROJECT_PATH#/d}" ] && [[ "$PROJECT_PATH" == /d/* ]]; then' >> /usr/local/bin/claude-namespace-launcher && \
    echo '        # Windows D: drive' >> /usr/local/bin/claude-namespace-launcher && \
    echo '        PROJECT_SOURCE="/host_d${PROJECT_PATH#/d}"' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    else' >> /usr/local/bin/claude-namespace-launcher && \
    echo '        echo "Error: Cannot find project at any expected mount point"' >> /usr/local/bin/claude-namespace-launcher && \
    echo '        echo "Looking for: $PROJECT_PATH"' >> /usr/local/bin/claude-namespace-launcher && \
    echo '        echo "Tried: /host${PROJECT_PATH}, /host_c${PROJECT_PATH#/c}, /host_d${PROJECT_PATH#/d}"' >> /usr/local/bin/claude-namespace-launcher && \
    echo '        exit 1' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    fi' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    ' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    # Create project mount point' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    mkdir -p /project' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    ' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    # Bind mount the project' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    mount --bind "$PROJECT_SOURCE" /project' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    mount -o remount,rw /project' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    ' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    # Hide host mounts from the user' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    # Create empty directories to hide the mounts' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    mkdir -p /tmp/empty' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    mount --bind /tmp/empty /host 2>/dev/null || true' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    mount --bind /tmp/empty /host_c 2>/dev/null || true' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    mount --bind /tmp/empty /host_d 2>/dev/null || true' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    ' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    # Switch to claude user and run claude' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    cd /project' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    # Set default theme if not already configured' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    if [ ! -f "/home/claude/.claude.json" ]; then' >> /usr/local/bin/claude-namespace-launcher && \
    echo '        mkdir -p /home/claude' >> /usr/local/bin/claude-namespace-launcher && \
    echo '        cat > /home/claude/.claude.json << CLAUDE_CONFIG' >> /usr/local/bin/claude-namespace-launcher && \
    echo '{' >> /usr/local/bin/claude-namespace-launcher && \
    echo '  "theme": "dark-daltonized",' >> /usr/local/bin/claude-namespace-launcher && \
    echo '  "model": "opus",' >> /usr/local/bin/claude-namespace-launcher && \
    echo '  "hasCompletedOnboarding": true,' >> /usr/local/bin/claude-namespace-launcher && \
    echo '  "hasTrustDialogAccepted": true' >> /usr/local/bin/claude-namespace-launcher && \
    echo '}' >> /usr/local/bin/claude-namespace-launcher && \
    echo 'CLAUDE_CONFIG' >> /usr/local/bin/claude-namespace-launcher && \
    echo '        chown claude:claude /home/claude/.claude.json' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    fi' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    exec sudo -u claude -E HOME=/home/claude bash -c "cd /project && claude --permission-mode bypassPermissions --dangerously-skip-permissions \$@"' >> /usr/local/bin/claude-namespace-launcher && \
    echo ''"'"' "$@"' >> /usr/local/bin/claude-namespace-launcher && \
    chmod +x /usr/local/bin/claude-namespace-launcher

# Create enhanced session cleanup daemon with security measures
RUN cat > /usr/local/bin/claude-cleanup-daemon << 'EOF'
#!/bin/bash
set -euo pipefail

# Configuration
readonly SESSION_DIR="/var/run/claude-sessions"
readonly STALE_TIMEOUT=120
readonly CHECK_INTERVAL=30
readonly LOCK_FILE="/var/lock/claude-cleanup.lock"
readonly LOG_FILE="/var/log/claude-cleanup.log"
readonly MAX_LOG_SIZE=$((10 * 1024 * 1024))  # 10MB

# Ensure session directory exists with proper permissions
mkdir -p "$SESSION_DIR"
chown claude-cleanup:claude-cleanup "$SESSION_DIR"
chmod 755 "$SESSION_DIR"

# Log rotation
rotate_log() {
    if [[ -f "$LOG_FILE" ]] && [[ $(stat -c%s "$LOG_FILE") -gt $MAX_LOG_SIZE ]]; then
        mv "$LOG_FILE" "${LOG_FILE}.old"
        touch "$LOG_FILE"
        chown claude-cleanup:claude-cleanup "$LOG_FILE"
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

# Check if process belongs to Claude session
is_claude_process() {
    local pid="$1"
    
    # Check if process exists and belongs to claude session
    if [[ -r "/proc/$pid/environ" ]]; then
        # Check for Claude session markers
        if grep -q "CLAUDE_SESSION\|SESSION_ID" "/proc/$pid/environ" 2>/dev/null; then
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
        
        # Verify it's actually a Claude process
        if ! is_claude_process "$pid"; then
            log "WARN" "PID $pid is not a Claude process, removing stale PID file"
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
    echo "$(date +%s)" > /var/run/claude-cleanup.health
}

# Signal handlers
trap 'log "INFO" "Received SIGTERM, shutting down..."; exit 0' TERM
trap 'log "INFO" "Received SIGINT, shutting down..."; exit 0' INT

# Main loop with health monitoring
log "INFO" "Claude cleanup daemon started (PID: $$)"

while true; do
    update_health
    
    # Run cleanup
    if ! cleanup_sessions; then
        log "ERROR" "Cleanup cycle failed"
    fi
    
    sleep "$CHECK_INTERVAL"
done
EOF

RUN chmod +x /usr/local/bin/claude-cleanup-daemon && \
    chown root:root /usr/local/bin/claude-cleanup-daemon && \
    # Simple session starter script
    printf '#!/bin/bash\ncd "${1:-/project}"\nshift\nexec claude "$@"\n' > /usr/local/bin/claude-session && \
    chmod +x /usr/local/bin/claude-session && \
    # Configuration for shared tools
    echo 'export PATH="/opt/claude-shared/bin:$PATH"' >> /etc/bash.bashrc && \
    echo 'export PYTHONPATH="/opt/claude-shared/lib/python3/site-packages:$PYTHONPATH"' >> /etc/bash.bashrc && \
    echo 'export NODE_PATH="/opt/claude-shared/lib/node_modules:$NODE_PATH"' >> /etc/bash.bashrc && \
    echo 'export PIP_TARGET="/opt/claude-shared/lib/python3/site-packages"' >> /etc/bash.bashrc && \
    echo 'export NPM_CONFIG_PREFIX="/opt/claude-shared"' >> /etc/bash.bashrc

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

[program:claude-cleanup]
command=/usr/local/bin/claude-cleanup-daemon
autostart=true
autorestart=unexpected
startsecs=10
startretries=3
stopasgroup=true
killasgroup=true
stopsignal=TERM
stopwaitsecs=10
stdout_logfile=/var/log/claude-cleanup.log
stdout_logfile_maxbytes=10MB
stdout_logfile_backups=3
stderr_logfile=/var/log/claude-cleanup.err
stderr_logfile_maxbytes=10MB
stderr_logfile_backups=3
user=claude-cleanup
priority=100
environment=PATH="/usr/local/bin:/usr/bin:/bin"
EOF

# Switch back to root for supervisord
USER root
WORKDIR /

# Enhanced healthcheck - verify both supervisord and cleanup daemon are functioning
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD bash -c 'supervisorctl status claude-cleanup | grep -q RUNNING && \
               [ -f /var/run/claude-cleanup.health ] && \
               [ $(($(date +%s) - $(cat /var/run/claude-cleanup.health))) -lt 120 ]'

# Start supervisord
CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]