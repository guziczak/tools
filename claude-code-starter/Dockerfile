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

# Session manager z właściwą izolacją
RUN mkdir -p /var/run/claude-sessions /opt/claude-shared/{bin,lib,share} && \
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
    echo '# Przygotuj katalog tymczasowy dla sesji' >> /usr/local/bin/claude-session && \
    echo 'SESSION_ID=$(python3 -c "import uuid; print(uuid.uuid4().hex[:8])")' >> /usr/local/bin/claude-session && \
    echo 'SESSION_TMP="/tmp/claude-session-$SESSION_ID"' >> /usr/local/bin/claude-session && \
    echo 'mkdir -p "$SESSION_TMP"' >> /usr/local/bin/claude-session && \
    echo '' >> /usr/local/bin/claude-session && \
    echo '# Cleanup przy wyjściu' >> /usr/local/bin/claude-session && \
    echo 'trap "rm -rf $SESSION_TMP" EXIT' >> /usr/local/bin/claude-session && \
    echo '' >> /usr/local/bin/claude-session && \
    echo '# Sprawdź czy claude istnieje' >> /usr/local/bin/claude-session && \
    echo 'if ! which claude >/dev/null 2>&1; then' >> /usr/local/bin/claude-session && \
    echo '    echo "Claude Code not found. Please install it first." >&2' >> /usr/local/bin/claude-session && \
    echo '    exit 1' >> /usr/local/bin/claude-session && \
    echo 'fi' >> /usr/local/bin/claude-session && \
    echo '' >> /usr/local/bin/claude-session && \
    echo '# Uruchom claude z bubblewrap - mocna izolacja' >> /usr/local/bin/claude-session && \
    echo 'exec bwrap \' >> /usr/local/bin/claude-session && \
    echo '    --ro-bind /usr /usr \' >> /usr/local/bin/claude-session && \
    echo '    --ro-bind /lib /lib \' >> /usr/local/bin/claude-session && \
    echo '    --ro-bind /lib64 /lib64 \' >> /usr/local/bin/claude-session && \
    echo '    --ro-bind /bin /bin \' >> /usr/local/bin/claude-session && \
    echo '    --ro-bind /sbin /sbin \' >> /usr/local/bin/claude-session && \
    echo '    --ro-bind /etc /etc \' >> /usr/local/bin/claude-session && \
    echo '    --bind /opt/claude-shared /opt/claude-shared \' >> /usr/local/bin/claude-session && \
    echo '    --bind "$PROJECT_PATH" "$PROJECT_PATH" \' >> /usr/local/bin/claude-session && \
    echo '    --bind "$SESSION_TMP" /tmp \' >> /usr/local/bin/claude-session && \
    echo '    --tmpfs /home \' >> /usr/local/bin/claude-session && \
    echo '    --tmpfs /root \' >> /usr/local/bin/claude-session && \
    echo '    --tmpfs /var \' >> /usr/local/bin/claude-session && \
    echo '    --tmpfs /run \' >> /usr/local/bin/claude-session && \
    echo '    --proc /proc \' >> /usr/local/bin/claude-session && \
    echo '    --dev /dev \' >> /usr/local/bin/claude-session && \
    echo '    --chdir "$PROJECT_PATH" \' >> /usr/local/bin/claude-session && \
    echo '    --unshare-pid \' >> /usr/local/bin/claude-session && \
    echo '    --die-with-parent \' >> /usr/local/bin/claude-session && \
    echo '    --setenv PATH "/opt/claude-shared/bin:$PATH" \' >> /usr/local/bin/claude-session && \
    echo '    --setenv PYTHONPATH "/opt/claude-shared/lib/python3/site-packages:$PYTHONPATH" \' >> /usr/local/bin/claude-session && \
    echo '    --setenv NODE_PATH "/opt/claude-shared/lib/node_modules:$NODE_PATH" \' >> /usr/local/bin/claude-session && \
    echo '    --setenv HOME "$PROJECT_PATH" \' >> /usr/local/bin/claude-session && \
    echo '    --setenv TMPDIR "/tmp" \' >> /usr/local/bin/claude-session && \
    echo '    claude "$@"' >> /usr/local/bin/claude-session && \
    chmod +x /usr/local/bin/claude-session

# Konfiguracja dla wspólnych narzędzi
RUN echo 'export PATH="/opt/claude-shared/bin:$PATH"' >> /etc/bash.bashrc && \
    echo 'export PYTHONPATH="/opt/claude-shared/lib/python3/site-packages:$PYTHONPATH"' >> /etc/bash.bashrc && \
    echo 'export NODE_PATH="/opt/claude-shared/lib/node_modules:$NODE_PATH"' >> /etc/bash.bashrc && \
    echo 'export PIP_TARGET="/opt/claude-shared/lib/python3/site-packages"' >> /etc/bash.bashrc && \
    echo 'export NPM_CONFIG_PREFIX="/opt/claude-shared"' >> /etc/bash.bashrc

WORKDIR /workspace

# Healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD echo "OK" || exit 1

# Utrzymanie kontenera
CMD ["sleep", "infinity"]