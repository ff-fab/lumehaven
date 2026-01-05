# ADR-007: Documentation System

## Status

Accepted

## Context

Lumehaven needs a documentation system that:
1. Hosts technical documentation (architecture, API, setup guides)
2. Integrates with existing ADRs in `docs/adr/`
3. Generates API documentation from code (Python docstrings, TypeScript types)
4. Remains maintainable for a solo developer / small team
5. Optionally supports requirements traceability for learning purposes

Current documentation:
- ADRs in `docs/adr/` (Markdown)
- Lessons learned in `docs/ll/` (Markdown)
- Planning docs in `docs/TODO/` (Markdown)

The project is a learning exercise, so the documentation system should balance sophistication with practicality.

## Considered Options

### Option 1: Sphinx + MyST + sphinx-autodoc
Python's mature documentation ecosystem with Markdown support.

**Stack:**
- Sphinx for site generation
- MyST-Parser for Markdown support (instead of reStructuredText)
- sphinx-autodoc for Python API docs
- TypeDoc integration for TypeScript (separate or embedded)

**Pros:**
- Mature, battle-tested
- Excellent Python integration (autodoc)
- MyST allows Markdown while keeping Sphinx power
- Cross-references, search, versioning
- Large ecosystem of extensions

**Cons:**
- Learning curve for Sphinx configuration
- TypeScript integration is awkward (needs separate tooling)
- Can feel heavyweight for smaller projects

### Option 2: MkDocs + mkdocstrings
Simpler Python documentation with native Markdown.

**Stack:**
- MkDocs for site generation
- Material for MkDocs theme
- mkdocstrings for Python API docs
- TypeDoc for TypeScript (separate)

**Pros:**
- Simple, Markdown-native
- Beautiful Material theme out of the box
- mkdocstrings handles Python docstrings well
- Fast and easy to configure
- Good search built-in

**Cons:**
- Less powerful than Sphinx for complex docs
- No requirements traceability extensions
- Cross-referencing less sophisticated

### Option 3: Sphinx + sphinx-needs (Full Traceability)
Sphinx with formal requirements management.

**Stack:**
- Sphinx + MyST
- sphinx-needs for requirements/specs
- sphinx-autodoc for Python
- Traceability matrices

**Pros:**
- Formal requirements traceability
- Links requirements → implementation → tests
- Professional documentation practice
- Learning opportunity for requirements engineering

**Cons:**
- Significant overhead for a personal project
- sphinx-needs has steep learning curve
- Over-engineering risk
- Maintenance burden

### Option 4: Docusaurus
React-based documentation site.

**Stack:**
- Docusaurus for site generation
- MDX for enhanced Markdown
- TypeDoc plugin for TypeScript

**Pros:**
- Modern, React-based
- Great TypeScript integration
- Beautiful default theme
- Versioning built-in

**Cons:**
- JavaScript/React ecosystem (not Python-native)
- Python API docs need separate solution
- Overkill for this project size
- Diverges from Python-centric stack

### Option 5: Minimal (Markdown + GitHub)
Keep documentation as Markdown, rely on GitHub rendering.

**Stack:**
- Markdown files in `docs/`
- GitHub's built-in rendering
- Optional: GitHub Pages for hosting

**Pros:**
- Zero additional tooling
- Works immediately
- No build step
- Lowest maintenance

**Cons:**
- No API doc generation
- No search
- Limited cross-referencing
- No unified site

## Decision

Use **Option 2: MkDocs + mkdocstrings** with the Material theme.

This provides the right balance of:
- Simplicity for a personal project
- Native Markdown support (matches existing docs)
- Good Python API documentation
- Beautiful, functional output
- Easy to set up and maintain

### Documentation Structure

```
docs/
├── index.md                    # Home page
├── getting-started/
│   ├── installation.md
│   ├── configuration.md
│   └── quickstart.md
├── architecture/
│   ├── overview.md
│   ├── signal-abstraction.md   # Links to/from ADR-005
│   └── adapters.md
├── adr/                        # Existing ADRs (included as-is)
│   ├── index.md                # ADR index/summary
│   ├── ADR-001-state-management.md
│   ├── ...
│   └── template.md
├── api/
│   ├── backend/                # Auto-generated from Python
│   │   ├── signal.md
│   │   └── adapters/
│   └── frontend/               # TypeDoc output (if needed)
├── development/
│   ├── testing.md              # Links to ADR-006
│   ├── contributing.md
│   └── coding-standards.md
├── ll/                         # Existing lessons learned
│   └── ...
└── TODO/                       # Existing planning docs
    └── ...
```

### MkDocs Configuration

```yaml
# mkdocs.yml
site_name: Lumehaven
site_description: Smart Home Dashboard
repo_url: https://github.com/ff-fab/lumehaven

theme:
  name: material
  palette:
    scheme: slate
    primary: teal
  features:
    - navigation.tabs
    - navigation.sections
    - navigation.expand
    - search.suggest
    - content.code.copy

plugins:
  - search
  - mkdocstrings:
      handlers:
        python:
          paths: [packages/backend/src]
          options:
            show_source: true
            show_root_heading: true
            members_order: source

markdown_extensions:
  - admonition
  - pymdownx.details
  - pymdownx.superfences
  - pymdownx.tabbed:
      alternate_style: true
  - pymdownx.highlight:
      anchor_linenums: true
  - toc:
      permalink: true

nav:
  - Home: index.md
  - Getting Started:
    - Installation: getting-started/installation.md
    - Configuration: getting-started/configuration.md
    - Quick Start: getting-started/quickstart.md
  - Architecture:
    - Overview: architecture/overview.md
    - Signal Abstraction: architecture/signal-abstraction.md
    - Adapters: architecture/adapters.md
  - API Reference:
    - Backend: api/backend/
  - Development:
    - Testing: development/testing.md
    - Contributing: development/contributing.md
  - ADRs: adr/
  - Lessons Learned: ll/
```

