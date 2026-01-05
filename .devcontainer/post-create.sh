#!/bin/bash
# Post-create setup script for devcontainer
set -e

echo "🏠 Setting up lumehaven development environment..."

# Backend setup
echo "📦 Setting up Python backend..."
cd /workspace/packages/backend
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
    uv run pre-commit install
fi

# GitHub CLI authentication reminder
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Development environment ready!"
echo ""
echo "Quick start:"
echo "  Backend:  cd packages/backend && uv run uvicorn lumehaven.main:app --reload"
echo "  Tests:    cd packages/backend && uv run pytest"
echo ""
echo "If you need GitHub CLI, run: gh auth login"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
