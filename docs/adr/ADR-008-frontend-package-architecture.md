# ADR-008: Frontend Package Architecture

## Status

Accepted **Date:** 2026-02-08

## Context

ADR-004 chose React + Vite + TypeScript for the frontend and sketched a single
`packages/frontend/` structure. Before starting implementation, we need to decide how to
**structure the frontend code** to support:

1. **Multiple dashboard modes** — code-driven (JSX) today, with widget-grid and
   WYSIWYG modes planned for the future (see ADR-009)
2. **Mobile dashboards** — the same backend SSE stream serving different device
   form factors via client-side routing
3. **Framework flexibility** — the ability to consume signal data without being
   locked to React (e.g., a vanilla-JS widget engine, or a future React Native app)
4. **Testability** — core signal logic testable without a DOM or React test renderer

The key tension: the SSE transport, signal state management, connection logic, and
command API are **framework-independent concerns**, while rendering signals as React
components is **React-specific**. Bundling both into a single package couples all
consumers to React.

## Decision Drivers

1. **Future dashboard modes** — widget-grid or WYSIWYG engines should consume signals
   without depending on React
2. **Mobile support** — React Native or other mobile renderers need signal access without
   web-specific code
3. **Testability** — core signal logic (SSE client, store, visibility rules) should be
   unit-testable with plain TypeScript, no jsdom needed
4. **Development velocity** — the split must not significantly slow down daily
   development in the monorepo
5. **Clear contracts** — the boundary between "data" and "rendering" should be explicit,
   not just a convention
6. **Ecosystem alignment** — works with bun workspaces, Vite, and GitHub Packages
   publishing (see ADR-009)

## Considered Options

### Option A: Single Package with Internal Modules

```
packages/frontend/
├── src/
│   ├── core/         # Vanilla TS: SSE client, signal store, types
│   ├── react/        # React hooks + components
│   └── app/          # Dashboard application
```

One package, internal directory boundaries. Extract later if needed.

**Strengths:**

- Simplest setup — one `package.json`, one build step
- No workspace linking overhead
- Refactoring across boundaries is easy

**Weaknesses:**

- Boundary is convention-only — nothing stops `app/` from importing `core/` internals
  or `core/` from accidentally importing React
- Widget engines or non-React consumers would need to depend on the entire React package
- "Extract later" historically means "never extract" — the coupling solidifies

### Option B: Two Packages (`@lumehaven/core` + `@lumehaven/react`)

```
packages/
├── core/             # @lumehaven/core — vanilla TypeScript, zero dependencies
│   ├── src/
│   │   ├── client.ts     # SignalClient: SSE connection, reconnection, heartbeat
│   │   ├── store.ts      # SignalStore: in-memory map, subscribe/notify
│   │   ├── commands.ts   # Command API client (POST to backend)
│   │   ├── types.ts      # Signal interface, SignalType enum
│   │   └── visibility.ts # Availability rules, special state detection
│   ├── package.json
│   └── tsconfig.json
├── react/            # @lumehaven/react — thin React bindings
│   ├── src/
│   │   ├── provider.tsx  # SignalProvider (React Context wrapping SignalClient)
│   │   ├── hooks.ts      # useSignal(), useSignals(), useCommand()
│   │   └── Signal.tsx    # <Signal> display component
│   ├── package.json      # peerDependency: react, dependency: @lumehaven/core
│   └── tsconfig.json
└── frontend/         # Reference dashboard application (see ADR-009)
    ├── src/
    │   └── ...
    └── package.json  # depends on @lumehaven/core, @lumehaven/react
```

Two publishable packages plus a dashboard application.

**Strengths:**

- Hard boundary enforced by package resolution — `core/` cannot import React
- Widget engines depend only on `@lumehaven/core` (no React in bundle)
- Each package has focused tests: core is pure TS, react uses React Testing Library
- Works with bun workspaces for local development, GitHub Packages for external
  consumption (ADR-009)
- Mirrors the backend's clean separation (adapter protocol ↔ adapter implementation)

**Weaknesses:**

- Two `package.json` files, two build configs
- Local development requires workspace linking (bun handles this well)
- Cross-package refactoring requires updating both packages

### Option C: Three Packages (core + react + components)

Separate the React hooks (`@lumehaven/react`) from the UI components
(`@lumehaven/components`), giving dashboard authors hooks without opinionated components.

**Strengths:**

- Maximum granularity — use hooks without the `<Signal>` component opinion
- Component library evolves independently from bindings

**Weaknesses:**

- Over-engineered for current needs — the component library is tiny
- Three packages to version and publish
- Hooks and components are tightly coupled in practice

## Decision Matrix

