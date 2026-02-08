# ADR-009: Dashboard Ownership and Deployment Model

## Status

Accepted **Date:** 2026-02-08

## Context

lumehaven must serve two audiences simultaneously:

1. **The author's personal dashboard** — a private deployment with family-specific
   presence tracking, hardcoded device URLs (cameras, Grafana), German locale,
   and personal smart home item bindings. This content cannot be committed to a
   public repository.

2. **A reusable framework** — generic smart home dashboard infrastructure that others
   can adopt, extend, and deploy with their own configurations.

The PoC (`old/frontend/home-front/`) demonstrated this tension: a 432-line `Start.js`
panel with personal camera IPs, family member names, and hardcoded German text,
alongside reusable patterns like the `<Item>` component and SSE data flow.

Additionally, the architecture must support **different dashboard experiences per
device** (wall-mounted tablet vs. phone), served from the same backend. And it must
plan for **future dashboard modes** beyond code-driven JSX — widget-grid editors,
template-driven dashboards — without requiring the deployment model to change.

## Decision Drivers

1. **Privacy** — personal dashboard content must not enter the public repository
2. **Development velocity** — daily feature development should happen in a single IDE
   workspace (the monorepo), not require cross-repo coordination
3. **Parallel development** — improving the framework and building the personal
   dashboard should be independent workflows
4. **Deployment simplicity** — the personal dashboard must produce a Docker image for
   Raspberry Pi deployment without complex build pipelines
5. **Reusability** — the framework should be consumable as versioned packages, not
   copy-pasted code
6. **Device flexibility** — tablet and phone dashboards should be different layouts,
   served from the same app, using client-side routing

## Considered Options

### Option A: Library / Toolkit

lumehaven ships as npm packages only. No reference dashboard in the monorepo. Every
user (including the author) builds their own app from scratch, importing the packages.

**Strengths:**

- Clean separation — the monorepo is purely library code
- Forces good API design (dogfooding from an external perspective)

**Weaknesses:**

- No integration test target in the monorepo
- No reference implementation for documentation
- Daily development requires working across two repos
- Feature development is painful: change core → publish → update dashboard → test

### Option B: Monorepo with .gitignored Private Folder

Add `packages/dashboard-private/` to lumehaven, exclude it via `.gitignore`. Framework
is public, personal content is local-only.

**Strengths:**

- Everything in one IDE workspace
- No publishing overhead during development

**Weaknesses:**

