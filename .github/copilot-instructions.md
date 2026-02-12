# GitHub Copilot Instructions

## Project Overview

**lumehaven** - A smart home dashboard supporting common smart home frameworks, starting
with OpenHAB and later HomeAssistant.

**Architecture:** BFF + SPA pattern. React frontend talks only to our backend, never
directly to smart home APIs. Backend normalizes data (units, formatting) so the frontend
stays "dumb" and lightweight.

## Architecture Decision Records

All major decisions are documented in `docs/adr/`. **Follow these decisions:**

| ADR | Decision             | Summary                                                     |
| --- | -------------------- | ----------------------------------------------------------- |
| 001 | State Management     | In-memory, abstracted interface, no Redis                   |
| 002 | Backend Runtime      | Python + FastAPI + uv                                       |
| 004 | Frontend Stack       | React + Vite + TypeScript + bun (amended: routing, locale)  |
| 005 | Signal Abstraction   | Enriched model (amended by ADR-010)                         |
| 006 | Testing              | pytest (unit) + Robot Framework (integration)               |
| 007 | Documentation        | MkDocs-Material + mkdocstrings                              |
| 008 | Package Architecture | Two packages: `@lumehaven/core` + `@lumehaven/react`        |
| 009 | Dashboard Ownership  | App + injection; reference dashboard in monorepo            |
| 010 | Signal Enrichment    | Typed value, `display_value`, `available`, `signal_type`    |
| 011 | Command Architecture | POST command endpoint, optimistic updates, adapter protocol |

Create new ADRs for any major changes or decisions.

## Repository Structure

```
lumehaven/
├── packages/
│   ├── backend/              # Python BFF (FastAPI)
│   ├── core/                 # @lumehaven/core — vanilla TS, zero React deps (ADR-008)
│   ├── react/                # @lumehaven/react — thin React bindings (ADR-008)
│   └── frontend/             # Reference dashboard SPA (ADR-009)
├── docs/
│   ├── adr/                  # Architecture Decision Records (authoritative)
│   ├── demos/                # Showboat proof-of-work demos (not published)
│   ├── planning/             # Decision tracker, design docs
│   └── TODO/                 # Technical debt, deferred items
└── old/                      # PoC reference (do not modify)
```

## Reference Material

- `old/` - Proof-of-concept (reference only, do not modify)
- `docs/adr/` - Architecture Decision Records (**authoritative**)

<!-- Workflow (git flow, beads, quality gates, coverage thresholds, showboat) is
     defined in .github/instructions/workflow.instructions.md — the single source
     of truth. Do not duplicate workflow content here. -->
