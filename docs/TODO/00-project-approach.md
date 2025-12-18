# Project Approach: lumehaven

## Overview

Restart of the home-dash smart home dashboard project from scratch, with clean architecture decisions and modern tooling.

## Phase 0: Foundation Decisions (Do First)

Before writing any code, these architectural decisions need to be made and documented as ADRs:

### 1. Monorepo Build System
**Decision:** Start with native tooling (uv, bun), add Bazel later as a learning exercise.

Rationale: Bazel has a steep learning curve and would slow down initial progress. Native tools (uv for Python, bun for JS/TS) are fast and sufficient for a small monorepo. Bazel can be introduced once the project structure stabilizes.

**Deferred to:** Phase 5 or later (see `docs/TODO/02-bazel-integration.md` when ready)

### 2. Backend Runtime & Framework
**Question:** What runtime and framework for the BFF (Backend for Frontend)?
**Options to evaluate:**
- Python + FastAPI (proven in PoC)
- Python + Litestar
- Bun + Hono/Elysia
- Rust + Axum (mentioned in old TODO)

**ADR needed:** `docs/adr/ADR-002-backend-framework.md`

### 3. State Management / Message Broker
**Question:** How do we handle real-time state from smart home → backend → frontend?
**Options to evaluate:**
- Redis (proven in PoC, but adds operational complexity)
- In-memory with event bus
- SQLite + polling
- Direct passthrough (no intermediate store)

**ADR needed:** `docs/adr/ADR-003-state-management.md`

### 4. Frontend Framework & Tooling
**Question:** React stack specifics?
**Options to evaluate:**
- React + Vite (mentioned in old TODO)
- Preact (lighter weight)
- Solid.js
- Svelte

**ADR needed:** `docs/adr/ADR-004-frontend-framework.md`

### 5. Smart Home Abstraction Layer
**Question:** How do we abstract OpenHAB/HomeAssistant differences?
**Decisions needed:**
- Common item/entity model
- Event stream normalization
- Command interface

**ADR needed:** `docs/adr/ADR-005-smart-home-abstraction.md`

## Phase 1: Repository Setup

Once Phase 0 decisions are made:

1. [ ] Initialize Bazel workspace (`WORKSPACE.bazel`, `.bazelrc`)
2. [ ] Set up rules for chosen technologies (rules_python, rules_js, etc.)
3. [ ] Configure uv for Python dependency management
4. [ ] Configure bun for JavaScript/TypeScript
5. [ ] Set up shared configuration (`.editorconfig`, linters, formatters)
6. [ ] Create initial `BUILD.bazel` files for packages
7. [ ] Set up GitHub Actions CI pipeline

## Phase 2: Core Backend

1. [ ] Smart home abstraction layer (protocol/interface)
2. [ ] OpenHAB adapter implementation
3. [ ] SSE event stream consumer
4. [ ] BFF API layer (REST + SSE endpoints)
5. [ ] Unit tests with pytest/nox

## Phase 3: Frontend Shell

1. [ ] React app scaffold with Vite
2. [ ] SSE client hook
3. [ ] Basic dashboard layout
4. [ ] Widget component architecture

## Phase 4: Integration & Deployment

1. [ ] Docker/container configuration
2. [ ] Raspberry Pi deployment strategy
3. [ ] Configuration management (env vars, secrets)

## Phase 5: Feature Parity with PoC

1. [ ] Weather forecast display
2. [ ] Temperature monitoring
3. [ ] Camera/media integration
4. [ ] Additional widgets as needed

---

## Key Architectural Drivers (to inform ADRs)

From the PoC and project goals:

1. **Low browser workload** - Raspberry Pi 4 target means we need efficient frontend
2. **Real-time updates** - SSE proven effective, avoid polling
3. **Smart home agnostic** - Must abstract OpenHAB vs HomeAssistant
4. **Unit normalization** - Backend handles SI/US conversion, value formatting
5. **Learning goal** - Bazel is explicitly for learning, not just pragmatism
6. **Monorepo** - Single repository for all components
7. **Modern tooling** - bun over node, uv over pip/poetry
