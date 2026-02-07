# Contributing

Thank you for your interest in contributing to lumehaven! This guide covers the
workflow, conventions, and expectations for contributions.

!!! tip "Quick start" For setting up your development environment, see the
[Development Setup](../tutorials/development-setup.md) tutorial first.

## Workflow (GitHub Flow)

lumehaven uses GitHub Flow — `main` is always deployable, all changes go through pull
requests.

### 1. Create a Feature Branch

```bash
git checkout main && git pull
git checkout -b feature/description   # or fix/, docs/, refactor/
```

### 2. Make Changes

- Follow the [coding standards](coding-standards.md)
- Write tests for new functionality
- Update documentation if needed

### 3. Verify Locally

```bash
task test:be          # All backend tests pass
task lint:be          # Linting passes
task typecheck:be     # Type checking passes
```

Pre-commit hooks will also run automatically on commit.

### 4. Push and Create a PR

```bash
git push -u origin feature/description
gh pr create
```

### 5. Review Process

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
