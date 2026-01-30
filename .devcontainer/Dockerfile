# lumehaven development container
# Python 3.14 + uv + bun + common dev tools

FROM mcr.microsoft.com/devcontainers/python:3.14

# Install uv (fast Python package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install additional system dependencies FIRST (ensures curl/bash are available)
# Remove Yarn apt source - we use bun, and Yarn's GPG key causes apt-get failures
RUN rm -f /etc/apt/sources.list.d/yarn.list \
    && apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
        # Required for bun installation
        curl \
        unzip \
        # For Robot Framework Browser library (future)
        libglib2.0-0 \
        libnss3 \
        libnspr4 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libcups2 \
        libdrm2 \
        libdbus-1-3 \
        libxkbcommon0 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxrandr2 \
        libgbm1 \
        libasound2 \
        # General utilities
        jq \
        httpie \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install bun (JavaScript runtime and package manager)
RUN curl -fsSL https://bun.sh/install | bash \
    && mv /root/.bun/bin/bun /usr/local/bin/ \
    && mv /root/.bun/bin/bunx /usr/local/bin/ \
    && rm -rf /root/.bun

# Configure uv to use project-local virtual environments
ENV UV_PROJECT_ENVIRONMENT="/workspace/packages/backend/.venv"

# Set bun environment
ENV BUN_INSTALL="/usr/local"

# Create .vscode-server directory with proper ownership
# This prevents permission issues when volumes are mounted
RUN mkdir -p /home/vscode/.vscode-server /home/vscode/.vscode-server/extensions \
    && chown -R vscode:vscode /home/vscode/.vscode-server

# Verify installations
RUN uv --version && bun --version && python --version
