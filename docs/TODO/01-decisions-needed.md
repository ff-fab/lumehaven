# Decisions Needed

A prioritized list of decisions to make before and during development.

## Priority 1: Blocking (Cannot proceed without)

### ~~D1: Build System Choice~~ → Deferred
- **Decision:** Start with native tooling (uv + bun), add Bazel later
- **Status:** Resolved - see `docs/TODO/00-project-approach.md`

### ~~D2: Backend Language/Runtime~~ → ADR-002 ✓
- **Decision:** Python + FastAPI + uv
- **Status:** Accepted - see `docs/adr/ADR-002-backend-runtime.md`
- **Future:** Rust rewrite noted as potential learning/optimization path once Python version is stable

### ~~D3: State Layer Architecture~~ → ADR-001 ✓
- **Decision:** Single backend with abstracted state storage (no Redis initially)
- **Status:** Accepted - see `docs/adr/ADR-001-state-management.md`
- **Rationale:** Weighted for future flexibility + resource efficiency

## Priority 2: Early Development

### ~~D4: Frontend Stack Details~~ → ADR-004 ✓
- **Decision:** React + Vite + TypeScript
- **Status:** Accepted - see `docs/adr/ADR-004-frontend-stack.md`
- **Note:** Close call with Preact; React chosen for ecosystem breadth and reputation

### D5: Smart Home Abstraction
- **How much abstraction?** - Full adapter pattern vs lighter approach
- **What's the common model?** - Define Item/Entity schema
- **Next step:** Create ADR-005, define types

### D6: Testing Strategy
- **Unit test frameworks** - pytest, vitest
- **Integration testing** - How to mock smart home APIs
- **E2E testing** - Playwright? Cypress? None initially?

### D7: Documentation System
- **Leaning:** Sphinx, possibly with sphinx-needs for requirements traceability
- **Considerations:**
  - Sphinx: Mature, great for technical docs, supports reStructuredText + Markdown
  - sphinx-needs: Adds requirements/specs management, traceability matrices
  - MkDocs: Simpler, Markdown-native, but less powerful
  - Docusaurus: React-based, overkill for this project
- **Questions:**
  - Do we need formal requirements traceability (sphinx-needs)?
  - How to integrate with ADRs?
  - API docs generation (autodoc for Python, TypeDoc for TS)?
- **Next step:** Create ADR-007

## Priority 3: Pre-Production

### D7: Deployment Model
- **Container orchestration** - Docker Compose, Kubernetes, or simpler?
- **Target:** Raspberry Pi 4
- **Update mechanism**

### D8: Configuration Management
- **Environment variables vs config files**
- **Secrets handling**
- **Multi-environment support (dev/prod)**

### D9: Observability
- **Logging** - Structured logging format
- **Metrics** - Prometheus? None?
- **Error tracking**

## Priority 4: Future Considerations

### D10: HomeAssistant Support
- **When to add?** - After OpenHAB is stable
- **Adapter complexity**
- **Testing against real HA instance

### D11: Authentication
- **Single user/household assumed?**
- **Network security model (LAN-only?)**

### D12: Mobile Support
- **PWA features**
- **Responsive design requirements**
