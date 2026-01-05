# GitHub Copilot Instructions

## Project Overview

**lumehaven** - A smart home dashboard supporting common smart home frameworks, starting with OpenHAB and later HomeAssistant.

**Architecture:** BFF + SPA pattern. React frontend talks only to our backend, never directly to smart home APIs. Backend normalizes data (units, formatting) so the frontend stays "dumb" and lightweight.

## Decided Technology Stack

All major architectural decisions are documented in `docs/adr/`. **Follow these decisions during implementation.**

### Backend (ADR-001, ADR-002)
| Component | Choice | Notes |
|-----------|--------|-------|
| Runtime | Python 3.14+ | |
| Framework | FastAPI | Async, good OpenAPI support |
| Package Manager | uv | Fast, replaces pip/poetry |
| Validation | pydantic v2 | PoC used v1, upgrade required |
| State Storage | In-memory (abstracted) | No Redis initially, interface allows swapping |

### Frontend (ADR-004)
| Component | Choice | Notes |
|-----------|--------|-------|
| Framework | React 18+ | Chosen over Preact for ecosystem |
| Build Tool | Vite | Fast, modern |
| Language | TypeScript | Strict mode |
| Runtime | bun | Replaces node.js |

### Signal Model (ADR-005)
The unified data model for smart home signals:
```python
@dataclass
class Signal:
    id: str           # Unique identifier (OpenHAB item name / HA entity_id)
    value: str        # Pre-formatted, display-ready value
    unit: str         # Unit symbol (e.g., "°C", "%", "W")
    label: str = ""   # Human-readable name
```

**Key principle:** Backend normalizes all data. Frontend just displays `value` and `unit`.

### Testing (ADR-006)
| Layer | Tool | Notes |
|-------|------|-------|
| Backend Unit Tests | pytest + pytest-asyncio | Primary focus |
| Integration/Acceptance | Robot Framework + RESTinstance | Human-readable scenarios |
| Frontend | Vitest | Lightweight, deferred |
| E2E | Robot Framework + Browser Library | Deferred until UI stable |

### Documentation (ADR-007)
| Component | Choice |
|-----------|--------|
| Site Generator | MkDocs |
| Theme | Material for MkDocs |
| Python API Docs | mkdocstrings |

### Build System
| Tool | Purpose | Status |
|------|---------|--------|
| uv | Python packages | Use now |
| bun | JS/TS packages | Use now |
| Bazel | Monorepo orchestration | Deferred (learning goal) |

## Repository Structure

```
lumehaven/
├── .devcontainer/            # Development container config
├── packages/
│   ├── backend/              # Python BFF (FastAPI)
│   │   ├── src/lumehaven/
│   │   │   ├── main.py       # FastAPI app entry point
│   │   │   ├── config.py     # Pydantic settings
│   │   │   ├── core/         # Domain models (Signal, exceptions)
│   │   │   ├── adapters/     # Smart home adapters (OpenHAB, etc.)
│   │   │   ├── api/          # REST routes + SSE endpoints
│   │   │   └── state/        # In-memory signal store
│   │   ├── tests/
│   │   │   ├── unit/         # pytest
│   │   │   ├── integration/  # Robot Framework
│   │   │   └── fixtures/
│   │   └── pyproject.toml
│   ├── frontend/             # React SPA (TypeScript) - TODO
│   │   ├── src/
│   │   ├── tests/
│   │   └── package.json
│   └── shared/               # Shared types/schemas (if needed)
├── docs/
│   ├── adr/                  # Architecture Decision Records
│   ├── ll/                   # Lessons learned from PoC
│   └── planning/             # Roadmap, decision tracker
├── old/                      # PoC reference (do not modify)
└── mkdocs.yml
```

## Reference Material

- `old/` - Proof-of-concept implementation (working but incomplete)
- `docs/ll/` - Lessons learned from PoC, OpenHAB API quirks
- `docs/adr/` - Architecture Decision Records (**authoritative**)
- `docs/planning/` - Roadmap and decision tracker

## Key Patterns

### Smart Home Adapter Protocol
From ADR-005, adapters implement:
```python
class SmartHomeAdapter(Protocol):
    def get_signals(self) -> Dict[str, Signal]: ...
    def get_signal(self, signal_id: str) -> Signal: ...
    def subscribe_events(self) -> Generator[Signal, None, None]: ...
```

