# ADR-004: Frontend Stack

## Status

Accepted

## Context

The frontend serves as the dashboard UI, running in browsers on wall-mounted tablets or similar displays. It must:

1. Receive real-time updates via SSE from the backend
2. Render widgets displaying smart home state (temperature, lights, weather, etc.)
3. Send commands to the smart home via the backend (buttons, sliders, text inputs)
4. Run efficiently on potentially low-powered display devices
5. Be maintainable with type safety

The dashboard is primarily for visualization, but requires interactive controls:
- **Buttons** - Toggle lights, trigger scenes, arm/disarm security
- **Sliders** - Adjust dimmer levels, thermostat setpoints, volume
- **Text fields** - Set custom values, search, or input names

The target is a "dumb client"—the backend handles all data normalization and command routing, so the frontend focuses on rendering and capturing user input.

## Decision Drivers

1. **Development velocity** - Time to working implementation
2. **Resource efficiency** - Bundle size, runtime performance on display devices
3. **Type safety** - Catch errors at compile time
4. **Ecosystem maturity** - Component libraries, tooling, documentation
5. **SSE support** - Clean integration with Server-Sent Events
6. **Maintainability** - Code clarity, debugging, long-term support
7. **Tooling alignment** - Integration with bun, potential Bazel build later

## Considered Options

### Option A: React + Vite + TypeScript

```
Framework: React 18+
Bundler: Vite
Language: TypeScript
State: React Context or Zustand
Styling: CSS Modules or Tailwind
```

**Strengths:**
- Massive ecosystem, extensive documentation
- Vite provides fast HMR and optimized builds
- Well-understood component model
- Excellent TypeScript support
- Easy to find examples and solutions

**Weaknesses:**
- Larger bundle size than alternatives (~40-50KB min for React)
- Virtual DOM overhead (acceptable for this use case)
- JSX is non-standard (requires transpilation)

**SSE Integration:**
```typescript
// hooks/useSSE.ts
function useSSE(url: string) {
  const [items, setItems] = useState<Record<string, Item>>({});
  
  useEffect(() => {
    const source = new EventSource(url);
    source.onmessage = (event) => {
      const item = JSON.parse(event.data);
      setItems(prev => ({ ...prev, [item.name]: item }));
    };
    return () => source.close(); // Cleanup on unmount
  }, [url]);
  
  return items;
}
```

### Option B: Preact + Vite + TypeScript

```
Framework: Preact
Bundler: Vite
Language: TypeScript
State: Preact Signals or Context
Styling: CSS Modules or Tailwind
```

**Strengths:**
- Much smaller bundle (~3KB vs ~40KB for React)
- API-compatible with React (easy migration path)
- Signals provide efficient fine-grained reactivity
- Same tooling as React (Vite, TypeScript)

**Weaknesses:**
- Smaller ecosystem than React
- Some React libraries need compatibility layer
- Fewer developers familiar with Preact specifically

### Option C: Solid.js + Vite + TypeScript

```
Framework: Solid.js
Bundler: Vite
Language: TypeScript
State: Solid Signals (built-in)
Styling: CSS Modules or Tailwind
```

**Strengths:**
- Excellent performance (no Virtual DOM, fine-grained reactivity)
- Small bundle size (~7KB)
- Familiar JSX-like syntax
- Built-in reactive primitives

**Weaknesses:**
- Smaller ecosystem than React
- Learning curve (looks like React but different mental model)
- Fewer component libraries available

### Option D: Svelte + SvelteKit + TypeScript

```
Framework: Svelte 5
Bundler: SvelteKit/Vite
Language: TypeScript
State: Svelte Runes (built-in)
Styling: Scoped CSS (built-in)
```

**Strengths:**
- Compile-time framework (minimal runtime)
- Excellent performance
- Clean, minimal syntax
- Built-in scoped styling

**Weaknesses:**
- Different paradigm (not component-as-function)
- Smaller ecosystem
- SvelteKit adds complexity if only SPA needed

## Decision Matrix

