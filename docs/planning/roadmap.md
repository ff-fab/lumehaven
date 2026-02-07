# Project Approach: lumehaven

## Overview

Restart of the home-dash smart home dashboard project from scratch, with clean
architecture decisions and modern tooling.

**Development Strategy:** Backend-first approach — mature the backend fully (signals,
adapters, testing, documentation, CI) before starting frontend work.

## ✅ Phase 0: Foundation Decisions (Complete)

All blocking architectural decisions have been made and documented as ADRs:

| Decision           | ADR                                               | Summary                              |
| ------------------ | ------------------------------------------------- | ------------------------------------ |
| Build System       | Deferred                                          | Start with uv + bun, add Bazel later |
| Backend Runtime    | [ADR-002](../adr/ADR-002-backend-runtime.md)      | Python + FastAPI + uv                |
| State Management   | [ADR-001](../adr/ADR-001-state-management.md)     | In-memory, abstracted interface      |
| Frontend Stack     | [ADR-004](../adr/ADR-004-frontend-stack.md)       | React + Vite + TypeScript + bun      |
| Signal Abstraction | [ADR-005](../adr/ADR-005-signal-abstraction.md)   | Minimal: id, value, unit, label      |
| Testing Strategy   | [ADR-006](../adr/ADR-006-testing-strategy.md)     | pytest + Robot Framework             |
| Documentation      | [ADR-007](../adr/ADR-007-documentation-system.md) | MkDocs-Material + mkdocstrings       |

## ✅ Phase 1: Backend Core (Complete)

| Task                                        | Status |
| ------------------------------------------- | ------ |
| Initialize `packages/backend/` with uv      | ✅     |
| Signal model (pydantic v2)                  | ✅     |
| SmartHomeAdapter protocol                   | ✅     |
| OpenHAB adapter (ported from PoC)           | ✅     |
| FastAPI endpoints (REST + SSE)              | ✅     |
| Multi-adapter support with registry pattern | ✅     |
| Basic unit tests for core logic             | ✅     |
| Basic Robot Framework integration tests     | ✅     |

## 🚧 Phase 2: Backend Maturity (Current)

| Task                                              | Status |
| ------------------------------------------------- | ------ |
| Comprehensive test coverage per ADR-006           | ✅     |
| GitHub Actions CI pipeline                        | ✅     |
| Integration tests in CI (subprocess mock servers) | ✅     |
| Shared config (.editorconfig)                     | ✅     |
| Pre-commit hooks                                  | ✅     |
| Set up MkDocs-Material documentation site         | 🚧     |
| Add mkdocstrings for API documentation            | 🚧     |
| Add docs build validation to CI (PR trigger)      | 🚧     |

## ⏳ Phase 2b (Interrupt): Implement Beads

| Task                                   | Status |
| -------------------------------------- | ------ |
| Install beads CLI\* for agent planning | ❌     |
| Integrate beads and transfer roadmap   | ❌     |

\*) https://github.com/steveyegge/beads

## ⏳ Phase 3: Frontend Implementation

| Task                                        | Status |
| ------------------------------------------- | ------ |
| Initialize `packages/frontend/` with bun    | ❌     |
| React app with Vite + TypeScript            | ❌     |
| SSE client hook with proper cleanup         | ❌     |
| Basic dashboard layout                      | ❌     |
| Signal display components                   | ❌     |
| Vitest smoke tests                          | ❌     |
| Refine test strategy for frontend (ADR-006) | ❌     |

## ⏳ Phase 4: Integration & Deployment

| Task                                        | Status |
| ------------------------------------------- | ------ |
| Docker/container configuration (D8)         | ❌     |
| Robot Framework E2E tests                   | ❌     |
| Docker Compose infrastructure for CI/E2E \* | ❌     |
| Deployment strategy                         | ❌     |
| Configuration management (D9)               | ❌     |
| Observability setup (D10)                   | ❌     |

\*) see Option C in TODO/ci-integration-tests.md

## ⏳ Phase 5: Maintenance & Future Development

| Task                        | Status |
| --------------------------- | ------ |
| Add SBOM functionality      | ❌     |
| Prometheus metrics endpoint | ❌     |
| Weather forecast display    | ❌     |
| Temperature monitoring      | ❌     |
| Camera/media integration    | ❌     |
| HomeAssistant adapter (D12) | ❌     |
| Bazel build system (D1)     | ❌     |
| PR preview deploys for docs | ❌     |
| Additional widgets          | ❌     |

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
