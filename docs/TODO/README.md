# Technical Debt & Deferred Items

This folder tracks items that don't fit the current development phase but should be
reconsidered later:

- **Technical debt** — shortcuts taken that need future attention
- **Deferred decisions** — items marked "to be reconsidered later"
- **Out-of-scope enhancements** — good ideas that don't fit current priorities

These items don't directly advance the planned development phases but shouldn't be
forgotten.

## Current Items

### T1: StateStore Abstraction Evaluation

- **Source:** ADR-001 (State Management)
- **Note:** "If abstraction proves unnecessary after 6 months, remove it"
- **Review date:** June 2026

### T2: Mock Fixture Freshness

- **Source:** ADR-006 (Testing Strategy)
- **Note:** Test fixtures from real API responses should be updated periodically
- **Action:** Compare fixtures against live OpenHAB API responses quarterly

### T3: TypeScript API Documentation

- **Source:** ADR-007 (Documentation System)
- **Note:** TypeDoc deferred; add when frontend API surface stabilizes
- **Trigger:** After Phase 3 frontend implementation

### T4: State Persistence Option

- **Source:** ADR-001 (State Management)
- **Note:** State lost on restart is acceptable now; could add persistence later
- **Options:** Redis migration via StateStore abstraction, or simple file-based cache

### T5: Re-evaluate Zensical as MkDocs Replacement

- **Source:** ADR-007 (Documentation System)
- **Note:** Zensical (v0.0.10–v0.0.21) has a critical asset pipeline bug — theme CSS/JS
  never copied to build output. All versions tested produce unstyled pages. Reverted to
  MkDocs-Material in February 2026. Re-evaluate when Zensical reaches a stable release
  with working asset generation.
- **Trigger:** Zensical v0.1.0+ or confirmed fix for asset pipeline
- **Review date:** August 2026

### T6: Signal Value Type — String-Only vs. Rich Types

- **Source:** ADR-005 (Signal Abstraction)
- **Context:** Currently `Signal.value` is always `str` and the frontend renders it
  as-is ("keep the frontend dumb"). In practice, the frontend will need to interpret
  values — e.g., hiding `NULL`/`UNDEF` signals, treating `ON`/`OFF` as boolean for
  toggle switches, numeric comparisons for thresholds or charts. Keeping everything as
  opaque strings pushes type interpretation into the frontend anyway, undermining the
  "dumb frontend" goal.
- **Options:**
    - Widen `value` to `str | int | float | bool | None` and let pydantic coerce on
      construction — frontend gets native types, no string parsing needed
    - Add a `value_type` discriminator field (`"string"`, `"number"`, `"bool"`,
      `"null"`) alongside the string value — frontend switches on it
    - Keep `str` but add a `raw_value` field with the original typed value
- **Trade-offs:** Changing `value` type touches Signal, all adapters, the store, API
  response models, and frontend contracts. The wider the type, the more the frontend
  must handle — but it already must. Better to formalize the contract than have implicit
  string parsing on the frontend side.
- **Trigger:** Frontend development (Phase 3) — revisit when building dashboard
  components that need conditional rendering or value interpretation
- **ADR impact:** Would amend ADR-005; consider a new ADR if the change is significant

### T7: ~~Beads Git Hooks (post-merge, pre-push)~~ — RESOLVED

- **Source:** Phase 2b (Beads introduction)
- **Resolution:** Option B selected — integrated beads sync as local hooks in
  `.pre-commit-config.yaml`. Pre-commit manages all git hooks (Single Responsibility).
  Hooks installed for `pre-push` (auto-syncs uncommitted JSONL) and `post-merge`
  (imports upstream JSONL changes after pull).
- **Resolved:** February 2026
