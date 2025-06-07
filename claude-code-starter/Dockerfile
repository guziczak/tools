FROM node:20-slim

# Instalacja Claude Code
RUN npm install -g @anthropic-ai/claude-code && \
    npm cache clean --force

WORKDIR /c

# Użycie exec form dla szybszego startu
ENTRYPOINT ["/bin/bash"]