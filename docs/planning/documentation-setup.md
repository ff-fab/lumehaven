# Documentation Planning

> Planning document for the lumehaven documentation site. Records decisions from the
> interactive planning session (Feb 2026).

## Decisions

| #   | Decision                 | Choice                                                             | Rationale                                                               |
| --- | ------------------------ | ------------------------------------------------------------------ | ----------------------------------------------------------------------- |
| D1  | Primary audience         | Dual (users + developers)                                          | Home Assistant model, but single site — two-site overkill for our scale |
| D2  | Documentation structure  | Diátaxis (4 quadrants)                                             | Used by Django, NumPy, Textual — maps naturally to dual-audience        |
| D3  | API documentation        | mkdocstrings + Swagger/ReDoc links                                 | FastAPI pattern — static Python internals + interactive REST API        |
| D4  | Contributing guide       | Root `CONTRIBUTE.md` overview + detailed guide in doc site         | Pydantic/FastAPI pattern                                                |
| D5  | How-to guides (now)      | Add adapter, Local dev setup, Configuration                        | Critical developer & user paths                                         |
| D6  | How-to guides (deferred) | Deployment, Frontend widgets, Dashboard generation                 | Depend on phases 3+                                                     |
| D7  | Landing page             | Project overview + quick links grid                                | Scannable, works for both audiences                                     |
| D8  | Blog                     | Nav slot planned, content deferred                                 | Avoid empty sections                                                    |
| D9  | Published scope          | ADRs public; LL temporary (remove after Phase 3); planning private | Standard open-source practice                                           |
| D10 | Versioning               | None (pre-v1)                                                      | Add when v1.0 ships                                                     |
| D11 | Deployment               | GitHub Pages from Phase 1                                          | Early visibility, iterate publicly                                      |

## Navigation Structure (Diátaxis)

```
Home (index.md) — project overview + quick-links grid

├── Tutorials (learning-oriented)
│   ├── Getting Started — install → configure → first signals
│   └── Development Setup — dev container, tools, PR workflow
│
├── How-To Guides (task-oriented)
│   ├── Configure lumehaven — YAML, env vars, adapters
│   ├── Add a New Adapter — Protocol, factory, tests
│   ├── Run Tests & Check Coverage — pytest, Robot, thresholds
│   └── [deferred: Deploy, Frontend Widget, Dashboard Generation]
│
├── Reference (information-oriented)
│   ├── Python API — auto-generated via mkdocstrings
│   │   ├── Core (Signal, exceptions)
│   │   ├── Adapters (Protocol, Manager, OpenHAB)
│   │   ├── API Routes (REST endpoints, SSE)
│   │   ├── State (SignalStore)
│   │   └── Config
│   ├── REST API → links to Swagger UI + ReDoc
│   ├── Configuration Reference
│   └── Architecture Decision Records (ADR index + all ADRs)
│
├── Explanation (understanding-oriented)
│   ├── Architecture: The BFF Pattern
│   ├── Signal Abstraction
│   ├── Adapter System
│   └── Testing Strategy (existing 6-chapter docs)
│
└── Contributing
    ├── Contribution Guide (workflow, PR process, conventions)
    └── Coding Standards (Python, TypeScript deferred)
```

## Published vs. Private Content

| Content                            | Published    | Notes                                 |
| ---------------------------------- | ------------ | ------------------------------------- |
| ADRs (`docs/adr/`)                 | ✅ Yes       | Standard open-source practice         |
| Testing strategy (`docs/testing/`) | ✅ Yes       | Part of Explanation quadrant          |
| Planning docs (`docs/planning/`)   | ❌ No        | Internal, excluded via `exclude_docs` |
| TODO items (`docs/TODO/`)          | ❌ No        | Internal, excluded via `exclude_docs` |

## Implementation Phases

### Phase 1: Foundation

- [x] Add MkDocs-Material + mkdocstrings dependencies to `pyproject.toml`
- [x] Create `mkdocs.yml` with Diátaxis nav structure
- [x] Create `docs/index.md` landing page
- [x] Create ADR index page
- [x] Add Taskfile tasks: `docs:serve`, `docs:build`
- [x] Create GitHub Pages deployment workflow
- [x] Update `.github/instructions/documentation.instructions.md`
- [x] Create all section index pages and stub content
- [x] Configure mkdocstrings for Python API reference
- [x] Verify `task docs:serve` renders correctly
- [x] Verify mkdocstrings generates API docs from existing docstrings

### Phase 2: Content (next)

- [ ] Complete "Getting Started" tutorial with real walkthrough
- [ ] Complete "Add a New Adapter" how-to with full code examples
- [ ] Complete "Configuration" how-to with all YAML options
- [ ] Expand architecture explanation with detailed diagrams
- [ ] Expand signal abstraction explanation with normalization details
- [ ] Fill in Configuration Reference from config model
- [ ] Slim down root `CONTRIBUTE.md` → link to doc site detail
- [ ] Cross-link between sections (tutorials ↔ how-tos ↔ reference)

### Phase 3: Polish (later)

- [ ] Activate blog section when first release note is ready
- [ ] Add `llms.txt` (Pydantic does this for AI-friendly docs)
- [ ] Frontend coding standards (when Phase 3 starts)
- [ ] Deployment how-to guide

### Phase 4: Versioning (v1.0)

- [ ] Add mike for documentation versioning
- [ ] Set up version selector in nav

## Tooling Summary

| Tool                | Purpose                         | Command                               |
| ------------------- | ------------------------------- | ------------------------------------- |
| MkDocs              | Static site generator           | `task docs:serve` / `task docs:build` |
| Material for MkDocs | Theme                           | Config in `mkdocs.yml`                |
| mkdocstrings        | Python API docs from docstrings | Plugin in `mkdocs.yml`                |
| GitHub Pages        | Hosting                         | `.github/workflows/docs.yml`          |
| Taskfile            | Local commands                  | `task docs:serve` / `task docs:build` |
