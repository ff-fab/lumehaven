# Track Work with Beads

!!! abstract "Goal"
    Use beads (`bd`) and Taskfile commands to find work, track progress, and
    understand project status.

## Overview

lumehaven uses **beads** (`bd`) as its issue tracker — a git-backed graph tracker that
stores issues as JSONL in `.beads/`. Work items have types (epic, task, bug, feature),
priorities, dependencies, and statuses.

Two complementary systems exist:

| System       | Purpose            | Content                 | Location     |
| ------------ | ------------------ | ----------------------- | ------------ |
| **Beads**    | Work tracking      | Actionable tasks, epics | `.beads/`    |
| **TODO docs** | Deferred decisions | Deliberation documents  | `docs/TODO/` |

## Quick Start: Taskfile Commands

The Taskfile provides ergonomic wrappers around common `bd` operations:

```bash
task plan             # Phase progress overview (epic status bars)
task plan:ready       # Show unblocked work ready to start
task plan:phase       # Backlog of highest-priority open phase
task plan:phase -- frontend   # Backlog of a specific phase (by keyword)
task plan:order       # Dependency graph of highest-priority open phase
task plan:order -- deploy     # Dependency graph of a specific phase
```

These commands resolve phases by **title keyword**, **full ID**, or **short ID**
(without the `lh-` prefix):

```bash
task plan:phase -- frontend   # by title keyword
task plan:phase -- lh-809     # by full ID
task plan:phase -- 809        # by short ID
```

!!! note "The `--` separator is required"
    Taskfile uses `--` to separate its own flags from arguments passed to the script.
    Always write `task plan:phase -- <arg>`, not `task plan:phase --<arg>`.

## Find Available Work

```bash
task plan:ready
```

This shows all unblocked tasks (no open dependencies). Pick one and claim it:

```bash
bd update <id> --status in_progress
```

??? tip "Priority levels"
    Issues use numeric priorities: **P0** (critical) → **P3** (low). `bd ready`
    sorts by priority, so the most important unblocked work appears first.

## Understand Project Status

### Phase Overview

```bash
task plan
```

Shows color-coded progress bars for each epic (project phase), e.g.:

```
 ●  lh-19c  Phase 0: Foundation Decisions             ████████████████████  100%  (7/7)
 ●  lh-26x  Phase 1: Backend Core                     ████████████████████  100%  (8/8)
 ○  lh-clk  Phase 2b: Implement Beads                 ████████████████░░░░   80%  (4/5)
 ○  lh-6yy  Phase 3: Frontend Implementation          █░░░░░░░░░░░░░░░░░░░    9%  (1/11)
 ○  lh-809  Phase 4: Integration & Deployment         ░░░░░░░░░░░░░░░░░░░░    0%  (0/6)
```

Color coding (visible in terminal):

- **● green** — phase completed (100%)
- **○ yellow** — phase in progress (>0%)
- **○ dim** — phase not started (0%)

### Phase Backlog

```bash
task plan:phase -- frontend    # All tasks in the "frontend" phase
task plan:phase                # Auto-selects highest-priority open phase
```

### Execution Order (Dependencies)

```bash
task plan:order -- frontend    # Dependency graph for "frontend" phase
task plan:order                # Auto-selects highest-priority open phase
```

This shows an ASCII graph of task dependencies within the phase, helping you understand
what unblocks what.

## Work on a Task

### Claim

```bash
bd update <id> --status in_progress
```

### Complete

```bash
bd close <id>
```

### Create a New Task

```bash
bd create "Fix SSE reconnection" --type bug --priority 1
bd create "Add HomeAssistant adapter" --type feature --priority 2
```

### Add Dependencies

```bash
bd dep add <child-id> <parent-id>    # child is blocked by parent
```

## Direct `bd` Commands

For operations not covered by Taskfile wrappers:

| Command                    | Description                          |
| -------------------------- | ------------------------------------ |
| `bd ready`                 | Unblocked tasks                      |
| `bd list`                  | All open issues                      |
| `bd list --type bug`       | Filter by type                       |
| `bd show <id>`             | Full issue details + dependencies    |
| `bd graph <id> --compact`  | ASCII dependency graph               |
| `bd epic status`           | Progress per epic                    |
| `bd status`                | Overall project health               |
| `bd blocked`               | Show what's blocking what            |
| `bd sync`                  | Export to JSONL for git              |

## Gate Tasks (Beads ↔ TODO Bridge)

Some TODO documents have **phase triggers** — they need to be evaluated before a
particular phase starts. These are tracked as **gate tasks** in beads:

- The gate task is a dependency of the first affected work item
- It references the TODO document (e.g., "Evaluate signal value type (T6)")
- When closing a gate task, the outcome is one of:
    - A new ADR
    - An update marking the TODO resolved
    - New beads tasks from the decision

## Git Integration

Beads data lives in `.beads/issues.jsonl` — a regular git-tracked file. Like any
file, changes only reach remote when **committed and pushed**.

### Before Pushing: Commit Beads State

After closing tasks, export and commit:

```bash
bd close <id>         # Close finished work
bd sync               # Export to JSONL
git add .beads/ && git commit -m "chore: sync beads state"
git push
```

This ensures the PR includes up-to-date issue state when merged to `main`.

!!! warning "The pre-push hook enforces this"
    A pre-push hook runs `bd sync` and **rejects the push** if `.beads/*.jsonl`
    has uncommitted changes. If you see this error, simply commit the beads
    state and push again.

### After Pulling: Automatic Import

A post-merge hook runs `bd sync --import-only` to pick up beads changes from remote.

Both hooks are managed via pre-commit and run automatically.
