# Agent Instructions

This project uses **bd** (beads) for issue tracking. Run `bd onboard` to get started.

## Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --status in_progress  # Claim work
bd close <id>         # Complete work
bd sync               # Sync with git
```

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete
until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**

- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds

## Beads vs TODO: Two Systems, Distinct Purposes

| System           | Purpose            | Content type            | Location     |
| ---------------- | ------------------ | ----------------------- | ------------ |
| **Beads (`bd`)** | Work tracking      | Actionable tasks, epics | `.beads/`    |
| **TODO folder**  | Deferred decisions | Rich deliberation docs  | `docs/TODO/` |

**Beads** tracks _work_: things to build, fix, or ship.

**TODO items** (T1–Tn) are _deliberation documents_ — deferred decisions, architectural
evaluations, and technical debt. They are mini-ADRs-in-waiting.

### Gate Tasks

Phase-triggered TODOs get a **gate task** in beads as a dependency of the relevant work
item. The gate task references the TODO doc but contains no decision logic itself.

- Date-triggered TODOs stay markdown-only
- When closing a gate task: create an ADR, update the TODO, or create new tasks
