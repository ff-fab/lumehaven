# GitHub Copilot Instructions

## Project Overview

**lumehaven** - A smart home dashboard supporting OpenHAB (later HomeAssistant), running on Raspberry Pi 4.

**Architecture:** BFF + SPA pattern. React frontend talks only to our backend, never directly to smart home APIs. Backend normalizes data (units, formatting) so the frontend stays "dumb" and lightweight.

## Reference Material

- `old/` - Proof-of-concept implementation (working but incomplete)
- `docs/ll/` - Lessons learned from PoC, OpenHAB API quirks
- `docs/TODO/` - Project approach, decisions needed
- `docs/adr/` - Architecture Decision Records

## Repository Structure (Planned)

```
lumehaven/
├── packages/
│   ├── backend/          # Python BFF (FastAPI)
│   ├── frontend/         # React SPA (TypeScript)
│   └── shared/           # Shared types/schemas
├── docs/
│   ├── adr/              # Architecture Decision Records
│   ├── ll/               # Lessons learned
│   └── TODO/             # Planning documents
└── old/                  # PoC reference (do not modify)
```

## Tooling Preferences

| Tool | Purpose | Notes |
|------|---------|-------|
| Bazel | Build system | Learning goal, orchestrates monorepo |
| bun | JS/TS runtime | Replaces node.js |
| uv | Python package manager | Replaces pip/poetry |
| pydantic v2 | Python validation | PoC used v1 |
| TypeScript | Frontend | PoC used JS, no type safety |

## Key Patterns from PoC

### Smart Home Abstraction
See `old/backend/home-observer/smarthome.py` - Protocol class enables OpenHAB/HomeAssistant swapping:
```python
class SmartHome(Protocol):
    items: Dict[str, SmartHomeItem]
    def get_event_stream(self) -> Generator[SmartHomeItem, None, None]: ...
```

### SSE Event Flow
```
OpenHAB → [SSE] → Backend (normalize) → [SSE] → Frontend (render)
```
- Backend handles unit extraction, value formatting, encoding fixes
- Frontend receives ready-to-display values

### Unit Normalization
See `old/backend/home-observer/units_of_measurement.json` for SI/US mapping.
OpenHAB `stateDescription.pattern` like `"%.1f °C"` must be parsed to extract unit and format value.

## Architecture Decision Records (ADRs)

Document decisions in `docs/adr/ADR-NNN-title.md` using this format:

```markdown
# ADR-<number>: <title>

## Status
Proposed | Accepted | Deprecated | Superseded

## Context
The issue and context for the decision.

## Decision
Use <solution> for <problem> because <rationale>.

## Decision Drivers
- Driver 1...

## Considered Options
- Option 1...

## Decision Matrix
| Criterion | Option 1 | Option 2 |
|-----------|----------|----------|
| Driver 1  | 3        | 5        |

*Scale: 1 (poor) to 5 (excellent)*

## Consequences
### Positive
- ...
### Negative
- ...

*<Date>*
```

## Common Pitfalls (from PoC)

1. **SSE in React** - Must use `useEffect` with cleanup, not in render
2. **OpenHAB special values** - `"UNDEF"` and `"NULL"` are valid states, don't parse
3. **Error swallowing** - PoC has `except: continue` patterns, need proper handling
4. **Hardcoded URLs** - Use environment config, not literals

## Development Commands (TBD)

Commands will be established after Bazel setup. Check `docs/TODO/00-project-approach.md` for current phase.

## Review Instructions for pull-requests

- Ensure ADRs are created/updated for architectural decisions
- Check TODO items and suggest changes to the pull request where future work could be impacted
  and changes should be made to accommodate future work.
- Specifically check against SOLID principles on every pull request and suggest changes where
  necessary. Even where no change is necessary, leave a comment indicating examples on successful
  adherence to SOLID principles, explaining why the code is a good example of SOLID principles.
  Consider yourself a tutor teaching best practices in software architecture.
