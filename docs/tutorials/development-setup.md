# Development Setup

!!! abstract "What you'll learn" Set up a full development environment using the dev
container, understand the project structure, run tests, and make your first
contribution.

!!! warning "Work in progress" This tutorial will be completed as part of the
documentation content phase.

## Prerequisites

- [Docker](https://www.docker.com/) installed
- [VS Code](https://code.visualstudio.com/) with the
  [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

## Steps

### 1. Open in Dev Container

```bash
git clone https://github.com/ff-fab/lumehaven.git
code lumehaven
# VS Code will prompt: "Reopen in Container" → click it
```

The dev container includes all required tools: Python 3.14, Node.js, uv, bun, Task, and
pre-commit hooks.

### 2. Verify the Setup

```bash
task test:be:unit   # Run backend unit tests
task lint:be        # Check linting
task typecheck:be   # Check types
```

### 3. Understand the Project Structure

```
lumehaven/
├── packages/
│   ├── backend/          # Python BFF (FastAPI)
│   │   ├── src/lumehaven/  # Source code
│   │   └── tests/          # pytest + Robot Framework
│   └── frontend/         # React SPA (TypeScript) — Phase 3
├── docs/                 # This documentation
├── Taskfile.yml          # Cross-platform task runner
└── mkdocs.yml            # Documentation site config
```

### 4. Make a Change and Run Tests

1. Create a feature branch: `git checkout -b feature/my-change`
2. Make your changes
3. Run tests: `task test:be`
4. Push and create a PR: `git push -u origin feature/my-change`

See the [Contribution Guide](../contributing/index.md) for the full workflow.

## Available Task Commands

Run `task` to see all available commands. Key ones:

| Command             | Description                         |
| ------------------- | ----------------------------------- |
| `task test:be`      | Run all backend tests with coverage |
| `task test:be:unit` | Run unit tests only (fast)          |
| `task lint:be`      | Check linting and formatting        |
| `task typecheck:be` | Run mypy type checking              |
| `task dev:be`       | Start backend with hot reload       |
| `task docs:serve`   | Preview documentation locally       |
