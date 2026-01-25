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
    # Use uv --directory to specify the Python environment without changing directories
    # This runs pre-commit from the repository root (where .pre-commit-config.yaml is)
    if uv --directory packages/backend run pre-commit install --install-hooks; then
        echo "✅ Pre-commit hooks installed successfully"
    else
        echo "⚠️  pre-commit install had issues, but continuing..."
    fi
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
echo "🔧 Maintenance:"
echo "   Update pre-commit hooks: ./scripts/update-precommit.sh"
echo ""
echo "📖 Documentation: See docs/DEVELOPMENT-ENVIRONMENT.md"
echo ""
echo "GitHub CLI: Run 'gh auth login' if needed"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
