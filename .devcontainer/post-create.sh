#!/bin/bash
# Post-create setup script for devcontainer
set -e

echo "🏠 Setting up lumehaven development environment..."

# Backend setup
echo "📦 Setting up Python backend..."
cd /workspace/packages/backend

# Check if venv exists but has broken symlinks (stale uv cache)
if [ -d ".venv" ]; then
    if ! uv pip check &>/dev/null; then
        echo "⚠️  Detected stale venv (broken symlinks), recreating..."
        rm -rf .venv
    fi
fi

uv sync --all-extras
echo "✅ Backend dependencies installed"

# Generate version from git tags (setuptools_scm)
echo "📌 Updating version from git tags..."
cd /workspace
python scripts/update_version.py || echo "⚠️  Could not update version (git tags may not be available)"

# Frontend setup (when it exists)
if [ -f "/workspace/packages/frontend/package.json" ]; then
    echo "📦 Setting up frontend..."
    cd /workspace/packages/frontend
    bun install
    echo "✅ Frontend dependencies installed"
else
    echo "⏭️  Frontend not yet initialized, skipping..."
fi

# Install pre-commit hooks (if configured)
cd /workspace
if [ -f ".pre-commit-config.yaml" ]; then
    echo "🪝 Installing pre-commit hooks..."
    # Use uv --directory to specify the Python environment without changing directories
    # This runs pre-commit from the repository root (where .pre-commit-config.yaml is)
    if uv --directory packages/backend run pre-commit install --install-hooks; then
        echo "✅ Pre-commit hooks installed successfully"
    else
        echo "⚠️  pre-commit install had issues, but continuing..."
    fi
    # Install additional hook stages for beads (bd) sync
    uv --directory packages/backend run pre-commit install --hook-type pre-push --hook-type post-merge 2>/dev/null || true
fi

# Install beads MCP server for Copilot integration (Python-based)
echo "🔮 Installing beads MCP server..."
uv tool install beads-mcp 2>/dev/null || echo "⚠️  beads-mcp install had issues, continuing..."

# Initialize beads issue tracker if not already done
cd /workspace
if [ ! -d ".beads" ]; then
    echo "🔮 Initializing beads issue tracker..."
    bd init --quiet --no-hooks
    echo "✅ Beads initialized"
else
    echo "✅ Beads already initialized"
fi

# SSH: seed known_hosts for GitHub so the first git push doesn't trigger a TOFU prompt.
# VS Code forwards the host's SSH agent automatically (SSH_AUTH_SOCK), so keys never
# enter the container. We just need known_hosts to be pre-populated and writable.
mkdir -p /home/vscode/.ssh
chmod 700 /home/vscode/.ssh
ssh-keyscan -t ed25519 github.com >> /home/vscode/.ssh/known_hosts 2>/dev/null
chmod 644 /home/vscode/.ssh/known_hosts
chown -R vscode:vscode /home/vscode/.ssh
echo "✅ SSH known_hosts seeded (agent forwarding handles authentication)"

# GitHub CLI: disable pager (prevents 'alternate buffer' issues with Copilot in VS Code)
# gh defaults to $PAGER (=less) when its own pager config is blank.
# GH_PAGER=cat is set via remoteEnv, but gh config persists across shell sessions.
gh config set pager cat 2>/dev/null || true

# GitHub CLI authentication reminder
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ DevContainer ready! Development environment configured."
echo ""
echo "⚡ Quick start:"
echo "   Backend:  cd packages/backend && uv run uvicorn lumehaven.main:app --reload"
echo "   Frontend: cd packages/frontend && bun run dev"
echo "   Tests:    cd packages/backend && uv run pytest"
echo ""
echo "🔧 Maintenance:"
echo "   Update pre-commit hooks: ./scripts/update-precommit.sh"
echo ""
echo "📖 Documentation: See docs/DEVELOPMENT-ENVIRONMENT.md"
echo ""
echo "GitHub CLI: Run 'gh auth login' if needed"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
