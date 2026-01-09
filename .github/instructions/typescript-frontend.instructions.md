---
description: 'TypeScript frontend development - React, Vite, bun'
applyTo: 'packages/frontend/**/*.{ts,tsx,js,jsx}'
---

# TypeScript Frontend Instructions

## Technology Stack

| Component  | Choice     | Notes                    |
| ---------- | ---------- | ------------------------ |
| Framework  | React 18+  | Function components only |
| Build Tool | Vite       | Fast HMR                 |
| Language   | TypeScript | Strict mode enabled      |
| Runtime    | bun        | Replaces node.js         |

## Architecture Role

The frontend is intentionally "dumb":

- Receives **pre-formatted** data from backend
- Just displays `signal.value` and `signal.unit`
- No unit conversion or formatting logic

## SSE Client Pattern

Use `useEffect` with proper cleanup:

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
