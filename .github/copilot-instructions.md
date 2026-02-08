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
│   ├── planning/             # Decision tracker, design docs
│   └── TODO/                 # Technical debt, deferred items
└── old/                      # PoC reference (do not modify)
```

## Reference Material

- `old/` - Proof-of-concept (reference only, do not modify)
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

4. **Close beads tasks and commit state**

   ```bash
   bd close <id>         # Close finished work
   bd sync               # Export to JSONL
   git add .beads/ && git commit -m "chore: sync beads state"
   ```

5. **Push and create pull request**

   ```bash
   git push -u origin feature/description
   gh pr create
   ```

**Key Principle:** `main` is always deployable. All changes go through PRs. Beads state
must be committed before pushing — the pre-push hook enforces this.

## Issue Tracking (Beads)

This project uses **bd (beads)** for issue tracking — a git-backed graph issue tracker
for AI agents. Issues are stored as JSONL in `.beads/` and committed to git.

Run `bd prime` for full workflow context.

**Quick reference:**

- `bd ready` — Find unblocked work
- `bd create "Title" --type task --priority 2` — Create issue
- `bd update <id> --claim` — Claim a task (assigns + sets in_progress)
- `bd close <id>` — Complete work
- `bd dep add <child> <parent>` — Add dependency
- `bd sync` — Sync with git (run at session end)

**Workflow:** Check `bd ready` at session start. Claim work, implement, close when done.
Commit beads state (`bd sync && git add .beads/ && git commit`) before pushing.

### Beads vs TODO: Two Systems, Distinct Purposes

This project uses **two complementary tracking systems**. Do not conflate them.

| System           | Purpose            | Content type            | Location     |
| ---------------- | ------------------ | ----------------------- | ------------ |
| **Beads (`bd`)** | Work tracking      | Actionable tasks, epics | `.beads/`    |
| **TODO folder**  | Deferred decisions | Rich deliberation docs  | `docs/TODO/` |

**Beads** tracks _work_: things to build, fix, or ship. Items flow through
`ready → in_progress → closed`.

**TODO items** (T1–Tn) are _deliberation documents_ — deferred decisions, architectural
evaluations, and technical debt assessments. They contain structured options with
advantages/disadvantages, trade-offs, and ADR references. They are mini-ADRs-in-waiting,
not work items.

### Gate Tasks (Hybrid Bridge)

When a TODO item has a **phase trigger** (e.g., "revisit when building frontend
components"), create a **gate task** in beads that:

1. References the TODO item: `"Evaluate signal value type (T6, docs/TODO/)"`
2. Is added as a **dependency** of the first task that would be affected
3. Contains no decision logic itself — points to the TODO doc for full context

This enforces that deferred decisions are evaluated at the right point in the workflow,
without duplicating the rich deliberation content into beads.

**Rules:**

- **Date-triggered TODOs** (e.g., "Review date: June 2026") stay markdown-only. Beads
  has no calendar awareness.
- **Phase-triggered TODOs** get a gate task as a dependency of the relevant phase task
- **When creating a new TODO item**, always check whether it needs a gate task
- **When closing a gate task**, the outcome should be one of:
  - A new ADR (if the decision is significant)
  - An update to the existing TODO item marking it resolved
  - New beads tasks created from the decision

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
