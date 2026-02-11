# Contributing to lumehaven

Thank you for contributing! This page gets you oriented quickly — detailed guides live
in the [documentation site](https://ff-fab.github.io/lumehaven/).

## Quick Start

This project uses **VS Code DevContainers** — everything auto-configures:

```bash
git clone https://github.com/ff-fab/lumehaven.git
code lumehaven
# VS Code prompt: "Reopen in Container" → click it
# Wait for setup (~2 min). Ready to code!
```

For full details (GitHub CLI auth, Python venv, troubleshooting):
**[Development Setup Tutorial](https://ff-fab.github.io/lumehaven/tutorials/development-setup/)**

## Common Commands

| Command             | Description                         |
| ------------------- | ----------------------------------- |
| `task dev:be`       | Start backend with hot reload       |
| `task test:be`      | Run all backend tests with coverage |
| `task test:be:unit` | Unit tests only (fast feedback)     |
| `task lint:be`      | Check linting and formatting        |
| `task typecheck:be` | mypy type checking                  |
| `task check`        | All checks (lint + types + tests)   |

Full command reference:
**[Testing How-To](https://ff-fab.github.io/lumehaven/how-to/testing/)**

## Workflow (GitHub Flow)

1. Branch from `main`: `git checkout -b feature/description`
2. Make changes, run `task check`
3. Push and create PR: `gh pr create`
4. CI must pass; use [conventional commits](https://www.conventionalcommits.org/)
   (`feat:`, `fix:`, `docs:`, `refactor:`)

Full workflow:
**[Contributing Guide](https://ff-fab.github.io/lumehaven/contributing/)**

## Key Resources

| Topic              | Where                                                                          |
| ------------------ | ------------------------------------------------------------------------------ |
| Development setup  | [Tutorial](https://ff-fab.github.io/lumehaven/tutorials/development-setup/)    |
| Coding standards   | [Standards](https://ff-fab.github.io/lumehaven/contributing/coding-standards/) |
| Testing & coverage | [How-To](https://ff-fab.github.io/lumehaven/how-to/testing/)                   |
| Architecture       | [Explanation](https://ff-fab.github.io/lumehaven/explanation/architecture/)    |
| Configuration      | [Reference](https://ff-fab.github.io/lumehaven/reference/configuration/)       |
| Adding adapters    | [How-To](https://ff-fab.github.io/lumehaven/how-to/add-adapter/)               |
| ADRs               | [decisions](https://ff-fab.github.io/lumehaven/adr/)                           |

## Questions?

Open an issue if something isn't clear.