### API Documentation Approach

**Python (mkdocstrings):**
```markdown
<!-- docs/api/backend/signal.md -->
# Signal Model

::: lumehaven.models.Signal
    options:
      show_root_heading: true
      members_order: source
```

**TypeScript (optional, deferred):**
- Use TypeDoc to generate Markdown
- Include in MkDocs site or link externally
- Only add when frontend API surface stabilizes

### ADR Integration

ADRs remain as Markdown in `docs/adr/` and are automatically included. Add an index page:

```markdown
<!-- docs/adr/index.md -->
# Architecture Decision Records

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [001](ADR-001-state-management.md) | State Management | Accepted | 2025-12-xx |
| [002](ADR-002-backend-runtime.md) | Backend Runtime | Accepted | 2025-12-xx |
| ... | ... | ... | ... |

## What is an ADR?

An Architecture Decision Record captures an important architectural decision...
```

### Deferred: Requirements Traceability

If formal requirements traceability becomes valuable later:
1. Migrate to Sphinx + sphinx-needs
2. Or add a lightweight traceability table in Markdown

For now, the linkage between ADRs → implementation → tests is informal but documented in ADRs themselves.

## Decision Drivers

1. **Markdown-native:** Matches existing documentation format
2. **Simplicity:** MkDocs is easy to configure and maintain
3. **Python integration:** mkdocstrings handles Python well
4. **Visual quality:** Material theme looks professional
5. **Low overhead:** Minimal configuration, fast builds
6. **Extensibility:** Can add features incrementally

## Decision Matrix

| Criterion | Option 1 (Sphinx) | Option 2 (MkDocs) | Option 3 (sphinx-needs) | Option 4 (Docusaurus) | Option 5 (Minimal) |
|-----------|-------------------|-------------------|-------------------------|----------------------|-------------------|
| Simplicity | 3 | 5 | 2 | 3 | 5 |
| Markdown support | 4 | 5 | 4 | 5 | 5 |
| Python API docs | 5 | 4 | 5 | 2 | 1 |
| TypeScript docs | 2 | 2 | 2 | 5 | 1 |
| Visual quality | 4 | 5 | 4 | 5 | 2 |
| Maintenance | 3 | 5 | 2 | 3 | 5 |
| Extensibility | 5 | 4 | 5 | 4 | 2 |
| **Total** | **26** | **30** | **24** | **27** | **21** |

*Scale: 1 (poor) to 5 (excellent)*

## Implementation Plan

### Phase 1: Basic Setup
- [ ] Install MkDocs + Material + mkdocstrings
- [ ] Create `mkdocs.yml` configuration
- [ ] Add `docs/index.md` home page
- [ ] Create ADR index page
- [ ] Verify existing docs render correctly

### Phase 2: Structure
- [ ] Create navigation structure
- [ ] Add getting-started guides
- [ ] Create architecture overview
- [ ] Link ADRs to architecture docs

### Phase 3: API Documentation
- [ ] Configure mkdocstrings for Python
- [ ] Document Signal model
- [ ] Document adapter interfaces
- [ ] Add code examples

### Phase 4: Deployment (Optional)
- [ ] GitHub Pages via GitHub Actions
- [ ] Or local-only with `mkdocs serve`

## Tooling Configuration

### Dependencies (pyproject.toml)
```toml
[project.optional-dependencies]
docs = [
    "mkdocs>=1.5",
    "mkdocs-material>=9.0",
    "mkdocstrings[python]>=0.24",
]
```

### GitHub Actions (optional)
```yaml
# .github/workflows/docs.yml
name: Deploy Docs
on:
  push:
    branches: [main]
    paths: ['docs/**', 'mkdocs.yml']

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install mkdocs-material mkdocstrings[python]
      - run: mkdocs gh-deploy --force
```

## Consequences

### Positive
- Simple, Markdown-native workflow
- Beautiful documentation with minimal effort
- Good Python API documentation
- Easy to maintain for solo developer
- Fast iteration with `mkdocs serve`

### Negative
- TypeScript API docs need separate handling
- No built-in requirements traceability
- Less powerful than Sphinx for complex cross-referencing

### Risks & Mitigations
| Risk | Mitigation |
|------|------------|
| Need more power later | Sphinx migration is straightforward from Markdown |
| TypeScript docs needed | Use TypeDoc separately, link from MkDocs |
| Requirements traceability | Add lightweight table in Markdown if needed |

## References

- MkDocs: https://www.mkdocs.org/
- Material for MkDocs: https://squidfunk.github.io/mkdocs-material/
- mkdocstrings: https://mkdocstrings.github.io/
- TypeDoc: https://typedoc.org/
- Sphinx: https://www.sphinx-doc.org/ (alternative)
- sphinx-needs: https://sphinx-needs.readthedocs.io/ (deferred option)

*January 5, 2026*
