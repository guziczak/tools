# Multi-stage build dla szybszego budowania
FROM node:20-slim AS node-builder

# Instalacja Claude Code z weryfikacją
RUN npm install -g typescript eslint prettier && \
    npm install -g @anthropic-ai/claude-code || \
    (echo "WARNING: Claude Code not available in npm registry" && \
     echo "Container will work as dev environment") && \
    npm cache clean --force && \
    # Debug - sprawdzamy co się zainstalowało
    echo "=== Installed packages ===" && \
    npm list -g --depth=0 && \
    echo "=== Looking for claude ===" && \
    find /usr/local -name "claude" -type f -o -type l 2>/dev/null | head -10

# ===== GŁÓWNY OBRAZ =====
FROM ubuntu:24.04

# Build argument dla wyboru wersji
ARG BUILD_VERSION=full

# Ustawienia środowiskowe
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONIOENCODING=utf-8 \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8 \
    CLAUDE_DEFAULT_MODEL=opus \
    CLAUDE_MODEL=opus \
    ANTHROPIC_MODEL=opus \
    PATH="/usr/local/lib/node_modules/.bin:${PATH}" \
    BUILD_VERSION=${BUILD_VERSION}

# Kopiowanie Node.js i pakietów z pierwszego stage'a
COPY --from=node-builder /usr/local/bin/node /usr/local/bin/
COPY --from=node-builder /usr/local/lib/node_modules /usr/local/lib/node_modules

# Tworzenie symlinków i instalacja podstawowych pakietów
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
    curl wget \
    gnupg lsb-release \
    software-properties-common apt-transport-https \
    git vim nano zip unzip xz-utils \
    python3 python3-pip python3-venv python3-dev \
    build-essential pkg-config \
    bubblewrap \
    # Java i Maven - zawsze (potrzebne nawet w slim)
    openjdk-17-jdk-headless maven \
    && ln -s /usr/bin/python3 /usr/bin/python \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Warunkowa instalacja dodatkowych pakietów (tylko dla full)
