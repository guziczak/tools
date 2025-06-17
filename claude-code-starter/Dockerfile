FROM ubuntu:22.04

# Ustawienie nieinteraktywnego trybu instalacji
ENV DEBIAN_FRONTEND=noninteractive

# Instalacja podstawowych narzędzi w jednym kroku
RUN apt-get update && apt-get install -y \
    # Podstawowe narzędzia
    curl wget vim nano \
    zip unzip tar gzip bzip2 xz-utils \
    build-essential pkg-config \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg lsb-release \
    # Narzędzia sieciowe i debugowania
    net-tools iputils-ping \
    htop tree jq \
    # Narzędzia wyszukiwania
    ripgrep fd-find fzf \
    # Narzędzia do obrazów/mediów
    imagemagick ffmpeg \
    # Narzędzia deweloperskie
    sqlite3 shellcheck \
    # Docker CLI
    docker.io \
    # Python 3 i pip
    python3 python3-pip python3-venv python3-dev \
    # Java (OpenJDK 17)
    openjdk-17-jdk maven gradle \
    # Ruby
    ruby-full \
    # PHP
    php php-cli php-mbstring php-xml php-curl php-zip composer \
    # LaTeX/TeX
    texlive texlive-latex-extra texlive-fonts-recommended \
    texlive-lang-polish biber latexmk \
    # Chrome/Chromium dla Selenium
    chromium-browser chromium-chromedriver \
    && ln -s /usr/bin/python3 /usr/bin/python \
    && rm -rf /var/lib/apt/lists/*

# Node.js 20 i npm
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Go (wersja lekka)
RUN wget -q https://go.dev/dl/go1.21.6.linux-amd64.tar.gz \
    && tar -C /usr/local -xzf go1.21.6.linux-amd64.tar.gz \
    && rm go1.21.6.linux-amd64.tar.gz
ENV PATH="/usr/local/go/bin:${PATH}"

# Instalacja Claude Code jako pierwsza rzecz po Node.js
RUN npm install -g @anthropic-ai/claude-code && \
    npm cache clean --force

# Podstawowe pakiety Python (rozszerzone o nowe zależności)
RUN pip3 install --no-cache-dir \
    requests beautifulsoup4 \
    pytest black flake8 \
    easyocr \
    selenium==4.18.1 \
    fastapi==0.109.2 \
    uvicorn==0.27.1 \
    anthropic==0.18.1 \
    pydantic==2.6.1 \
    pyyaml==6.0.1 \
    lxml==5.1.0 \
    aiofiles==23.2.1 \
    python-multipart==0.0.9 \
    httpx==0.26.0 \
    websockets==12.0 \
    rich==13.7.0

# Podstawowe pakiety Node.js (tylko najpotrzebniejsze)
RUN npm install -g \
    typescript \
    eslint prettier

# Ustawienia dla Selenium z Chromium
ENV CHROME_BIN=/usr/bin/chromium-browser \
    CHROME_DRIVER=/usr/bin/chromedriver

# Ustawienia środowiskowe dla Claude Code
ENV CLAUDE_DEFAULT_MODEL=opus \
    CLAUDE_MODEL=opus \
    ANTHROPIC_MODEL=opus

WORKDIR /c

# Prosty healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD echo "OK" || exit 1

# Utrzymanie kontenera przy życiu
CMD ["tail", "-f", "/dev/null"]