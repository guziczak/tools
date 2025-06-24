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
    sudo util-linux \
    curl wget \
    gnupg lsb-release \
    software-properties-common apt-transport-https \
    git vim nano zip unzip xz-utils \
    python3 python3-pip python3-venv python3-dev \
    build-essential pkg-config \
    # Java i Maven - zawsze (potrzebne nawet w slim)
    openjdk-17-jdk-headless maven \
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
    echo '# Create new mount namespace and run Claude' >> /usr/local/bin/claude-namespace-launcher && \
    echo 'exec unshare --mount bash -c '"'"'' >> /usr/local/bin/claude-namespace-launcher && \
    echo '    # Inside new namespace' >> /usr/local/bin/claude-namespace-launcher && \
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
    echo '    exec sudo -u claude -E HOME=/home/claude bash -c "cd /project && claude $*"' >> /usr/local/bin/claude-namespace-launcher && \
    echo ''"'"' "$@"' >> /usr/local/bin/claude-namespace-launcher && \
    chmod +x /usr/local/bin/claude-namespace-launcher

# Simple session starter script
RUN printf '#!/bin/bash\ncd "${1:-/project}"\nshift\nexec claude "$@"\n' > /usr/local/bin/claude-session && \
    chmod +x /usr/local/bin/claude-session && \
    # Konfiguracja dla wspólnych narzędzi
    echo 'export PATH="/opt/claude-shared/bin:$PATH"' >> /etc/bash.bashrc && \
    echo 'export PYTHONPATH="/opt/claude-shared/lib/python3/site-packages:$PYTHONPATH"' >> /etc/bash.bashrc && \
    echo 'export NODE_PATH="/opt/claude-shared/lib/node_modules:$NODE_PATH"' >> /etc/bash.bashrc && \
    echo 'export PIP_TARGET="/opt/claude-shared/lib/python3/site-packages"' >> /etc/bash.bashrc && \
    echo 'export NPM_CONFIG_PREFIX="/opt/claude-shared"' >> /etc/bash.bashrc

# Przełączenie na użytkownika claude
USER claude
WORKDIR /home/claude

# Healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD echo "OK" || exit 1

# Utrzymanie kontenera
CMD ["sleep", "infinity"]