RUN if [ "$BUILD_VERSION" = "full" ]; then \
        apt-get update && apt-get install -y --no-install-recommends \
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
        # LaTeX - pełny zestaw
        texlive texlive-latex-extra texlive-fonts-recommended \
        texlive-lang-polish biber latexmk \
        && apt-get clean \
        && rm -rf /var/lib/apt/lists/* ; \
    fi

# Python packages - dla Ubuntu 24.04, nie aktualizujemy systemowych pakietów
RUN python3 -m pip install --break-system-packages --no-cache-dir \
        requests beautifulsoup4 anthropic && \
    if [ "$BUILD_VERSION" = "full" ]; then \
        python3 -m pip install --break-system-packages --no-cache-dir \
            pytest black flake8 \
            selenium==4.18.1 fastapi==0.109.2 uvicorn==0.27.1 \
            pydantic==2.6.1 pyyaml==6.0.1 \
            lxml==5.1.0 aiofiles==23.2.1 python-multipart==0.0.9 \
            httpx==0.26.0 websockets==12.0 rich==13.7.0 ; \
    fi

# Chrome environment variables (tylko jeśli full)
RUN if [ "$BUILD_VERSION" = "full" ]; then \
        echo 'export CHROME_BIN=/usr/bin/chromium-browser' >> /etc/bash.bashrc && \
        echo 'export CHROME_DRIVER=/usr/bin/chromedriver' >> /etc/bash.bashrc ; \
    fi

# Skrypt pomocniczy do instalacji Claude Code
RUN echo '#!/bin/bash' > /usr/local/bin/check-claude && \
    echo 'if ! which claude >/dev/null 2>&1; then' >> /usr/local/bin/check-claude && \
    echo '    echo "Claude Code not found. Attempting to install..."' >> /usr/local/bin/check-claude && \
    echo '    npm install -g @anthropic-ai/claude-code && \' >> /usr/local/bin/check-claude && \
    echo '    echo "Claude Code installed successfully!" || \' >> /usr/local/bin/check-claude && \
    echo '    echo "Failed to install Claude Code"' >> /usr/local/bin/check-claude && \
    echo 'fi' >> /usr/local/bin/check-claude && \
    chmod +x /usr/local/bin/check-claude

# Session manager
RUN mkdir -p /var/run/claude-sessions && \
    echo '#!/bin/bash' > /usr/local/bin/claude-session && \
    echo 'set -euo pipefail' >> /usr/local/bin/claude-session && \
    echo '' >> /usr/local/bin/claude-session && \
    echo '# Pobierz argumenty' >> /usr/local/bin/claude-session && \
    echo 'PROJECT_PATH="${1:-/workspace}"' >> /usr/local/bin/claude-session && \
    echo 'shift || true' >> /usr/local/bin/claude-session && \
    echo '' >> /usr/local/bin/claude-session && \
    echo '# Walidacja ścieżki' >> /usr/local/bin/claude-session && \
    echo 'if [ ! -d "$PROJECT_PATH" ]; then' >> /usr/local/bin/claude-session && \
    echo '    echo "Error: Project path does not exist: $PROJECT_PATH" >&2' >> /usr/local/bin/claude-session && \
    echo '    exit 1' >> /usr/local/bin/claude-session && \
    echo 'fi' >> /usr/local/bin/claude-session && \
    echo '' >> /usr/local/bin/claude-session && \
    echo '# Generuj unikalny ID sesji używając UUID' >> /usr/local/bin/claude-session && \
    echo 'SESSION_ID=$(python3 -c "import uuid; print(uuid.uuid4().hex[:8])")' >> /usr/local/bin/claude-session && \
    echo 'SESSION_FILE="/var/run/claude-sessions/${SESSION_ID}.session"' >> /usr/local/bin/claude-session && \
    echo '' >> /usr/local/bin/claude-session && \
    echo '# Cleanup przy wyjściu' >> /usr/local/bin/claude-session && \
    echo 'trap "rm -f $SESSION_FILE /tmp/project-bashrc-$SESSION_ID" EXIT' >> /usr/local/bin/claude-session && \
    echo '' >> /usr/local/bin/claude-session && \
    echo '# Zapisz informacje o sesji' >> /usr/local/bin/claude-session && \
    echo 'echo "{\"path\": \"$PROJECT_PATH\", \"pid\": $$, \"time\": $(date +%s)}" > "$SESSION_FILE"' >> /usr/local/bin/claude-session && \
    echo '' >> /usr/local/bin/claude-session && \
    echo '# Przygotuj bashrc dla projektu' >> /usr/local/bin/claude-session && \
    echo 'cat > /tmp/project-bashrc-$SESSION_ID << '\''BASHRC'\''' >> /usr/local/bin/claude-session && \
    echo '# Project environment' >> /usr/local/bin/claude-session && \
    echo 'export PS1="\[\033[01;32m\][sandbox]\[\033[00m\] \[\033[01;34m\]\w\[\033[00m\] $ "' >> /usr/local/bin/claude-session && \
    echo 'export PROJECT_ROOT="$PROJECT_ROOT"' >> /usr/local/bin/claude-session && \
    echo 'alias ll="ls -la"' >> /usr/local/bin/claude-session && \
    echo 'alias ..="cd .."' >> /usr/local/bin/claude-session && \
    echo 'echo "🔒 Sandboxed session for: $PROJECT_ROOT"' >> /usr/local/bin/claude-session && \
    echo 'echo "📦 Available tools: python, node, java, maven"' >> /usr/local/bin/claude-session && \
    echo 'echo "💡 Type '\''exit'\'' to leave sandbox"' >> /usr/local/bin/claude-session && \
    echo 'BASHRC' >> /usr/local/bin/claude-session && \
    echo '' >> /usr/local/bin/claude-session && \
    echo '# Uruchom w sandboxie z bubblewrap' >> /usr/local/bin/claude-session && \
    echo 'exec bwrap \' >> /usr/local/bin/claude-session && \
    echo '    --bind / / \' >> /usr/local/bin/claude-session && \
    echo '    --tmpfs /home \' >> /usr/local/bin/claude-session && \
    echo '    --tmpfs /root \' >> /usr/local/bin/claude-session && \
    echo '    --tmpfs /tmp \' >> /usr/local/bin/claude-session && \
    echo '    --bind "$PROJECT_PATH" /workspace \' >> /usr/local/bin/claude-session && \
    echo '    --bind "/tmp/project-bashrc-$SESSION_ID" /etc/project-bashrc \' >> /usr/local/bin/claude-session && \
    echo '    --chdir /workspace \' >> /usr/local/bin/claude-session && \
    echo '    --unshare-pid \' >> /usr/local/bin/claude-session && \
    echo '    --die-with-parent \' >> /usr/local/bin/claude-session && \
    echo '    --dev /dev \' >> /usr/local/bin/claude-session && \
    echo '    --proc /proc \' >> /usr/local/bin/claude-session && \
    echo '    --setenv PATH "$PATH" \' >> /usr/local/bin/claude-session && \
    echo '    --setenv HOME /workspace \' >> /usr/local/bin/claude-session && \
    echo '    --setenv PROJECT_ROOT "$PROJECT_PATH" \' >> /usr/local/bin/claude-session && \
    echo '    bash --rcfile /etc/project-bashrc "$@"' >> /usr/local/bin/claude-session && \
    chmod +x /usr/local/bin/claude-session

WORKDIR /workspace

# Healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD echo "OK" || exit 1

# Utrzymanie kontenera
CMD ["sleep", "infinity"]