| Criterion            | Weight | A: React | B: Preact | C: Solid | D: Svelte |
|----------------------|--------|----------|-----------|----------|-----------|
| Development velocity | 2x     | 5 (10)   | 4 (8)     | 3 (6)    | 4 (8)     |
| Resource efficiency  | 2x     | 3 (6)    | 5 (10)    | 5 (10)   | 5 (10)    |
| Type safety          | 1x     | 5        | 5         | 5        | 4         |
| Ecosystem maturity   | 1x     | 5        | 3         | 3        | 3         |
| SSE support          | 1x     | 5        | 5         | 5        | 5         |
| Maintainability      | 1x     | 5        | 4         | 3        | 4         |
| Tooling alignment    | 1x     | 5        | 5         | 5        | 4         |
| **Weighted Total**   |        | **41**   | **40**    | **37**   | **38**    |

*Scale: 1 (poor) to 5 (excellent)*

## Analysis

### React vs Preact: The Close Call

React and Preact score within 1 point. Key tradeoffs:

| Factor | React Advantage | Preact Advantage |
|--------|-----------------|------------------|
| Bundle size | - | 3KB vs 40KB |
| Ecosystem | Much larger | Mostly compatible |
| Documentation | More extensive | Uses React docs |
| Signals | Requires library | Built-in (preact/signals) |
| Hiring/onboarding | More familiar | Slightly less |

### Why Not Solid/Svelte?

Both are excellent frameworks, but:
- **Solid:** Different mental model despite similar syntax; learning curve for React developers
- **Svelte:** Great DX but different paradigm; smaller ecosystem for component libraries

For a project prioritizing development velocity, the React ecosystem advantage is significant.

### Bundle Size Consideration

For a wall-mounted dashboard on local network:
- Initial load happens once (device stays on)
- 40KB vs 3KB difference is ~0.3 seconds on slow network
- After initial load, both perform similarly

Bundle size matters less here than for a public website.

### State Management

For this use case, heavy state management is unnecessary:
- Single source of truth: backend SSE stream
- UI state: minimal (active panel, loading states, optimistic updates for controls)
- React Context or Preact Signals sufficient

No need for Redux, Zustand, or similar libraries initially.

### Command Handling

Commands (button presses, slider changes) follow a simple pattern:
1. User interacts with control
2. Frontend sends POST/PUT to backend API
3. Backend forwards command to smart home system
4. Smart home responds with state change
5. Backend broadcasts update via SSE
6. Frontend renders new state

For better UX, optimistic updates can show immediate feedback while awaiting confirmation.

## Decision

**Use Option A: React + Vite + TypeScript**

This is a close call—React and Preact scored within 1 point. The decision favors React primarily due to its broader ecosystem and reputation:

1. **Ecosystem breadth:** Largest selection of component libraries, examples, and solutions
2. **Community & reputation:** Most widely used; easier to find answers, tutorials, and developers
3. **Tooling:** Excellent Vite integration, straightforward TypeScript setup
4. **Bundle size acceptable:** Dashboard loads once and stays running; 40KB vs 3KB is negligible for this use case
5. **Migration path:** Can alias to Preact later if bundle size becomes a concern (API compatible)

## Future Consideration: Preact Migration

If bundle size or performance becomes a concern:
- Preact is largely API-compatible with React
- Vite supports aliasing React to Preact with minimal config
- Migration would be low-effort

## Implementation Notes

### Project Structure

```
packages/frontend/
├── src/
│   ├── main.tsx           # Entry point
│   ├── App.tsx            # Root component
│   ├── hooks/
│   │   └── useSSE.ts      # SSE subscription hook
│   ├── components/
│   │   ├── Dashboard.tsx
│   │   └── widgets/
│   │       ├── Temperature.tsx
│   │       ├── Weather.tsx
│   │       └── ...
│   ├── types/
│   │   └── item.ts        # Shared types (from backend)
│   └── styles/
├── index.html
├── vite.config.ts
├── tsconfig.json
└── package.json
```

### SSE Hook Pattern