### SSE Event Flow
```
OpenHAB → [SSE] → Backend (normalize) → [SSE] → Frontend (render)
```
- Backend handles unit extraction, value formatting, encoding fixes
- Frontend receives ready-to-display values

### OpenHAB Unit Extraction
See `old/backend/home-observer/units_of_measurement.json` for SI/US mapping.
Parse `stateDescription.pattern` like `"%.1f °C"` to extract unit and format value.

The PoC in `old/backend/home-observer` successfully implemented deriving units
and value formatting from OpenHAB metadata, which should be ported to the new backend.

## Common Pitfalls (from PoC)

1. **SSE in React** - Must use `useEffect` with cleanup, not in render
2. **OpenHAB special values** - `"UNDEF"` and `"NULL"` are valid states, don't parse as errors
3. **Error swallowing** - PoC has `except: continue` patterns, need proper logging
4. **Hardcoded URLs** - Use environment config, not literals
5. **Encoding issues** - OpenHAB SSE may have encoding problems (see `ftfy` usage in PoC)

## Implementation Roadmap

### Phase 1: Project Setup (Current)
- [ ] Initialize `packages/backend/` with uv + pyproject.toml
- [ ] Initialize `packages/frontend/` with bun + Vite
- [ ] Set up pytest and basic test structure
- [ ] Set up MkDocs

### Phase 2: Core Backend
- [ ] Signal model (pydantic)
- [ ] SmartHomeAdapter protocol
- [ ] OpenHAB adapter (port from PoC)
- [ ] FastAPI endpoints (REST + SSE)
- [ ] Unit tests for parsing logic

### Phase 3: Frontend Shell
- [ ] React app with Vite + TypeScript
- [ ] SSE client hook with proper cleanup
- [ ] Basic dashboard layout
- [ ] Signal display components

### Phase 4: Integration
- [ ] Robot Framework integration tests
- [ ] Docker configuration
- [ ] MkDocs documentation site

### Phase 5: Deployment (Decisions D8-D10)
- [ ] Raspberry Pi deployment
- [ ] Configuration management
- [ ] Observability/logging

## Git Workflow

Follow **GitHub Flow**:

1. `main` is always deployable
2. Create feature branches from `main` for all changes
3. Branch naming: `feature/<short-description>` or `adr/<number>-<topic>`
4. Open pull request when ready for review
5. Merge to `main` after review/approval

```bash
# Example workflow
git checkout main && git pull
git checkout -b feature/backend-signal-model
# ... make changes ...
git push -u origin feature/backend-signal-model
gh pr create
```

## Development Commands

```bash
# Devcontainer (recommended)
# Open in VS Code, then: Ctrl+Shift+P → "Dev Containers: Reopen in Container"
# Dependencies install automatically via post-create.sh

# Backend
cd packages/backend
uv sync                      # Install dependencies
uv run pytest               # Run unit tests
uv run robot tests/integration  # Run Robot Framework tests
uv run uvicorn lumehaven.main:app --reload  # Start dev server

# Frontend
cd packages/frontend
bun install                 # Install dependencies
bun run dev                 # Start dev server
bun test                    # Run tests

# Documentation
mkdocs serve                # Preview docs locally
mkdocs build                # Build static site
```

## ADR Quick Reference

| ADR | Decision | Key Points |
|-----|----------|------------|
| 001 | State Management | In-memory, abstracted interface, no Redis |
| 002 | Backend Runtime | Python + FastAPI + uv |
| 004 | Frontend Stack | React + Vite + TypeScript + bun |
| 005 | Signal Abstraction | Minimal: `id`, `value`, `unit`, `label` |
| 006 | Testing | pytest (unit) + Robot Framework (integration) |
| 007 | Documentation | MkDocs + Material + mkdocstrings |

## Review Instructions for Pull Requests

- Ensure ADRs are created/updated for architectural decisions
- Ensure ADRs are followed in implementation (or new ones suggested where necessary)
- Check against remaining TODO items (D8-D13) for future compatibility
- **SOLID principles:** Review and comment on adherence. Even when code is good, explain why as a teaching moment.
- Consider yourself a tutor teaching best practices in software architecture.
