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
| 007 | Documentation      | Zensical + mkdocstrings (modern, performant)  |

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
│   └── planning/             # Roadmap, decision tracker
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

3. **Push and create pull request**

   ```bash
   git push -u origin feature/description
   gh pr create
   ```

4. **Merge after review**
   - Pre-commit hooks must pass
   - Squash merge preferred
   - Delete branch after merge

**Key Principle:** `main` is always deployable. All changes go through PRs.
