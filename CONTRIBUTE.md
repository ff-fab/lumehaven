# Contributing to lumehaven

Thank you for contributing! Here's how to get started.

## Development Environment

This project uses **VS Code DevContainers** as the exclusive development environment. This ensures all contributors work identically regardless of OS.

### Quick Start (2 minutes)

```bash
git clone https://github.com/ff-fab/lumehaven.git
cd lumehaven

# Open with workspace file (recommended)
code lumehaven.code-workspace

# Reopen in DevContainer: Ctrl+Shift+P → "Dev Containers: Reopen in Container"
# Everything auto-configures. Ready to code!
```

### What Gets Configured Automatically
- ✓ All VS Code extensions (Python, Prettier, Ruff, etc.)
- ✓ Python dependencies (uv sync --all-extras)
- ✓ Node dependencies (bun install)
- ✓ Formatters & linters (Prettier, Ruff, mypy)
- ✓ Version number (from git tags)

### Forgot the Workspace File?
Don't worry. Both work identically:
```bash
code lumehaven.code-workspace  # Recommended (clearer sidebar)
code .                         # Also works (less organized)
```
DevContainer applies all settings either way.

## Development Workflows

### Backend (Python/FastAPI)
```bash
cd packages/backend

# Install dependencies
uv sync --all-extras

# Start dev server (http://localhost:8000)
uv run uvicorn lumehaven.main:app --reload

# Run tests
uv run pytest tests/unit/

# Format and lint
uv run ruff format src/
uv run ruff check src/
uv run mypy src/lumehaven
```

### Frontend (React/TypeScript)
```bash
cd packages/frontend

# Install dependencies
bun install

# Start dev server (http://localhost:5173)
bun run dev

# Run tests
bun test

# Format
bun run format
```

## Code Quality

All formatters and linters are **auto-configured**:
- **Prettier** — Formats JS, TS, JSON, Markdown, YAML (88-char line width)
- **Ruff** — Lints and formats Python (88-char line width)
- **mypy** — Type checking in strict mode
- **ESLint** — JavaScript/TypeScript linting

**Format on save is enabled** — your code auto-formats when you save.

## Git Workflow

1. Create a feature branch from `main`
   ```bash
   git checkout main && git pull
   git checkout -b feature/my-feature
   ```

2. Make changes and commit
   ```bash
   git commit -m "Clear, descriptive commit message"
   ```

3. Open a pull request
   ```bash
   git push -u origin feature/my-feature
   gh pr create
   ```

4. After approval and CI passes, merge and delete branch

## Documentation

- **Architecture decisions**: [docs/adr/](docs/adr/)
- **Lessons learned from PoC**: [docs/ll/](docs/ll/)
- **Setup details**: [.devcontainer/README.md](.devcontainer/README.md)
- **Project overview**: [README.md](README.md)

## Questions?

- See [.devcontainer/README.md](.devcontainer/README.md) for technical DevContainer details
- See [packages/backend/README.md](packages/backend/README.md) for API development
- Check [docs/adr/](docs/adr/) for architecture decisions
- Open an issue if something isn't clear

---

**Happy contributing!** 🎉
