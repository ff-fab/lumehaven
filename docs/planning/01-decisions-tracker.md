# Decisions Tracker

Tracking architectural decisions for lumehaven. Completed decisions have ADRs in
`docs/adr/`.

## ✅ Completed Decisions

### ~~D1: Build System Choice~~ → Deferred

- **Decision:** Start with native tooling (uv + bun), add Bazel later
- **Status:** Resolved - see `docs/planning/00-project-approach.md`

### ~~D2: Backend Language/Runtime~~ → ADR-002 ✓

- **Decision:** Python + FastAPI + uv
- **Status:** Accepted - see `docs/adr/ADR-002-backend-runtime.md`
- **Future:** Rust rewrite noted as potential learning/optimization path once Python
  version is stable

### ~~D3: State Layer Architecture~~ → ADR-001 ✓

- **Decision:** Single backend with abstracted state storage (no Redis initially)
- **Status:** Accepted - see `docs/adr/ADR-001-state-management.md`
- **Rationale:** Weighted for future flexibility + resource efficiency

### ~~D4: Frontend Stack Details~~ → ADR-004 ✓

- **Decision:** React + Vite + TypeScript
- **Status:** Accepted - see `docs/adr/ADR-004-frontend-stack.md`
- **Note:** Close call with Preact; React chosen for ecosystem breadth and reputation

### ~~D5: Signal Identity and Metadata Strategy~~ → ADR-005 ✓

- **Decision:** Minimal Signal abstraction (id, value, unit, label) based on PoC pattern
- **Status:** Accepted - see `docs/adr/ADR-005-signal-abstraction.md`
- **Rationale:** Proven in PoC, simple extension path, keeps frontend "dumb"

### ~~D6: Testing Strategy~~ → ADR-006 ✓

- **Decision:** Hybrid approach - pytest for unit tests, Robot Framework for
  integration/acceptance
- **Status:** Accepted - see `docs/adr/ADR-006-testing-strategy.md`
- **Rationale:** Backend-first focus, human-readable scenarios, extensible to E2E

### ~~D7: Documentation System~~ → ADR-007 ✓

- **Decision:** MkDocs + Material theme + mkdocstrings for Python API docs
- **Status:** Accepted - see `docs/adr/ADR-007-documentation-system.md`
- **Rationale:** Markdown-native, simple, beautiful output, good Python integration

## 🔜 Pending Decisions (Pre-Production)

These decisions can be made during implementation when needed.

### D8: Deployment Model

- **Container orchestration** - Docker Compose, Kubernetes, or simpler?
- **Target:** Raspberry Pi 4
- **Update mechanism**

### D9: Configuration Management

- **Environment variables vs config files**
- **Secrets handling**
- **Multi-environment support (dev/prod)**

### D10: Observability

- **Logging** - Structured logging format
- **Metrics** - Prometheus? None?
- **Error tracking**

## 📋 Future Considerations

These will be addressed after core functionality is complete.

### D11: Multi-Adapter & HomeAssistant Support

- **Planning doc:** [`02-multi-adapter-support.md`](02-multi-adapter-support.md)
- **When to add?** - After OpenHAB adapter is stable
- **Key issues:** Signal ID collisions, protocol additions, config schema
- **Phases:** Protocol hardening → ID namespacing → Orchestration → HA adapter

### D12: Authentication

- **Single user/household assumed?**
- **Network security model (LAN-only?)**

### D13: Mobile Support

- **PWA features**
- **Responsive design requirements**
