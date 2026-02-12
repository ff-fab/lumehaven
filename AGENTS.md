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

## Workflow

All workflow details — Git flow, beads conventions, quality gates, session completion,
showboat demos, and coverage thresholds — are defined in
`.github/instructions/workflow.instructions.md` (the single source of truth).

GitHub Copilot loads this file automatically. Other agents should read it at session
start.

### Critical Rules (Always Apply)

- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing — that leaves work stranded locally
- NEVER say "ready to push when you are" — YOU must push
- Beads state MUST be committed before pushing — the pre-push hook will reject pushes
  with uncommitted `.beads/` changes
- Run `task pre-pr` before creating a PR (quality gates)
