# GIMPL - (G)eorge's Re(impl)ementation agent sandbox, adapted from the course module_1 Dockerfile.
# Every package below is here for a specific GIMPL need. Removed from the
# course starter: OpenCode, ngrok, nano, and the requirements.txt Python
# packages (none are used by Chocolate Heretic or the demo check).
# Rust is not installed yet. It will be added later as course progresses.
FROM python:3.12-slim

WORKDIR /workspace

RUN apt-get update && apt-get install -y --no-install-recommends \
    # Agent basics
    bash \
    ca-certificates \
    curl \
    git \
    procps \
    # Claude Code runs on Node.js
    nodejs \
    npm \
    # Build Chocolate Heretic with autotools (./autogen.sh && make)
    gcc \
    make \
    autoconf \
    automake \
    libtool \
    pkg-config \
    # SDL2 libraries Chocolate Heretic links against
    libsdl2-dev \
    libsdl2-mixer-dev \
    libsdl2-net-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code
RUN npm install -g @anthropic-ai/claude-code

# Let git run as root on the mounted repo, so the agent can check its own changes with git status and git diff
RUN git config --global --add safe.directory /workspace

# Claude Code configuration: default settings + status line
RUN mkdir -p /root/.claude
COPY settings.json /root/.claude/settings.json
COPY statusline.sh /root/.claude/statusline.sh
RUN chmod +x /root/.claude/statusline.sh

# Entrypoint keeps the Claude login in the claude-auth volume
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Run the game headless: no window, no sound device in the container
ENV SDL_VIDEODRIVER=dummy \
    SDL_AUDIODRIVER=dummy

# Student shell quality-of-life improvements
RUN echo 'export PS1="gimpl:\\w# "' >> /root/.bashrc && \
    echo 'alias ll="ls -alF"' >> /root/.bashrc && \
    echo 'alias la="ls -A"' >> /root/.bashrc && \
    echo 'alias l="ls -CF"' >> /root/.bashrc

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["/bin/bash"]
