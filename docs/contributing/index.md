# Contributing

Thank you for your interest in contributing to lumehaven! This guide covers the
workflow, conventions, and expectations for contributions.

!!! tip "Quick start" For setting up your development environment, see the
[Development Setup](../tutorials/development-setup.md) tutorial first.

## Workflow (GitHub Flow)

lumehaven uses GitHub Flow — `main` is always deployable, all changes go through pull
requests.

### 1. Find Work

```bash
task plan:ready       # Show unblocked tasks
bd update <id> --status in_progress   # Claim a task
```

For full details on work tracking, see
[Track Work with Beads](../how-to/work-tracking.md).

### 2. Create a Feature Branch

```bash
git checkout main && git pull
git checkout -b feature/description   # or fix/, docs/, refactor/
```

### 3. Make Changes

- Follow the [coding standards](coding-standards.md)
- Write tests for new functionality
- Update documentation if needed

### 4. Verify Locally

```bash
task test:be          # All backend tests pass
task lint:be          # Linting passes
task typecheck:be     # Type checking passes
```

Pre-commit hooks will also run automatically on commit.

### 5. Push and Create a PR

```bash
bd close <id>         # Mark your task as done
git push -u origin feature/description
gh pr create
```

!!! note "Beads syncs automatically"
    A pre-push hook runs `bd sync` to export the latest issue state before pushing.
    After pulling, a post-merge hook imports any remote changes.

### 6. Review Process

- CI must pass (tests, lint, type check, coverage thresholds)
- PRs should have clear descriptions of what and why
- Use [conventional commits](https://www.conventionalcommits.org/): `feat:`, `fix:`,
  `docs:`, `refactor:`, `test:`, `chore:`

## What to Contribute

| Area              | Examples                                                                             |
| ----------------- | ------------------------------------------------------------------------------------ |
| **New adapters**  | HomeAssistant, MQTT, Zigbee2MQTT — see [Add a New Adapter](../how-to/add-adapter.md) |
| **Bug fixes**     | Open an issue first, then submit a PR                                                |
| **Documentation** | Typo fixes, new guides, improved explanations                                        |
| **Tests**         | Increase coverage, add edge cases                                                    |

## Architecture Decisions

Significant changes should be discussed via an
[Architecture Decision Record (ADR)](../adr/index.md). If your change affects
architecture, create a new ADR as part of the PR.

## Code of Conduct

Be respectful and constructive. We're building something useful together.
