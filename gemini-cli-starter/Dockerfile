# Gemini CLI Docker Container
FROM ubuntu:24.04

# Build arguments
ARG BUILD_VERSION=full
ARG DEBIAN_FRONTEND=noninteractive

# Set up base environment
ENV TZ=UTC \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    NODE_VERSION=20 \
    PATH="/usr/local/bin:$PATH" \
    GEMINI_CONTAINER_VERSION=${BUILD_VERSION}

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Essential tools
    curl wget git vim nano sudo \
    ca-certificates gnupg lsb-release \
    build-essential python3 python3-pip \
    unzip zip jq tree htop \
    # For namespace operations
    util-linux coreutils \
    # Network tools
    net-tools iputils-ping \
    # Shell
    bash bash-completion \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g npm@latest

# Install Gemini CLI globally
RUN npm install -g @google/gemini-cli

# Create directories for persistent storage
RUN mkdir -p /opt/gemini-shared \
    /opt/project-sessions \
    /usr/local/bin

# Install additional tools based on build version
RUN if [ "$BUILD_VERSION" = "full" ]; then \
    apt-get update && apt-get install -y \
    # Java and build tools
    openjdk-17-jdk maven gradle \
    # Python tools
    python3-venv python3-dev \
    # Ruby
    ruby-full \
    # PHP
    php php-cli php-mbstring php-xml php-zip \
    # Database
    sqlite3 postgresql-client mysql-client \
    # Media tools
    ffmpeg imagemagick \
    # Docker CLI
    docker.io \
    # Search tools
    ripgrep fd-find fzf \
    # Other dev tools
    shellcheck tmux screen \
    && rm -rf /var/lib/apt/lists/*; \
    fi

# Install Python packages
RUN pip3 install --no-cache-dir --break-system-packages \
    requests beautifulsoup4 lxml \
    pyyaml rich click \
    pytest black flake8 \
    fastapi uvicorn \
    google-generativeai

# Install Composer for PHP (full version only)
RUN if [ "$BUILD_VERSION" = "full" ]; then \
    curl -sS https://getcomposer.org/installer | php -- --install-dir=/usr/local/bin --filename=composer; \
    fi

# Skrypt pomocniczy do instalacji Gemini CLI
RUN echo '#!/bin/bash' > /usr/local/bin/check-gemini && \
    echo 'if ! which gemini >/dev/null 2>&1; then' >> /usr/local/bin/check-gemini && \
    echo '    echo "Gemini CLI not found. Attempting to install..."' >> /usr/local/bin/check-gemini && \
    echo '    npm install -g @google/gemini-cli && \' >> /usr/local/bin/check-gemini && \
    echo '    echo "Gemini CLI installed successfully!" || \' >> /usr/local/bin/check-gemini && \
    echo '    echo "Failed to install Gemini CLI"' >> /usr/local/bin/check-gemini && \
    echo 'fi' >> /usr/local/bin/check-gemini && \
    chmod +x /usr/local/bin/check-gemini

# Create directory structure for shared tools
RUN mkdir -p /opt/gemini-shared/{bin,lib,share} \
    /opt/gemini-shared/lib/{python3/site-packages,node_modules} \
    /opt/project-sessions \
    /home/gemini && \
    chmod -R 755 /opt/gemini-shared && \
    chmod 755 /opt/project-sessions

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
    echo '# Create new mount namespace and run Gemini' >> /usr/local/bin/gemini-namespace-launcher && \
    echo 'exec unshare --mount bash -c '"'"'' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    # Inside new namespace' >> /usr/local/bin/gemini-namespace-launcher && \
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
    echo '    # Run gemini in project directory' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    cd /project' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    ' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    # Check if Gemini is installed' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    if ! which gemini >/dev/null 2>&1; then' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '        echo "Installing Gemini CLI..."' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '        npm install -g @google/gemini-cli' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    fi' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    ' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    # Run gemini with all arguments' >> /usr/local/bin/gemini-namespace-launcher && \
    echo '    exec gemini "$@"' >> /usr/local/bin/gemini-namespace-launcher && \
    echo ''"'"' "$@"' >> /usr/local/bin/gemini-namespace-launcher && \
    chmod +x /usr/local/bin/gemini-namespace-launcher

# Create gemini wrapper for better UX
RUN echo '#!/bin/bash' > /usr/local/bin/gemini-session && \
    echo '# Simple wrapper to ensure Gemini CLI runs with proper environment' >> /usr/local/bin/gemini-session && \
    echo 'exec gemini "$@"' >> /usr/local/bin/gemini-session && \
    chmod +x /usr/local/bin/gemini-session

# Set up sudo without password for development
RUN echo "ALL ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

# Create startup script
RUN echo '#!/bin/bash' > /usr/local/bin/startup.sh && \
    echo 'echo "Gemini CLI Container Started"' >> /usr/local/bin/startup.sh && \
    echo 'echo "Version: ${GEMINI_CONTAINER_VERSION}"' >> /usr/local/bin/startup.sh && \
    echo 'echo "Ready for connections..."' >> /usr/local/bin/startup.sh && \
    echo '' >> /usr/local/bin/startup.sh && \
    echo '# Keep container running' >> /usr/local/bin/startup.sh && \
    echo 'exec sleep infinity' >> /usr/local/bin/startup.sh && \
    chmod +x /usr/local/bin/startup.sh

# Expose port for potential web services
EXPOSE 8080

# Set working directory
WORKDIR /opt/project-sessions

# Run as root for mount operations
USER root

# Default command
CMD ["/usr/local/bin/startup.sh"]