# Project Approach: lumehaven

## Overview

Restart of the home-dash smart home dashboard project from scratch, with clean architecture decisions and modern tooling.

## ✅ Phase 0: Foundation Decisions (Complete)

All blocking architectural decisions have been made and documented as ADRs:

| Decision | ADR | Summary |
|----------|-----|---------|
| Build System | Deferred | Start with uv + bun, add Bazel later |
| Backend Runtime | [ADR-002](../adr/ADR-002-backend-runtime.md) | Python + FastAPI + uv |
| State Management | [ADR-001](../adr/ADR-001-state-management.md) | In-memory, abstracted interface |
| Frontend Stack | [ADR-004](../adr/ADR-004-frontend-stack.md) | React + Vite + TypeScript + bun |
| Signal Abstraction | [ADR-005](../adr/ADR-005-signal-abstraction.md) | Minimal: id, value, unit, label |
| Testing Strategy | [ADR-006](../adr/ADR-006-testing-strategy.md) | pytest + Robot Framework |
| Documentation | [ADR-007](../adr/ADR-007-documentation-system.md) | MkDocs + Material |

## 🚧 Phase 1: Project Setup (Current)

1. [ ] Initialize `packages/backend/` with uv + pyproject.toml
2. [ ] Initialize `packages/frontend/` with bun + Vite
3. [ ] Set up pytest and basic test structure
4. [ ] Set up shared configuration (`.editorconfig`, linters, formatters)
5. [ ] Set up MkDocs documentation
6. [ ] Set up GitHub Actions CI pipeline

## Phase 2: Core Backend

1. [ ] Signal model (pydantic v2)
2. [ ] SmartHomeAdapter protocol
3. [ ] OpenHAB adapter (port from PoC)
4. [ ] FastAPI endpoints (REST + SSE)
5. [ ] Unit tests for parsing logic
6. [ ] Robot Framework integration tests

## Phase 3: Frontend Shell

1. [ ] React app with Vite + TypeScript
2. [ ] SSE client hook with proper cleanup
3. [ ] Basic dashboard layout
4. [ ] Signal display components
5. [ ] Vitest smoke tests

## Phase 4: Integration & Deployment

1. [ ] Docker/container configuration
2. [ ] Robot Framework E2E tests
3. [ ] Raspberry Pi deployment strategy (D8)
4. [ ] Configuration management (D9)

## Phase 5: Feature Parity with PoC

1. [ ] Weather forecast display
2. [ ] Temperature monitoring
3. [ ] Camera/media integration
4. [ ] Additional widgets as needed

---

## Key Architectural Drivers

From the PoC and project goals:

1. **Low browser workload** - Raspberry Pi 4 target means efficient frontend
2. **Real-time updates** - SSE proven effective, avoid polling
3. **Smart home agnostic** - Abstract OpenHAB vs HomeAssistant via adapters
4. **Unit normalization** - Backend handles SI/US conversion, value formatting
5. **Learning goal** - Bazel deferred but remains a future learning opportunity
6. **Monorepo** - Single repository for all components
7. **Modern tooling** - bun over node, uv over pip/poetry
