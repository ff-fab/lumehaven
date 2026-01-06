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

## GitHub CLI Authentication

By default, GitHub CLI uses SSH authentication from your host machine via VS Code's SSH forwarding:

**The container automatically forwarded your SSH socket** from VS Code, which has access to your host's SSH keys.
If you have SSH keys configured on your host, `gh` should work out of the box on first use.

**Why this approach?** VS Code's SSH forwarding:
- Works on **all platforms** (Linux, macOS, Windows/WSL)
- Keeps SSH keys on the host (never copied to container)
- Allows SSH to read keys AND write `known_hosts` on first connection
- Secure: Uses SSH agent forwarding, not file mounting

**If SSH isn't configured on your host:**
```bash
gh auth login
# Prompts you to authenticate (creates a token in the container)
```

**Prerequisites:**
- VS Code with Remote Development extension (included in devcontainer)
- SSH key on host with **correct permissions**: `chmod 600 ~/.ssh/id_rsa` (private keys)
- SSH public key added to GitHub: https://github.com/settings/keys

### Troubleshooting GitHub CLI

- **"permission denied (publickey)"** → Add your SSH public key to GitHub at https://github.com/settings/keys (verify your host SSH key has correct permissions: `chmod 600 ~/.ssh/id_*`)
- **"command not found: gh"** → Run `sudo apt update && sudo apt install -y gh` (GitHub CLI feature auto-installs, but sometimes needs refresh)
- **Token expired** → Run `gh auth login` again to refresh
- **SSH not working in WSL** → Ensure SSH keys are in WSL `~/.ssh/` directory, not Windows home

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

## Pre-commit Hooks (Optional but Recommended)

Pre-commit hooks automatically check and fix code issues **before you commit**, preventing bad code from entering the repository.

### Setup (One-time)

```bash
# Install pre-commit framework
uv run pre-commit install

# (Optional) Run all checks on all files
uv run pre-commit run --all-files
```

### What Gets Checked

- **Trailing whitespace** — Removes trailing spaces
- **File endings** — Ensures files end with newline
- **YAML/JSON/TOML** — Validates syntax
- **Merge conflicts** — Detects unresolved conflicts
- **Private keys** — Prevents committing secrets
- **Prettier** — Formats JS, TS, JSON, Markdown, YAML
- **Ruff** — Lints and formats Python
- **mypy** — Type checking in strict mode

### How It Works

When you run `git commit`, pre-commit hooks run automatically:
- ✓ If checks pass → commit succeeds
- ✓ If checks fail but can auto-fix → files are fixed, you re-stage and commit
- ✗ If checks fail with manual fixes needed → commit blocked until fixed

### Disable for Specific Commit

If you need to bypass hooks temporarily:
```bash
git commit --no-verify  # Not recommended, but exists
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
