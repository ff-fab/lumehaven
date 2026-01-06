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
    # Use uv to activate the environment and run pre-commit install
    # Use 'if' instead of $? check because set -e exits before the check executes
    if cd /workspace/packages/backend && uv run pre-commit install --install-hooks; then
        echo "✅ Pre-commit hooks installed successfully"
    else
        echo "⚠️  pre-commit install had issues, but continuing..."
    fi
    cd /workspace
fi

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
echo "📖 Documentation: See docs/DEVELOPMENT-ENVIRONMENT.md"
echo ""
echo "GitHub CLI: Run 'gh auth login' if needed"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