| Criterion              | Weight | A: Single | B: Two Packages | C: Three Packages |
| ---------------------- | ------ | --------- | --------------- | ----------------- |
| Future dashboard modes | 2×     | 2 (4)     | 5 (10)          | 5 (10)            |
| Testability            | 2×     | 3 (6)     | 5 (10)          | 5 (10)            |
| Development velocity   | 2×     | 5 (10)    | 4 (8)           | 3 (6)             |
| Clear contracts        | 1×     | 2         | 5               | 5                 |
| Ecosystem alignment    | 1×     | 4         | 5               | 4                 |
| Maintenance burden     | 1×     | 5         | 4               | 2                 |
| **Weighted Total**     |        | **31**    | **42**          | **37**            |

_Scale: 1 (poor) to 5 (excellent)_

## Decision

**Use Option B: Two packages (`@lumehaven/core` + `@lumehaven/react`).**

The core package is vanilla TypeScript with zero framework dependencies. It owns:

- **`SignalClient`** — SSE connection management, reconnection, heartbeat detection
- **`SignalStore`** — client-side in-memory signal map with subscription/notification
- **`CommandClient`** — HTTP client for sending commands to the backend
- **Signal types** — TypeScript interfaces mirroring the backend Signal model
- **Visibility rules** — `available` flag interpretation, special state detection
- **Value helpers** — locale-aware formatting utilities

The react package is a thin binding layer. It owns:

- **`SignalProvider`** — React Context wrapping `SignalClient`/`SignalStore`
- **`useSignal(id)`** — hook returning a single signal by ID
- **`useSignals()`** — hook returning all signals (the "items" pattern)
- **`useCommand()`** — hook for sending commands with optimistic update support
- **`<Signal>`** — display component (see Component Design below)

### Component Design: `<Signal>`

The `<Signal>` component supports both ID-based lookup (from context) and direct prop
passing:

```tsx
// ID-based: looks up signal from SignalProvider context
<Signal id="oh:DryerOpState" />

// Prop-based: receives signal object directly (for custom logic)
<Signal signal={signals["oh:DryerOpState"]} />
```

**DOM structure** — wrapper element with data attributes, BEM naming:

```html
<span class="signal" data-available="true" data-type="number" data-id="oh:Temperature">
  <span class="signal__value">21.5</span>
  <span class="signal__unit">°C</span>
</span>
```

Design rationale:

- **Wrapper element** — one CSS rule controls visibility of both value and unit:
  `.signal[data-available="false"] { display: none; }`
- **Data attributes** — enable type-based and per-signal CSS styling without JavaScript
  changes: `.signal[data-type="boolean"] .signal__value { text-transform: uppercase; }`
- **BEM naming** — `.signal`, `.signal__value`, `.signal__unit` — robust, predictable,
  easily overridden by dashboard-specific CSS
- **Semantic markup** — `data-id` allows dashboard authors to style individual signals:
  `.signal[data-id="oh:Temperature"] { color: var(--color-temperature); }`

### How Future Dashboard Modes Connect

```
┌──────────────────────────────────────────────────┐
│  @lumehaven/core (vanilla TypeScript, no React)   │
│                                                   │
│  SignalClient ──► SignalStore ──► subscribe()      │
│  CommandClient                                    │
└──────────────┬────────────────────────────────────┘
               │
    ┌──────────┼──────────────┐
    ▼          ▼              ▼
┌─────────┐ ┌──────────┐ ┌──────────────┐
│ @lume/  │ │ Widget   │ │ Future:      │
│ react   │ │ Engine   │ │ Mobile/      │
│ (hooks, │ │ (vanilla │ │ React Native │
│ <Signal>│ │  JS+DOM) │ │              │
│)        │ │          │ │              │
└─────────┘ └──────────┘ └──────────────┘
```

Each renderer depends only on `@lumehaven/core`. The code-driven React dashboard
(current phase) uses `@lumehaven/react`. A future widget engine would import
`SignalStore` directly and manipulate the DOM without React.

## Consequences

### Positive

- Hard package boundary prevents accidental React coupling in core signal logic
- Widget/WYSIWYG engines can be built later without React in the bundle
- Core package is testable with plain TypeScript — fast, no DOM overhead
- Mirrors the backend architecture: protocol (core) vs. implementation (react)
- Monorepo workspace linking gives seamless DX during development

### Negative

- Two packages to maintain, version, and publish (mitigated by bun workspaces + GitHub
  Packages automation)
- Cross-package type changes require building core before react sees updates (mitigated
  by TypeScript project references)
- Slightly more initial setup than a single package

### Risks & Mitigations

| Risk                                   | Mitigation                                           |
| -------------------------------------- | ---------------------------------------------------- |
| Core API changes break react bindings  | Shared TypeScript project references, CI type-checks |
| Over-abstraction in core               | Start minimal; only extract what react actually needs |
| Workspace linking issues               | bun workspaces handle this natively                  |

## Related Decisions

- [ADR-004](ADR-004-frontend-stack.md) — React + Vite + TypeScript (confirmed; this ADR
  refines the package structure)
- [ADR-005](ADR-005-signal-abstraction.md) — Signal model (amended to add
  `display_value`, `available`, `signal_type`; core types mirror this)
- [ADR-009](ADR-009-dashboard-ownership.md) — Dashboard ownership and deployment model

_February 2026_