```typescript
// hooks/useSSE.ts
import { useEffect, useState } from 'react';

interface Item {
  name: string;
  value: string;
  unit: string;
}

export function useSSE(url: string) {
  const [items, setItems] = useState<Record<string, Item>>({});
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const source = new EventSource(url);
    
    source.onopen = () => {
      setConnected(true);
      setError(null);
    };
    
    source.onmessage = (event) => {
      const item: Item = JSON.parse(event.data);
      setItems(prev => ({ ...prev, [item.name]: item }));
    };
    
    source.onerror = () => {
      setConnected(false);
      setError('Connection lost, reconnecting...');
      // EventSource auto-reconnects
    };
    
    return () => {
      source.close();
    };
  }, [url]);

  return { items, connected, error };
}
```

### Initial State Fetch

```typescript
// App.tsx
function App() {
  const [initialItems, setInitialItems] = useState<Record<string, Item>>({});
  const { items: sseItems, connected } = useSSE('/api/events');
  
  // Fetch initial state on mount
  useEffect(() => {
    fetch('/api/states')
      .then(res => res.json())
      .then(data => {
        const itemMap = data.reduce<Record<string, Item>>(
          (acc: Record<string, Item>, item: Item) => {
            acc[item.name] = item;
            return acc;
          },
          {}
        );
        setInitialItems(itemMap);
      });
  }, []);
  
  // Merge initial state with SSE updates
  const items = { ...initialItems, ...sseItems };
  
  return <Dashboard items={items} connected={connected} />;
}
```

### Command Hook Pattern

```typescript
// hooks/useCommand.ts
import { useState, useCallback } from 'react';

interface CommandOptions {
  optimistic?: boolean;  // Show immediate feedback
}

export function useCommand() {
  const [pending, setPending] = useState<Set<string>>(new Set());

  const sendCommand = useCallback(async (
    itemName: string, 
    value: string,
    options: CommandOptions = {}
  ) => {
    setPending(prev => new Set(prev).add(itemName));
    
    try {
      const response = await fetch(`/api/items/${itemName}/command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ value }),
      });
      
      if (!response.ok) {
        throw new Error(`Command failed: ${response.statusText}`);
      }
    } finally {
      setPending(prev => {
        const next = new Set(prev);
        next.delete(itemName);
        return next;
      });
    }
  }, []);

  return { sendCommand, isPending: (name: string) => pending.has(name) };
}
```

### Interactive Widget Examples

```typescript
// components/widgets/DimmerSlider.tsx
interface DimmerSliderProps {
  item: Item;
  onCommand: (value: string) => void;
  isPending: boolean;
}

function DimmerSlider({ item, onCommand, isPending }: DimmerSliderProps) {
  const [localValue, setLocalValue] = useState(Number(item.value));
  
  // Sync with SSE updates when not dragging
  useEffect(() => {
    if (!isPending) {
      setLocalValue(Number(item.value));
    }
  }, [item.value, isPending]);

  return (
    <input
      type="range"
      min={0}
      max={100}
      value={localValue}
      onChange={(e) => setLocalValue(Number(e.target.value))}
      onMouseUp={() => onCommand(String(localValue))}
      onTouchEnd={() => onCommand(String(localValue))}
      disabled={isPending}
    />
  );
}

// components/widgets/ToggleButton.tsx
function ToggleButton({ item, onCommand, isPending }: ToggleButtonProps) {
  const isOn = item.value === 'ON';
  
  return (
    <button
      onClick={() => onCommand(isOn ? 'OFF' : 'ON')}
      disabled={isPending}
      className={isOn ? 'active' : ''}
    >
      {isPending ? '...' : item.name}
    </button>
  );
}
```

## Consequences

### Positive

- Fast development with familiar tools
- Extensive component library options (if needed)
- Strong TypeScript integration
- Easy to find solutions to common problems
- Vite provides excellent DX (fast HMR, optimized builds)

### Negative

- Larger bundle than Preact/Solid (~40KB baseline)
- Virtual DOM overhead (negligible for this use case)

### Mitigations

1. **Bundle size:** Can alias to Preact if needed; code-split aggressively
2. **Performance:** React 18's concurrent features help; profile before optimizing

*Accepted: December 2025*
*Close decision between React and Preact; React chosen for ecosystem breadth and reputation.*
