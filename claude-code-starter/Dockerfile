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
    chgrp root /usr/local/bin /usr/local/lib

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

# Create session cleanup daemon with proper error handling
RUN echo '#!/bin/bash' > /usr/local/bin/claude-cleanup-daemon && \
    echo 'set -euo pipefail' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '# Configuration' >> /usr/local/bin/claude-cleanup-daemon && \
    echo 'readonly SESSION_DIR="/var/run/claude-sessions"' >> /usr/local/bin/claude-cleanup-daemon && \
    echo 'readonly STALE_TIMEOUT=120' >> /usr/local/bin/claude-cleanup-daemon && \
    echo 'readonly CHECK_INTERVAL=30' >> /usr/local/bin/claude-cleanup-daemon && \
    echo 'readonly LOCK_FILE="/var/lock/claude-cleanup.lock"' >> /usr/local/bin/claude-cleanup-daemon && \
    echo 'readonly LOG_FILE="/var/log/claude-cleanup.log"' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '# Ensure session directory exists' >> /usr/local/bin/claude-cleanup-daemon && \
    echo 'mkdir -p "$SESSION_DIR"' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '# Logging function' >> /usr/local/bin/claude-cleanup-daemon && \
    echo 'log() {' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '    echo "[$(date +"%Y-%m-%d %H:%M:%S")] $1" | tee -a "$LOG_FILE"' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '}' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '# Cleanup function with file-based tracking' >> /usr/local/bin/claude-cleanup-daemon && \
    echo 'cleanup_sessions() {' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '    exec 200>"$LOCK_FILE"' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '    if ! flock -n 200; then' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '        log "Another cleanup instance is running"' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '        return' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '    fi' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '    ' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '    find "$SESSION_DIR" -name "*.pid" -type f | while read -r pidfile; do' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '        if [[ ! -r "$pidfile" ]]; then' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '            continue' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '        fi' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '        ' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '        # Read PID with timeout' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '        if ! timeout 1s head -n1 "$pidfile" > /tmp/pid.tmp 2>/dev/null; then' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '            log "Failed to read $pidfile, removing"' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '            rm -f "$pidfile"' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '            continue' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '        fi' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '        ' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '        pid=$(cat /tmp/pid.tmp)' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '        ' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '        # Validate PID format' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '        if ! [[ "$pid" =~ ^[0-9]+$ ]]; then' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '            log "Invalid PID format in $pidfile"' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '            rm -f "$pidfile"' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '            continue' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '        fi' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '        ' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '        # Check if process exists' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '        if ! kill -0 "$pid" 2>/dev/null; then' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '            log "Removing dead session $pidfile (PID: $pid)"' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '            rm -f "$pidfile"' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '            continue' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '        fi' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '        ' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '        # Check if terminal is attached (active session)' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '        if ls /proc/$pid/fd/* 2>/dev/null | xargs -r readlink | grep -q "pts/"; then' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '            continue  # Active session with terminal' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '        fi' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '        ' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '        # Check session age from file timestamp' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '        file_age=$(( $(date +%s) - $(stat -c %Y "$pidfile" 2>/dev/null || echo 0) ))' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '        if [ "$file_age" -gt "$STALE_TIMEOUT" ]; then' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '            log "Terminating stale session $pidfile (PID: $pid, age: ${file_age}s)"' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '            kill -TERM "$pid" 2>/dev/null || true' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '            rm -f "$pidfile"' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '        fi' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '    done' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '}' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '# Main loop with error recovery' >> /usr/local/bin/claude-cleanup-daemon && \
    echo 'log "Claude cleanup daemon started"' >> /usr/local/bin/claude-cleanup-daemon && \
    echo 'while true; do' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '    cleanup_sessions || log "Error in cleanup_sessions"' >> /usr/local/bin/claude-cleanup-daemon && \
    echo '    sleep "$CHECK_INTERVAL"' >> /usr/local/bin/claude-cleanup-daemon && \
    echo 'done' >> /usr/local/bin/claude-cleanup-daemon && \
    chmod +x /usr/local/bin/claude-cleanup-daemon && \
    # Simple session starter script
    printf '#!/bin/bash\ncd "${1:-/project}"\nshift\nexec claude "$@"\n' > /usr/local/bin/claude-session && \
    chmod +x /usr/local/bin/claude-session && \
    # Configuration for shared tools
    echo 'export PATH="/opt/claude-shared/bin:$PATH"' >> /etc/bash.bashrc && \
    echo 'export PYTHONPATH="/opt/claude-shared/lib/python3/site-packages:$PYTHONPATH"' >> /etc/bash.bashrc && \
    echo 'export NODE_PATH="/opt/claude-shared/lib/node_modules:$NODE_PATH"' >> /etc/bash.bashrc && \
    echo 'export PIP_TARGET="/opt/claude-shared/lib/python3/site-packages"' >> /etc/bash.bashrc && \
    echo 'export NPM_CONFIG_PREFIX="/opt/claude-shared"' >> /etc/bash.bashrc

# Configure supervisord
RUN mkdir -p /var/log/supervisor && \
    chmod 755 /var/log/supervisor && \
    echo '[unix_http_server]' > /etc/supervisor/conf.d/supervisord.conf && \
    echo 'file=/var/run/supervisor.sock' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'chmod=0700' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo '' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo '[supervisord]' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'nodaemon=true' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'logfile=/var/log/supervisor/supervisord.log' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'pidfile=/var/run/supervisord.pid' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo '' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo '[rpcinterface:supervisor]' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo '' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo '[supervisorctl]' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'serverurl=unix:///var/run/supervisor.sock' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo '' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo '[program:claude-cleanup]' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'command=/usr/local/bin/claude-cleanup-daemon' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'autostart=true' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'autorestart=true' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'stderr_logfile=/var/log/claude-cleanup.err.log' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'stdout_logfile=/var/log/claude-cleanup.out.log' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'user=root' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'priority=100' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'startsecs=2' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'startretries=3' >> /etc/supervisor/conf.d/supervisord.conf

# Switch back to root for supervisord
USER root
WORKDIR /

# Healthcheck - verify supervisord is running
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD supervisorctl status claude-cleanup | grep -q RUNNING || exit 1

# Start supervisord
CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]