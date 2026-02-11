# Devcontainer Settings, Showboat & E2E Evaluation

*2026-02-11T19:51:39Z*

Added showboat to devcontainer toolchain and agent workflow instructions (AGENTS.md, copilot-instructions). Created T8 E2E tool evaluation (TODO) with beads gate task blocking Phase 4 E2E work. Updated pydantic constraints and regenerated lockfile.

```bash
showboat --version
```

```output
0.4.0
```

```bash
grep -c 'showboat' AGENTS.md
```

```output
17
```

```bash
bd show lh-36f --short
```

```output
○ lh-36f ● P2 Gate: Evaluate E2E testing tool (T8, docs/TODO/)
```

```bash
head -1 docs/TODO/e2e-testing-tool-evaluation.md
```

```output
# T8: E2E Testing Tool Evaluation
```
