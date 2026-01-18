# Decisions Needed

A prioritized list of decisions to make before and during development.

## Priority 1: Blocking (Cannot proceed without)

### ~~D1: Build System Choice~~ → Deferred

- **Decision:** Start with native tooling (uv + bun), add Bazel later
- **Status:** Resolved - see `docs/TODO/00-project-approach.md`

### ~~D2: Backend Language/Runtime~~ → ADR-002 ✓

- **Decision:** Python + FastAPI + uv
- **Status:** Accepted - see `docs/adr/ADR-002-backend-runtime.md`
- **Future:** Rust rewrite noted as potential learning/optimization path once Python
  version is stable

### ~~D3: State Layer Architecture~~ → ADR-001 ✓

- **Decision:** Single backend with abstracted state storage (no Redis initially)
- **Status:** Accepted - see `docs/adr/ADR-001-state-management.md`
- **Rationale:** Weighted for future flexibility + resource efficiency

## Priority 2: Early Development

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

## Priority 3: Pre-Production

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

## Priority 4: Future Considerations

### D11: HomeAssistant Support

- **When to add?** - After OpenHAB is stable
- **Adapter complexity**
- **Testing against real HA instance**

### D12: Authentication

- **Single user/household assumed?**
- **Network security model (LAN-only?)**

### D13: Mobile Support

- **PWA features**
- **Responsive design requirements**

### D14: Frontend Performance Optimization

- **When to add?** - After frontend has meaningful complexity
- **Topics:** Memoization, code splitting, lazy loading
- **Reference:** awesome-copilot community patterns
- **Source:** T1e community comparison

### D15: Security Patterns

- **When to add?** - Before deployment/production
- **Topics:** Input validation, auth patterns, CSRF protection
- **Reference:** awesome-copilot security-and-owasp.instructions.md
- **Source:** T1e community comparison

## Phase 1 Setup Tasks ✅ (Complete)

### T1: Code Formatting & Linting Configuration ✅ COMPLETE

- **Status:** ✅ Complete
- **Completed:**

  - [x] `.prettierrc.json` - Frontend formatting rules (2-space indent, single quotes,
        LF line endings)
  - [x] `VERSIONING.md` - Automated versioning with setuptools_scm from git tags
  - [x] `scripts/update_version.py` - Version regeneration helper
  - [x] `.devcontainer/post-create.sh` - Auto-generate version on container startup
  - [x] T1a: `.gitattributes` Configuration - Line ending normalization across platforms
  - [x] T1b: Explicit Ruff Configuration - Python linting & formatting rules (explicit
        in pyproject.toml)
  - [x] T1c: DevContainer-Only Development Setup
    - [x] Deleted `.vscode/settings.json` - No local settings (DevContainer is official)
    - [x] Verified `.devcontainer/devcontainer.json` - All settings mirrored and
          consistent
    - [x] Created `README.md` - Project overview and quick start
    - [x] Created `.devcontainer/README.md` - DevContainer-specific documentation
  - [x] T1d: **Pre-commit Hooks Setup** - Enforce formatting checks before commits
    - [x] Created `.pre-commit-config.yaml` - Hooks for Prettier, Ruff, mypy, basic
          checks
    - [x] Updated `CONTRIBUTE.md` - Instructions for setup and workflow
    - [x] Updated `.devcontainer/post-create.sh` - Auto-installs pre-commit hooks on
          container startup

- **Remaining (Backlog for Phase 2+):**
  - [x] T1e: **Overhaul copilot-instructions** - Multi-context instruction files
        following best practices ✅
  - [ ] T1f: **Introduce custom agents** - Specifically one for planning and task
        breakdown (or multiples for different levels of planning) and implementation
  - [ ] T1g: **Evaluate Code Analysis Tools** - SonarQube, etc. for code quality and
        security
  - [ ] T1h: **GitHub Repository Settings** - Branch protection, required reviews,
        issue/PR templates
  - [ ] T1i: **Document Phase 1 Setup** - Create comprehensive summary document

---

## Notes

- **Phase 1 Setup (T1)** is ✅ **COMPLETE** — All code quality infrastructure is now in
  place
- **Key Decision:** DevContainer is the **exclusive official development environment**
  - No local `.vscode/settings.json` — all settings come from
    `.devcontainer/devcontainer.json`
  - This eliminates configuration drift and guarantees consistency across all developers
- **Single Source of Truth Architecture:**
  - Tool configs (pyproject.toml, .prettierrc.json, .gitattributes) = authoritative
    rules
  - DevContainer settings = mirrored for VS Code real-time feedback
  - Both apply identical rules via different mechanisms
- **Documentation Updated:**
  - `README.md` - Project overview and quick start
  - `docs/DEVELOPMENT-ENVIRONMENT.md` - Complete development guide
  - `.devcontainer/README.md` - DevContainer configuration details
  - `docs/DEVCONTAINER-ARCHITECTURE.md` - Architecture and design principles
- **Next Phase Tasks (T1d+):** Will focus on pre-commit hooks, GitHub settings, and code
  analysis tools
