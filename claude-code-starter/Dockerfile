# Multi-stage build dla szybszego budowania
FROM node:20-slim AS node-builder

# Instalacja Claude Code z weryfikacją
RUN npm install -g @anthropic-ai/claude-code typescript eslint prettier || \
    (echo "=== Claude Code installation failed, continuing anyway ===" && \
     npm install -g typescript eslint prettier) && \
    npm cache clean --force && \
    # Debug - sprawdzamy co się zainstalowało
    echo "=== Installed packages ===" && \
    npm list -g --depth=0 && \
    echo "=== Looking for claude ===" && \
    find /usr/local -name "claude" -type f -o -type l 2>/dev/null | head -10

# Główny obraz
FROM ubuntu:22.04

# Ustawienia środowiskowe
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONIOENCODING=utf-8 \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8 \
    CLAUDE_DEFAULT_MODEL=opus \
    CLAUDE_MODEL=opus \
    ANTHROPIC_MODEL=opus \
    CHROME_BIN=/usr/bin/chromium-browser \
    CHROME_DRIVER=/usr/bin/chromedriver \
    PATH="/usr/local/lib/node_modules/.bin:${PATH}"

# Kopiowanie Node.js i pakietów z pierwszego stage'a
COPY --from=node-builder /usr/local/bin/node /usr/local/bin/
COPY --from=node-builder /usr/local/lib/node_modules /usr/local/lib/node_modules

# Tworzenie symlinków
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
    ln -s /usr/local/lib/node_modules/prettier/bin/prettier.cjs /usr/local/bin/prettier 2>/dev/null || true

# Instalacja podstawowych pakietów z cache mount dla szybszego rebuildu
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    # Podstawowe (niezbędne)
    curl wget ca-certificates gnupg lsb-release \
    software-properties-common apt-transport-https \
    # Python
    python3 python3-pip python3-venv python3-dev \
    # Narzędzia budowania
    build-essential pkg-config \
    # Git i podstawowe narzędzia
    git vim nano zip unzip tar gzip bzip2 xz-utils \
    tree jq net-tools iputils-ping htop \
    # Narzędzia wyszukiwania
    ripgrep fd-find fzf \
    # Java (runtime)
    openjdk-17-jdk maven gradle \
    # Ruby - tylko runtime
    ruby \
    # PHP
    php php-cli php-mbstring php-xml php-curl php-zip composer \
    # Chrome dla Selenium
    chromium-browser chromium-chromedriver \
    # Docker CLI
    docker.io \
    # Media
    imagemagick ffmpeg \
    # Dodatkowe
    sqlite3 shellcheck \
    # LaTeX - pełny zestaw
    texlive texlive-latex-extra texlive-fonts-recommended \
    texlive-lang-polish biber latexmk \
    # Bubblewrap dla sandboxowania
    bubblewrap \
    # Czyszczenie
    && ln -s /usr/bin/python3 /usr/bin/python \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Python packages - z obsługą externally-managed-environment
RUN python3 -m pip install --break-system-packages --no-cache-dir --upgrade pip setuptools wheel && \
    python3 -m pip install --break-system-packages --no-cache-dir \
        requests beautifulsoup4 pytest black flake8 \
        easyocr \
        selenium==4.18.1 fastapi==0.109.2 uvicorn==0.27.1 \
        anthropic==0.18.1 pydantic==2.6.1 pyyaml==6.0.1 \
        lxml==5.1.0 aiofiles==23.2.1 python-multipart==0.0.9 \
        httpx==0.26.0 websockets==12.0 rich==13.7.0 || \
    # Alternatywa przez venv jeśli --break-system-packages nie działa
    (echo "Installing Python packages via venv..." && \
     python3 -m venv /opt/venv && \
     /opt/venv/bin/pip install --upgrade pip setuptools wheel && \
     /opt/venv/bin/pip install \
        requests beautifulsoup4 pytest black flake8 \
        easyocr \
        selenium==4.18.1 fastapi==0.109.2 uvicorn==0.27.1 \
        anthropic==0.18.1 pydantic==2.6.1 pyyaml==6.0.1 \
        lxml==5.1.0 aiofiles==23.2.1 python-multipart==0.0.9 \
        httpx==0.26.0 websockets==12.0 rich==13.7.0 && \
     echo 'export PATH="/opt/venv/bin:$PATH"' >> /etc/bash.bashrc)

# Skrypt pomocniczy do instalacji Claude Code
RUN echo '#!/bin/bash\n\
if ! which claude >/dev/null 2>&1; then\n\
    echo "Claude Code not found. Attempting to install..."\n\
    npm install -g @anthropic-ai/claude-code && \\\n\
    echo "Claude Code installed successfully!" || \\\n\
    echo "Failed to install Claude Code"\n\
fi' > /usr/local/bin/check-claude && chmod +x /usr/local/bin/check-claude

# Session manager dla sandboxowania
RUN mkdir -p /var/run/claude-sessions && \
    cat > /usr/local/bin/claude-session << 'SCRIPT'
#!/bin/bash
set -euo pipefail

# Pobierz argumenty
PROJECT_PATH="${1:-/workspace}"
shift || true

# Walidacja ścieżki
if [ ! -d "$PROJECT_PATH" ]; then
    echo "Error: Project path does not exist: $PROJECT_PATH" >&2
    exit 1
fi

# Generuj unikalny ID sesji używając UUID
SESSION_ID=$(python3 -c "import uuid; print(uuid.uuid4().hex[:8])")
SESSION_FILE="/var/run/claude-sessions/${SESSION_ID}.session"

# Zapisz informacje o sesji
echo "{\"path\": \"$PROJECT_PATH\", \"pid\": $$, \"time\": $(date +%s)}" > "$SESSION_FILE"

# Przygotuj bashrc dla projektu
cat > /tmp/project-bashrc-$SESSION_ID << 'BASHRC'
# Project environment
export PS1="\[\033[01;32m\][sandbox]\[\033[00m\] \[\033[01;34m\]\w\[\033[00m\] $ "
export PROJECT_ROOT="$PROJECT_ROOT"
alias ll="ls -la"
alias ..="cd .."
echo "🔒 Sandboxed session for: $PROJECT_ROOT"
echo "📦 Available tools: python, node, java, ruby, php"
echo "💡 Type 'exit' to leave sandbox"
BASHRC

# Uruchom w sandboxie z bubblewrap
exec bwrap \
    --bind / / \
    --tmpfs /home \
    --tmpfs /root \
    --tmpfs /tmp \
    --bind "$PROJECT_PATH" /workspace \
    --bind "/tmp/project-bashrc-$SESSION_ID" /etc/project-bashrc \
    --chdir /workspace \
    --unshare-pid \
    --dev /dev \
    --proc /proc \
    --setenv PATH "$PATH" \
    --setenv HOME /workspace \
    --setenv PROJECT_ROOT "$PROJECT_PATH" \
    bash --rcfile /etc/project-bashrc "$@"
SCRIPT
chmod +x /usr/local/bin/claude-session

WORKDIR /workspace

# Healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD echo "OK" || exit 1

# Utrzymanie kontenera - używamy sleep infinity (best practice)
CMD ["sleep", "infinity"]