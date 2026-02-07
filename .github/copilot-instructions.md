# GitHub Copilot Instructions

## Project Overview

**lumehaven** - A smart home dashboard supporting common smart home frameworks, starting
with OpenHAB and later HomeAssistant.

**Architecture:** BFF + SPA pattern. React frontend talks only to our backend, never
directly to smart home APIs. Backend normalizes data (units, formatting) so the frontend
stays "dumb" and lightweight.

## Architecture Decision Records

All major decisions are documented in `docs/adr/`. **Follow these decisions:**

| ADR | Decision           | Summary                                       |
| --- | ------------------ | --------------------------------------------- |
| 001 | State Management   | In-memory, abstracted interface, no Redis     |
| 002 | Backend Runtime    | Python + FastAPI + uv                         |
| 004 | Frontend Stack     | React + Vite + TypeScript + bun               |
| 005 | Signal Abstraction | Minimal: `id`, `value`, `unit`, `label`       |
| 006 | Testing            | pytest (unit) + Robot Framework (integration) |
| 007 | Documentation      | MkDocs-Material + mkdocstrings                |

Create new ADRs for any major changes or decisions.

## Repository Structure

```
lumehaven/
├── packages/
│   ├── backend/              # Python BFF (FastAPI)
│   └── frontend/             # React SPA (TypeScript)
├── docs/
│   ├── adr/                  # Architecture Decision Records (authoritative)
│   ├── ll/                   # Lessons learned from PoC
│   ├── planning/             # Roadmap, decision tracker
│   └── TODO/                 # Technical debt, deferred items
└── old/                      # PoC reference (do not modify)
```

## Reference Material

- `old/` - Proof-of-concept (reference only, do not modify)
- `docs/ll/` - Lessons learned from PoC, OpenHAB API quirks
- `docs/adr/` - Architecture Decision Records (**authoritative**)

## Git Workflow (GitHub Flow)

**CRITICAL: Always follow this workflow. Never push directly to main.**

1. **Create feature branch from main**

   ```bash
   git checkout main && git pull
   git checkout -b feature/description  # or fix/, docs/, etc.
   ```

2. **Make commits with clear messages**

   ```bash
   git commit -m "feat: clear description of changes"
   # Use conventional commits: feat:, fix:, docs:, refactor:, etc.
   ```

3. Ensure all tests pass and coverage thresholds are met

   - Pre-commit hooks must pass
   - Unit tests must pass
   - Test coverage thresholds must be met

   ```bash
   task test:be        # Run backend tests
   task test:fe        # Run frontend tests
   ```

   Note:

   - shared fixtures (in tests/fixtures/) should be used to avoid duplication
   - always ensure tests incl. fixtures, documentation and feature are in sync

4. **Push and create pull request**

   ```bash
   git push -u origin feature/description
   gh pr create
   ```

**Key Principle:** `main` is always deployable. All changes go through PRs.

## Test Coverage Thresholds

Per-module coverage thresholds are enforced at the **module** (directory) level — files
are aggregated (weighted by statement/branch count) before checking against the
threshold. See `docs/testing/03-coverage-strategy.md`.

**Single source of truth:** `packages/backend/tests/coverage_config.py` —
`MODULE_THRESHOLDS` dict. Both the pytest hook (`conftest.py`) and the standalone script
import from it.

| Risk Level | Line | Branch | Matching Rule                                    |
| ---------- | ---- | ------ | ------------------------------------------------ |
| Critical   | 90%  | 85%    | `adapters/*` — any adapter implementation subdir |
| High       | 85%  | 80%    | `adapters` (framework), `config`, `state`        |
| Medium     | 80%  | 75%    | `api`                                            |
| Low        | 80%  | 70%    | `core`                                           |
| Low        | 30%  | 0%     | `__root__` (package init, version)               |
| Excluded   | —    | —      | `main.py` (entrypoint, Robot integration only)   |

New adapter implementations (e.g. `adapters/homeassistant/`) auto-inherit the Critical
threshold — no config changes needed.
