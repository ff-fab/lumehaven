# Architecture Decision Records

Architecture Decision Records (ADRs) capture important architectural decisions made
during lumehaven's development. Each ADR documents the context, the decision, the
alternatives considered, and the consequences.

## Index

| ADR                                    | Title                                    | Status   | Date     |
| -------------------------------------- | ---------------------------------------- | -------- | -------- |
| [001](ADR-001-state-management.md)     | State Management Architecture            | Accepted | Dec 2025 |
| [002](ADR-002-backend-runtime.md)      | Backend Language and Runtime             | Accepted | Dec 2025 |
| [004](ADR-004-frontend-stack.md)       | Frontend Stack                           | Accepted (Amended) | Dec 2025 |
| [005](ADR-005-signal-abstraction.md)   | Signal Identity and Metadata Abstraction | Accepted (Amended) | Jan 2026 |
| [006](ADR-006-testing-strategy.md)     | Testing Strategy                         | Accepted | Jan 2026 |
| [007](ADR-007-documentation-system.md) | Documentation System                     | Accepted (Amended) | Feb 2026 |
| [008](ADR-008-frontend-package-architecture.md) | Frontend Package Architecture       | Accepted           | Feb 2026 |
| [009](ADR-009-dashboard-ownership.md)  | Dashboard Ownership and Deployment       | Accepted           | Feb 2026 |
| [010](ADR-010-signal-model-enrichment.md) | Signal Model Enrichment               | Accepted           | Feb 2026 |
| [011](ADR-011-command-architecture.md) | Command Architecture                    | Accepted           | Feb 2026 |

!!! note "Numbering gap" ADR-003 was a draft that was merged into ADR-002 during review.

## What is an ADR?

An Architecture Decision Record is a short document that captures a single significant
decision. Once accepted, an ADR may only be amended while the initial implementation of
its scope is still in progress (e.g., a tooling change discovered during setup). Once
stable, a decision is reversed or replaced via a new ADR that supersedes the original.

**Format:** Each ADR follows a consistent template with Status, Context, Decision,
Decision Drivers, Considered Options, Decision Matrix, and Consequences sections. See
the
[documentation instructions](https://github.com/ff-fab/lumehaven/blob/main/.github/instructions/documentation.instructions.md)
for the full template.
