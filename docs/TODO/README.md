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
