---
description: 'Documentation - Markdown and MkDocs conventions'
applyTo: '**/*.md'
---

# Documentation Instructions

## Documentation System (ADR-007)

| Component       | Choice                                                  |
| --------------- | ------------------------------------------------------- |
| Site Generator  | MkDocs + Material for MkDocs (`mkdocs.yml`)             |
| Theme           | Material for MkDocs                                     |
| Python API Docs | mkdocstrings                                            |
| Structure       | Diátaxis (Tutorials / How-To / Reference / Explanation) |
| CLI             | `task docs:serve`, `task docs:build`                    |

## ADR Format

Architecture Decision Records follow this structure:

Document decisions in `docs/adr/ADR-NNN-title.md` using this format:

```markdown
# ADR-<number>: <title>

## Status

Proposed | Accepted | Deprecated | Superseded **Date:** YYYY-MM-DD

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
| --------- | -------- | -------- |
| Driver 1  | 3        | 5        |

_Scale: 1 (poor) to 5 (excellent)_

## Consequences

### Positive

- ...

### Negative

- ...

_<Date>_
```

## File Locations

| Content            | Location         |
| ------------------ | ---------------- |
| ADRs               | `docs/adr/`      |
| Planning/Decisions | `docs/planning/` |
| Pending Decisions  | `docs/TODO/`     |
| Agent Demo Proofs  | `docs/demos/`    |
| Work Tracking      | `.beads/`        |
