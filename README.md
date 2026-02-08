# lumehaven

A smart home dashboard supporting common smart home frameworks. Currently supporting
OpenHAB, with HomeAssistant support planned.

**Architecture:** Backend-for-Frontend (BFF) + Single Page Application (SPA) pattern.
React frontend talks only to our backend, never directly to smart home APIs. Backend
normalizes data (units, formatting) so the frontend stays lightweight.

## Quick Start

### Prerequisites

- Docker and Docker Compose (for DevContainer)
- VS Code with DevContainers extension

### Setup (2 minutes)

```bash
# Clone the repository
git clone https://github.com/ff-fab/lumehaven.git
cd lumehaven

# Open in VS Code
code .

# In VS Code: Ctrl+Shift+P → "Dev Containers: Reopen in Container"
# DevContainer will start automatically, install dependencies, and configure everything
```

That's it! You're ready to develop.

### After Setup

- **Backend API** (FastAPI): http://localhost:8000
- **Frontend** (React dev server): http://localhost:5173

VS Code will notify you when ports are ready.

## What's Inside

This is a monorepo with three main components:

| Component         | Technology                       | Purpose                                               |
| ----------------- | -------------------------------- | ----------------------------------------------------- |
| **Backend**       | Python 3.14, FastAPI, uvicorn    | Smart home BFF, data normalization, REST + SSE API    |
| **Frontend**      | React 18+, TypeScript, Vite, bun | Dashboard UI for viewing/controlling devices          |
| **Documentation** | MkDocs                           | Project docs, architecture decisions, lessons learned |

## Development

**Want to contribute?** See [CONTRIBUTE.md](CONTRIBUTE.md) for setup instructions using
DevContainer.

## Architecture & Design Decisions

All major architectural decisions are documented in [docs/adr/](docs/adr/):

| ADR                                                 | Decision                                                                |
| --------------------------------------------------- | ----------------------------------------------------------------------- |
| [ADR-001](docs/adr/ADR-001-state-management.md)     | In-memory state storage (abstracted interface for future Redis support) |
| [ADR-002](docs/adr/ADR-002-backend-runtime.md)      | Python 3.14 + FastAPI + uv package manager                              |
| [ADR-004](docs/adr/ADR-004-frontend-stack.md)       | React 18+ + TypeScript + Vite + bun                                     |
| [ADR-005](docs/adr/ADR-005-signal-abstraction.md)   | Unified Signal model (id, value, unit, label)                           |
| [ADR-006](docs/adr/ADR-006-testing-strategy.md)     | pytest (unit) + Robot Framework (integration)                           |
| [ADR-007](docs/adr/ADR-007-documentation-system.md) | MkDocs + Material theme                                                 |

## Key Concepts

### Signal Model

The unified data model representing smart home signals:

```python
@dataclass
class Signal:
    id: str           # Unique identifier (OpenHAB item name)
    value: str        # Pre-formatted, display-ready value
    unit: str         # Unit symbol (e.g., "°C", "%", "W")
    label: str = ""   # Human-readable name
```

**Principle:** Backend normalizes all data. Frontend just displays values.

### SSE Event Flow

```
OpenHAB → [Server-Sent Events] → Backend (normalize) → [SSE] → Frontend (render)
```

Backend extracts units from OpenHAB metadata, formats values consistently, fixes
encoding issues. Frontend receives ready-to-display data.

## Common Commands

See [CONTRIBUTE.md](CONTRIBUTE.md) for detailed development workflows.

**Quick reference (via [Taskfile](https://taskfile.dev)):**

```bash
task test              # Run all tests (backend + frontend)
task test:be           # Backend tests only
task test:fe           # Frontend tests only
task dev:be            # Start backend dev server
task dev:fe            # Start frontend dev server
task lint              # Lint all code
task lint:fix          # Auto-fix lint issues
task check             # Run all checks (lint + typecheck + test)
task --list            # Show all available tasks
```

## Project Structure

```
lumehaven/
├── .devcontainer/              # DevContainer configuration
│   ├── devcontainer.json       # Container setup + VS Code settings
│   ├── docker-compose.yml      # Docker Compose definition
│   ├── Dockerfile              # Container image
│   ├── post-create.sh          # Auto-setup script
│   └── README.md               # DevContainer documentation
├── packages/
│   ├── backend/                # Python FastAPI backend
│   │   ├── src/lumehaven/      # Source code
│   │   ├── tests/              # Unit + integration tests
│   │   └── pyproject.toml      # Python configuration (Ruff, mypy, pytest)
│   └── frontend/               # React TypeScript frontend
│       ├── src/                # React components
│       ├── tests/              # Test files
│       └── package.json        # Node dependencies, scripts
├── docs/                       # Documentation
│   ├── adr/                    # Architecture Decision Records
│   ├── ll/                     # Lessons learned from PoC
│   ├── planning/               # Decisions, design docs
│   ├── DEVELOPMENT-ENVIRONMENT.md  # Development guide
│   └── TODO/                   # Task backlog
├── .prettierrc.json            # Frontend formatter config
├── .gitattributes              # Cross-platform line ending rules
├── VERSIONING.md               # Version management documentation
├── mkdocs.yml                  # Documentation site config
└── README.md                   # This file
```

## Code Quality

### Formatting

- **Python**: Ruff (88-char line length, double quotes)
- **Frontend**: Prettier (88-char line length, single quotes)
- **All files**: LF line endings (enforced via `.gitattributes`)

### Linting

- **Python**: Ruff (comprehensive rule set)
- **TypeScript**: ESLint

### Type Checking

- **Python**: mypy (strict mode)
- **TypeScript**: TypeScript compiler (strict mode)

All tools are **auto-configured in DevContainer** via `.devcontainer/devcontainer.json`.
Format on save is enabled by default.

## Versioning

Versions are automatically derived from git tags using `setuptools_scm`:

```bash
# Current version (from git tag or dev counter)
python -c "from lumehaven import __version__; print(__version__)"

# Tag a release
git tag v0.1.0
```

See [VERSIONING.md](VERSIONING.md) for details.

## Testing

### Backend Unit Tests

```bash
cd packages/backend
uv run pytest tests/unit/ -v
```

### Backend Integration Tests (Robot Framework)

```bash
cd packages/backend
# Requires OpenHAB instance running
uv run robot tests/integration/api_tests.robot
```

### Frontend Tests

```bash
cd packages/frontend
bun test
```

## Contributing

1. Create a feature branch from `main`
2. Make changes following the project's code quality standards
3. Open a pull request for review
4. Merge after approval

Run `task plan` to see phase progress, or `bd ready` for available work.

## Documentation

Full development guide:
[docs/DEVELOPMENT-ENVIRONMENT.md](docs/DEVELOPMENT-ENVIRONMENT.md)

DevContainer guide: [.devcontainer/README.md](.devcontainer/README.md)

Architecture decisions: [docs/adr/](docs/adr/)

Lessons from PoC: [docs/ll/](docs/ll/)

## License

MIT License. See [LICENSE](LICENSE) for details.

## Lessons from Proof-of-Concept

The `old/` directory contains a working PoC that informed this project. Key learnings:

- **SSE in React** — Must use `useEffect` with proper cleanup, not in render
- **OpenHAB special values** — `"UNDEF"` and `"NULL"` are valid states
- **Encoding issues** — OpenHAB SSE may have encoding problems
- **Unit extraction** — Can derive from `stateDescription.pattern` metadata

See [docs/ll/](docs/ll/) for detailed lessons learned.