- Private content is unversioned — no backup, no history
- `.gitignore` is fragile — one mistake exposes personal data
- No clean deployment story (how does the private folder become a Docker image?)
- Confusing repo structure (phantom package that doesn't exist in CI)

### Option C: App with Injection — Separate Dashboard Repos

lumehaven monorepo contains the framework packages AND a reference dashboard.
Personal dashboards live in separate git repositories that import the framework
packages as versioned dependencies.

```
lumehaven monorepo (public)          my-dashboard repo (private)
├── packages/                       ├── package.json
│   ├── core/    → @lumehaven/core  │   └── deps: @lumehaven/core,
│   ├── react/   → @lumehaven/react │           @lumehaven/react
│   └── frontend/ → reference dash  ├── src/
│       └── full working example    │   ├── panels/
│                                   │   │   ├── Home.tsx (personal)
│                                   │   │   └── Climate.tsx (personal)
│                                   │   └── App.tsx
│                                   ├── vite.config.ts
│                                   └── Dockerfile
```

**Strengths:**

- Daily development happens in the monorepo against the reference dashboard
- Reference dashboard serves as documentation, template, and integration test fixture
- Personal dashboard is properly versioned in its own private repo with full git history
- Clean deployment: personal repo owns its Dockerfile and `docker-compose.yaml`
- Framework packages published to GitHub Packages with semantic versioning
- Personal dashboard depends on stable, versioned packages — no surprise breakage

**Weaknesses:**

- Requires publishing packages (mitigated: GitHub Packages + CI automation)
- Cross-repo development requires `bun link` or local path overrides during
  active framework changes (standard monorepo pattern)
- Two repos to maintain

### Option D: Runtime Plugin System

lumehaven ships as a complete app. Personal dashboards are loaded as plugins from a
configurable directory at runtime (dynamic import or module federation).

**Strengths:**

- Single Docker image for all deployments
- Plugin directory is volume-mounted — easy deployment update

**Weaknesses:**

- Dynamic import adds complexity (bundler configuration, typing, error handling)
- Module federation is fragile and version-sensitive
- Plugin API surface must be stable and documented
- Overkill for the current code-driven dashboard approach

## Decision Matrix

| Criterion              | Weight | A: Library | B: Gitignored | C: Injection | D: Plugins |
| ---------------------- | ------ | ---------- | ------------- | ------------ | ---------- |
| Privacy                | 2×     | 5 (10)     | 3 (6)         | 5 (10)       | 4 (8)      |
| Development velocity   | 2×     | 2 (4)      | 5 (10)        | 4 (8)        | 3 (6)      |
| Parallel development   | 2×     | 3 (6)      | 4 (8)         | 5 (10)       | 4 (8)      |
| Deployment simplicity  | 1×     | 4          | 2             | 5            | 3          |
| Reusability            | 1×     | 5          | 2             | 5            | 4          |
| Device flexibility     | 1×     | 4          | 4             | 4            | 4          |
| **Weighted Total**     |        | **33**     | **32**        | **42**       | **33**     |

_Scale: 1 (poor) to 5 (excellent)_

## Decision

**Use Option C: App with Injection — separate dashboard repos that import lumehaven
packages as versioned dependencies.**

### Three-Layer Architecture

The frontend follows a three-layer model:

| Layer                  | What                                              | Lives where          |
| ---------------------- | ------------------------------------------------- | -------------------- |
| **Framework**          | SSE client, signal store, React hooks, `<Signal>` | lumehaven monorepo   |
| **Engine**             | How dashboards load, route, compose                | lumehaven monorepo   |
| **Dashboard content**  | Panels, layouts, personal signal bindings          | Separate repo        |

### Reference Dashboard

The lumehaven monorepo includes a **full reference dashboard** in `packages/frontend/`
that:

- Demonstrates all framework features (SSE connection, signal display, commands,
  routing, responsive layout)
- Serves as the integration test target for the framework packages
- Acts as documentation-by-example for dashboard authors
- Uses synthetic/anonymized signal data (no personal information)
- Is the primary workspace for daily framework development

The reference dashboard is a **functional application**, not a minimal stub. Feature
development happens here first, then the personal dashboard consumes the improved
packages.

### Personal Dashboard Repo

The author's private dashboard is a separate git repository that:

- Depends on `@lumehaven/core` and `@lumehaven/react` from GitHub Packages
- Owns its own `vite.config.ts`, build pipeline, and `Dockerfile`
- Contains all private content (device URLs, family names, personal layouts)
- Produces the Docker image deployed to the Raspberry Pi
- Uses the reference dashboard as a starting template

### Package Publishing via GitHub Packages

Framework packages are published to GitHub Packages (npm registry scoped to `@lumehaven`
or the GitHub org):

- **Triggering:** CI publishes on tagged releases (semantic versioning)
- **Consumption:** Personal dashboard's `package.json` references the GitHub Packages
  registry
- **Local development:** During active framework changes, use `bun link` or workspace
  protocol to point at local packages

### Device-Specific Dashboards

Different device form factors (tablet, phone) are handled via **client-side routing**
within a single application:

```
/              → Tablet dashboard (default, wall-mounted display)
/mobile        → Phone dashboard (compact layout)
/kiosk         → Kiosk mode (no navigation, auto-rotate panels)
```

One build, one Docker image, one deployment. The device either navigates to its route
directly, or the app detects viewport/user-agent and redirects. Dashboard content
authors define layouts per route.

## Development Workflow

### Daily framework development (monorepo)

```bash
# Work entirely in lumehaven monorepo
cd packages/frontend
bun dev                     # Vite dev server with reference dashboard
# Edit core/, react/, frontend/ — changes reflect instantly via workspace linking
```

### Consuming in personal dashboard

```bash
# In personal dashboard repo
bun add @lumehaven/core@latest @lumehaven/react@latest
# Or during active framework changes:
bun link @lumehaven/core @lumehaven/react
```

### Deployment

```bash
# In personal dashboard repo
docker build -t my-dashboard .
# docker-compose.yaml references my-dashboard, not lumehaven-frontend
```

## Consequences

### Positive

- Personal content is fully private with proper git history in its own repo
- Daily development stays in one IDE workspace (monorepo + reference dashboard)
- Framework packages have stable, versioned contracts via GitHub Packages
- Reference dashboard serves triple duty: dev workspace, docs, test fixture
- Clean deployment: personal repo owns the Docker image
- Other users can create their own dashboard repos following the same pattern

### Negative

- Publishing overhead for package releases (mitigated: CI automation)
- Two repos to maintain for the author (mitigated: personal dashboard is "just panels")
- `bun link` workflow needed during cross-repo development (standard pattern)

### Risks & Mitigations

| Risk                                         | Mitigation                                   |
| -------------------------------------------- | -------------------------------------------- |
| Publishing friction slows iteration          | CI auto-publishes on semver tags             |
| Reference dashboard diverges from framework  | CI builds reference dashboard as test gate   |
| Personal dashboard falls behind on versions  | Dependabot / renovate for auto-updates       |

## Related Decisions

- [ADR-004](ADR-004-frontend-stack.md) — React + Vite + TypeScript (the reference
  dashboard and personal dashboards both use this stack)
- [ADR-008](ADR-008-frontend-package-architecture.md) — Two-package split
  (`@lumehaven/core` + `@lumehaven/react`) that enables this model
- [ADR-001](ADR-001-state-management.md) — Backend state management (unchanged; the
  frontend consumes signals from the same SSE/REST API)

_February 2026_
