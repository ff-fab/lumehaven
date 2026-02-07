# Development Setup

!!! abstract "What you'll learn"
    Set up a full development environment using the dev container, understand the
    project structure, run tests, and make your first contribution.

## Prerequisites

- [Docker](https://www.docker.com/) installed and running
- [VS Code](https://code.visualstudio.com/) with the
  [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

## 1. Open in Dev Container

```bash
git clone https://github.com/ff-fab/lumehaven.git
code lumehaven
# VS Code will prompt: "Reopen in Container" → click it
```

The container auto-configures everything (~2 minutes on first run):

- Python 3.14 + uv + all backend dependencies
- Node.js + bun + all frontend dependencies
- VS Code extensions (Ruff, Prettier, Python, etc.)
- Formatters, linters, and pre-commit hooks
- Version number (from git tags)

## 2. Verify the Setup

```bash
task test:be:unit   # Run backend unit tests
task lint:be        # Check linting
task typecheck:be   # Check types
```

All three should pass with no errors.

## 3. Understand the Project Structure

```
lumehaven/
├── packages/
│   ├── backend/              # Python BFF (FastAPI)
│   │   ├── src/lumehaven/    # Source code
│   │   └── tests/            # pytest + Robot Framework
│   └── frontend/             # React SPA (TypeScript) — Phase 3
├── docs/                     # This documentation (MkDocs)
├── Taskfile.yml              # Cross-platform task runner
└── mkdocs.yml                # Doc site configuration
```

For how the backend components fit together, see
[Architecture](../explanation/architecture.md).

## 4. GitHub CLI Authentication

The container mounts your host's `~/.ssh` directory for SSH-based authentication. If
you have SSH keys configured on your host, `gh` should work out of the box.

**If SSH isn't configured:**

```bash
gh auth login
# Follow the prompts to authenticate
```

??? info "How SSH mounting works"
    The container mounts `~/.ssh` from your host with full access. SSH needs read
    access for private keys and write access for `known_hosts` when connecting to new
    hosts. Keys aren't copied — they're mounted. Nothing persists except `known_hosts`
    entries.

**Troubleshooting:**

| Problem                         | Solution                                                       |
| ------------------------------- | -------------------------------------------------------------- |
| "permission denied (publickey)" | Add SSH key to GitHub: <https://github.com/settings/keys>      |
| "command not found: gh"         | `sudo apt update && sudo apt install -y gh`                    |
| Token expired                   | `gh auth login` again                                          |
| SSH not working in WSL          | Ensure keys are in WSL `~/.ssh/`, not Windows home             |

## 5. Understanding the Python Virtual Environment

This project uses **uv** as the Python package manager. It creates and manages a virtual
environment at `packages/backend/.venv/` without requiring manual activation.

- On startup, `uv sync --all-extras` creates `.venv/` with all dependencies
- The container's `PATH` includes `.venv/bin/`, so `python` and `pytest` just work
- No `(venv)` prompt — uv manages it transparently

**Verify the venv:**

```bash
which python    # → /workspace/packages/backend/.venv/bin/python
python --version
```

**Managing dependencies:**

```bash
uv add httpx                  # Add production dependency
uv add --dev pytest-debugpy   # Add dev dependency
uv lock --upgrade             # Update to latest compatible versions
```

!!! note "Always commit `uv.lock`"
    Like `package-lock.json` or `poetry.lock`, `uv.lock` is version-controlled. `uv
    sync` installs from the lockfile but never modifies it — only `uv add` and `uv
    lock` update it.

## 6. Development Workflows

### Backend (Python/FastAPI)

```bash
task sync:be              # Sync dependencies (after git pull)
task dev:be               # Start dev server (http://localhost:8000)
task test:be              # Run all backend tests
task test:be:unit         # Unit tests only (fast feedback)
task test:be:cov          # Tests with coverage report
task lint:be:fix          # Auto-format and fix lint issues
task lint:be              # Check only (no fixes)
task typecheck:be         # mypy type checking
task check                # All checks (lint + types + tests)
```

**Debugging:** Press ++f5++ → select "Debug Backend (FastAPI)" to start with the VS Code
debugger attached.

### Frontend (React/TypeScript)

```bash
task sync:fe              # Install dependencies
task dev:fe               # Start dev server (http://localhost:5173)
task test:fe              # Run tests
task lint:fe:fix          # Format and lint
```

Full task listing: run `task` or `task --list`.

## 7. Make a Change

1. Create a feature branch: `git checkout -b feature/my-change`
2. Make your changes
3. Run checks: `task check`
4. Commit (pre-commit hooks run automatically)
5. Push and create PR: `git push -u origin feature/my-change && gh pr create`

For the full contribution workflow, see the
[Contributing Guide](../contributing/index.md).

## Available Task Commands

| Command                    | Description                              |
| -------------------------- | ---------------------------------------- |
| `task dev:be`              | Start backend with hot reload            |
| `task dev:fe`              | Start frontend dev server                |
| `task test:be`             | Full backend tests (unit + integration)  |
| `task test:be:unit`        | Unit tests only (fast)                   |
| `task test:be:integration` | Robot Framework integration tests        |
| `task test:be:cov`         | Tests with coverage (terminal + XML)     |
| `task lint:be`             | Check Python linting and formatting      |
| `task lint:be:fix`         | Auto-fix Python lint/format issues       |
| `task typecheck:be`        | mypy type checking                       |
| `task check`               | All checks (lint + types + tests)        |
| `task test:fe`             | Frontend tests                           |

## Next Steps

- [Getting Started](getting-started.md) — run lumehaven with a real adapter
- [Coding Standards](../contributing/coding-standards.md) — style, docstrings, tooling
- [Testing How-To](../how-to/testing.md) — coverage thresholds and test organization
| `task docs:serve`   | Preview documentation locally       |
