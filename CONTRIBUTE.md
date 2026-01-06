# Contributing to lumehaven

Thank you for contributing! Here's how to get started.

## Development Environment

This project uses **VS Code DevContainers** as the exclusive development environment.
This ensures all contributors work identically regardless of OS.

### Quick Start (2 minutes)

```bash
git clone https://github.com/ff-fab/lumehaven.git
cd lumehaven

# Open in VS Code
code .

# Reopen in DevContainer: Ctrl+Shift+P → "Dev Containers: Reopen in Container"
# Everything auto-configures. Ready to code!
```

### What Gets Configured Automatically

- ✓ All VS Code extensions (Python, Prettier, Ruff, etc.)
- ✓ Python dependencies (uv sync --all-extras)
- ✓ Node dependencies (bun install)
- ✓ Formatters & linters (Prettier, Ruff, mypy)
- ✓ Version number (from git tags)

## GitHub CLI Authentication

By default, GitHub CLI uses SSH authentication from your host machine via VS Code's SSH
forwarding:

**The container automatically mounts your SSH directory** (`~/.ssh` from host) with full
access. If you have SSH keys configured on your host, `gh` should work out of the box on
first use.

**Why full access?** SSH needs to read your private keys AND write to `known_hosts` when
connecting to new hosts (like github.com for the first time). This is safe because the
container runs under your host's ssh-agent context.

**If SSH isn't configured on your host:**

```bash
gh auth login
# Prompts you to authenticate (creates a token in the container)
```

**Security note:** The `~/.ssh` mount uses your host's keys—they're not copied into the
container. When the devcontainer stops, nothing persists except `known_hosts` entries.

### Troubleshooting GitHub CLI

- **"permission denied (publickey)"** → Add your SSH public key to GitHub at
  https://github.com/settings/keys (verify your host SSH key has correct permissions:
  `chmod 600 ~/.ssh/id_*`)
- **"command not found: gh"** → Run `sudo apt update && sudo apt install -y gh` (GitHub
  CLI feature auto-installs, but sometimes needs refresh)
- **Token expired** → Run `gh auth login` again to refresh
- **SSH not working in WSL** → Ensure SSH keys are in WSL `~/.ssh/` directory, not
  Windows home

## Development Workflows

### Understanding the Python Virtual Environment

This project uses **uv** as the Python package manager. It automatically creates and
manages a virtual environment at `/workspace/packages/backend/.venv/` without requiring
manual activation.

**How it works:**

- On devcontainer startup, `uv sync --all-extras` creates `.venv/` with all dependencies
- The devcontainer's `PATH` includes `.venv/bin/`, so Python commands automatically use
  the venv
- You don't see the `(venv)` prompt because uv manages it transparently

**To verify the venv is active:**

```bash
which python    # Should return: /workspace/packages/backend/.venv/bin/python
python --version
pip list        # Shows installed packages in the venv
```

**When uv.lock gets updated:**

- Automatically when you run `uv add <package>` or `uv add --dev <package>`
- Manually when you run `uv lock --upgrade` (to update to latest compatible versions)
- **Always commit uv.lock** to git (like package-lock.json or poetry.lock)

_Note:_ `uv sync` installs dependencies based on the existing `uv.lock` file but does **not**
update or modify `uv.lock` itself.
### Backend (Python/FastAPI)

```bash
cd packages/backend

# Install/update dependencies (run after git pull if pyproject.toml or uv.lock changed)
uv sync --all-extras

# Add a new dependency
uv add requests                # Production dependency
uv add --dev pytest-debugpy   # Development dependency

# Start dev server with auto-reload (http://localhost:8000)
uv run uvicorn lumehaven.main:app --reload

# Run tests with pytest
uv run pytest tests/

# Run specific test file with verbose output
uv run pytest tests/unit/test_signal.py -v

# Debug a failing test (drop into debugger on failure)
uv run pytest tests/unit/ --pdb

# Format and lint Python code
uv run ruff format src/                  # Auto-format
uv run ruff check src/ --fix             # Lint and fix violations
uv run mypy src/lumehaven                # Type check with strict mode

# Alternative: Use VS Code Debug Configs
# Press F5 → Select "Debug Backend (FastAPI)" to start with debugger
# VS Code automatically uses the venv at .venv/bin/python
```

**About `uv run`:**

- `uv run <command>` automatically uses the venv (most explicit way)
- Directly typing `python`, `pytest`, etc. also works (PATH includes venv)
- Both are equivalent—use whichever you prefer

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

Pre-commit hooks automatically check and fix code issues **before you commit**,
preventing bad code from entering the repository.

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

- See [.devcontainer/README.md](.devcontainer/README.md) for technical DevContainer
  details
- See [packages/backend/README.md](packages/backend/README.md) for API development
- Check [docs/adr/](docs/adr/) for architecture decisions
- Open an issue if something isn't clear

---

**Happy contributing!** 🎉
