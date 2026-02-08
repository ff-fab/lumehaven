---
description: 'TypeScript frontend development - React, Vite, bun'
applyTo:
  'packages/frontend/**/*.{ts,tsx,js,jsx}, packages/core/**/*.{ts,tsx,js,jsx},
  packages/react/**/*.{ts,tsx,js,jsx}'
---

# TypeScript Frontend Instructions

## Package Architecture (ADR-008)

| Package              | Purpose                        | Dependencies      |
| -------------------- | ------------------------------ | ----------------- |
| `@lumehaven/core`    | SSE client, Signal types       | None (vanilla TS) |
| `@lumehaven/react`   | React hooks + Signal component | core + React      |
| `packages/frontend/` | Reference dashboard SPA        | react + Vite      |

## Technology Stack

| Component  | Choice     | Notes                                        |
| ---------- | ---------- | -------------------------------------------- |
| Framework  | React 18+  | Function components only                     |
| Build Tool | Vite       | Fast HMR                                     |
| Language   | TypeScript | Strict mode enabled                          |
| Runtime    | bun        | Replaces node.js                             |
| Styling    | CSS + BEM  | `.signal`, `.signal__value`, `.signal__unit` |
| UI State   | Zustand    | Theme, active view                           |

## Architecture Role

The frontend is intentionally "dumb":

- Receives **enriched** data from backend (ADR-010)
- Uses `display_value` for rendering, `value` for logic
- Uses `signal_type` to select component variant
- Uses `available` flag for staleness indicators
- No unit conversion or formatting logic

## Signal Component (ADR-008)

```tsx
// Two usage patterns:
<Signal id="oh:kitchen_temp" />     {/* Fetches from store; id includes adapter prefix */}
<Signal signal={signalObject} />     {/* Direct pass */}

// Renders BEM structure:
// <span class="signal" data-type="number" data-available="true" data-id="oh:kitchen_temp">
//   <span class="signal__value">21.3</span>
//   <span class="signal__unit">°C</span>
// </span>
```

## SSE Client Pattern (in @lumehaven/core)

The SSE client lives in `@lumehaven/core` (no React dependency):

```typescript
useEffect(() => {
  const eventSource = new EventSource('/api/signals/stream');

  eventSource.onmessage = (event) => {
    const signal = JSON.parse(event.data);
    // update state
  };

  return () => eventSource.close(); // Cleanup!
}, []);
```

**Pitfall:** Never create EventSource in render — only in effects with cleanup.

## TypeScript Patterns

### Type Safety

- Avoid `any` type; prefer `unknown` with type guards
- Use TypeScript interfaces for component props
- Use `React.FC<Props>` for typed function components

```typescript
interface SignalCardProps {
  signal: Signal;
  onRefresh?: () => void;
}

const SignalCard: React.FC<SignalCardProps> = ({ signal, onRefresh }) => {
  // ...
};
```

### Hooks Guidelines

- Follow React hooks rules (no conditional hooks)
- Use `useEffect` with cleanup for subscriptions
- Use `useMemo` for expensive computations
- Use `useCallback` for stable function references passed to children

## Component Patterns

### Loading and Error States

- Implement proper loading states for async operations
- Handle error states gracefully with user feedback
- Use Suspense boundaries where appropriate

### Accessibility

- Use semantic HTML elements (`<button>`, `<nav>`, `<main>`)
- Add ARIA attributes when semantic HTML is insufficient
- Ensure keyboard navigation works

## Code Style

- Function components only (no class components)
- Use TypeScript strict mode
- Prefer named exports over default exports
- Keep components small and focused
