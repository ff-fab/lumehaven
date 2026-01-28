# ADR-002: Backend Language and Runtime

## Status

Accepted

## Context

The backend serves as a BFF (Backend for Frontend) that:

1. Consumes SSE events from smart home systems (OpenHAB, later HomeAssistant)
2. Normalizes data (units, formatting, encoding)
3. Maintains in-memory state (per ADR-001)
4. Serves REST endpoints for initial state fetch
5. Serves SSE endpoints for real-time updates to the frontend

The target deployment is a Raspberry Pi 4 (ARM64, 1-8GB RAM). Development velocity,
maintainability, and resource efficiency are all important.

## Decision Drivers

1. **Development velocity** - Time to working implementation
2. **Resource efficiency** - Memory and CPU usage on Raspberry Pi 4
3. **Async capability** - Must handle concurrent SSE streams efficiently
4. **Ecosystem maturity** - Libraries for SSE, HTTP clients, validation
5. **Type safety** - Catch errors at compile/lint time
6. **Maintainability** - Code clarity, debugging, onboarding
7. **ARM64 support** - Must run reliably on Raspberry Pi
8. **Tooling alignment** - Consistency with frontend tooling choices

## Considered Options

### Option A: Python + FastAPI + uv

```
Runtime: Python 3.12+
Framework: FastAPI + Starlette
Package manager: uv
Key libraries: httpx (async HTTP), sse-starlette, pydantic v2
```

**Strengths:**

- FastAPI is mature, well-documented, production-proven
- Excellent async support via asyncio
- pydantic v2 provides fast validation with good DX
- uv is extremely fast (10-100x pip)
- Strong typing with mypy/pyright
- Large ecosystem, easy to find solutions
- Runs well on ARM64 (native Python)

**Weaknesses:**

- Higher memory footprint than compiled languages (~50-100MB baseline)
- GIL limits true parallelism (mitigated by async I/O)
- Two languages in the stack (Python backend, TypeScript frontend)

**SSE Implementation:**

```python
# Consuming SSE from OpenHAB
async with httpx.AsyncClient() as client:
    async with client.stream("GET", f"{base_url}/events") as response:
        async for line in response.aiter_lines():
            yield parse_sse(line)

# Serving SSE to frontend
from sse_starlette.sse import EventSourceResponse

@app.get("/events")
async def events():
    return EventSourceResponse(state_store.subscribe())
```

### Option B: Bun + TypeScript + Hono/Elysia

```
Runtime: Bun 1.x
Framework: Hono or Elysia
Package manager: Bun (built-in)
Key libraries: zod (validation), built-in fetch/Response
```

**Strengths:**

- Unified tooling with frontend (both TypeScript, both Bun)
- Very fast startup and execution
- Native TypeScript (no transpilation step)
- Built-in test runner, bundler
- Modern APIs (fetch, Response, streams)

**Weaknesses:**

- Less mature than Python ecosystem
- ARM64 support exists but less battle-tested on Pi
- Smaller community, fewer examples
- Framework ecosystem still evolving (Hono vs Elysia vs raw)
- SSE client libraries less mature than Python's

**SSE Implementation:**

```typescript
// Consuming SSE from OpenHAB
const response = await fetch(`${baseUrl}/events`);
const reader = response.body?.getReader();
// Manual SSE parsing required or use eventsource-parser

// Serving SSE to frontend (Hono)
app.get('/events', (c) => {
  return streamSSE(c, async (stream) => {
    for await (const item of stateStore.subscribe()) {
      await stream.writeSSE({ data: JSON.stringify(item) });
    }
  });
});
```

### Option C: Rust + Axum + Tokio

```
Runtime: Native binary
Framework: Axum
Package manager: Cargo
Key libraries: tokio (async), reqwest (HTTP), serde (serialization)
```

**Strengths:**

- Best resource efficiency (lowest memory, fastest execution)
- Excellent for resource-constrained Pi deployment
- Strong compile-time guarantees
- No runtime dependencies (single binary)
- axum is well-designed and production-ready

**Weaknesses:**

- Steep learning curve (ownership, lifetimes, async)
- Slower development velocity (compile times, fighting borrow checker)
- Smaller web ecosystem than Python
- Overkill for I/O-bound workload (smart home API calls)
- Two very different languages in stack

**SSE Implementation:**

```rust
// Consuming SSE - requires manual implementation or eventsource-client crate
// Serving SSE
async fn events(State(store): State<Arc<StateStore>>) -> Sse<impl Stream<Item = Result<Event, Infallible>>> {
    let stream = store.subscribe().map(|item| {
        Ok(Event::default().data(serde_json::to_string(&item).unwrap()))
    });
    Sse::new(stream)
}
```

### Option D: Node.js + Express/Fastify

```
Runtime: Node.js 20+
Framework: Fastify
Package manager: npm/pnpm
Key libraries: undici (HTTP), zod, better-sse
```

**Strengths:**

- Mature, stable, well-understood
- Large ecosystem
- Same language as frontend (if using JS/TS)

**Weaknesses:**

- If using Bun for frontend, why not Bun for backend too?
- Slower than Bun
- npm/pnpm slower than Bun's package manager
- No compelling advantage over Python or Bun

## Decision Matrix

| Criterion            | Weight | A: Python | B: Bun | C: Rust | D: Node |
| -------------------- | ------ | --------- | ------ | ------- | ------- |
| Development velocity | 2x     | 5 (10)    | 4 (8)  | 2 (4)   | 4 (8)   |
| Resource efficiency  | 2x     | 3 (6)     | 4 (8)  | 5 (10)  | 3 (6)   |
| Async capability     | 1x     | 5         | 5      | 5       | 5       |
| Ecosystem maturity   | 1x     | 5         | 3      | 4       | 5       |
| Type safety          | 1x     | 4         | 5      | 5       | 4       |
| Maintainability      | 1x     | 5         | 4      | 3       | 4       |
| ARM64 support        | 1x     | 5         | 4      | 5       | 5       |
| Tooling alignment    | 1x     | 3         | 5      | 2       | 3       |
| **Weighted Total**   |        | **43**    | **42** | **38**  | **40**  |

_Scale: 1 (poor) to 5 (excellent)_

## Analysis

### Python vs Bun: The Close Call

Python and Bun score within 1 point. The key tradeoffs:

| Factor            | Python Advantage                | Bun Advantage                             |
| ----------------- | ------------------------------- | ----------------------------------------- |
| SSE libraries     | httpx, sse-starlette are mature | Must parse SSE manually or use newer libs |
| Validation        | pydantic v2 is exceptional      | zod is good but different paradigm        |
| Development speed | Slightly faster (more examples) | Unified with frontend                     |
| Memory            | ~50-100MB baseline              | ~30-50MB baseline                         |
| Pi deployment     | Very well tested                | Works but less common                     |

### Why Not Rust?

Rust would be ideal for resource efficiency, but:

- This is an I/O-bound workload (waiting on HTTP), not CPU-bound
- Development velocity matters more than shaving 30MB RAM
- The abstraction from ADR-001 means we can always rewrite the backend later if needed
- Learning curve would significantly slow initial development

### Why Not Node.js?

If TypeScript is desired, Bun is strictly better:

- Faster runtime
- Faster package management
- Native TypeScript
- Built-in tooling

Node.js offers no advantage over Bun for a new project.

## Decision

**Use Option A: Python + FastAPI + uv**

Rationale:

1. **Proven path:** FastAPI + async Python is well-documented for exactly this use case
   (SSE proxy)
2. **Ecosystem:** httpx, sse-starlette, pydantic are mature and well-maintained
3. **uv eliminates Python's packaging pain:** Dependency resolution in milliseconds
4. **Pi-friendly:** Python on ARM64 is thoroughly battle-tested
5. **Flexibility:** The StateStore abstraction (ADR-001) allows backend replacement if
   needed

## Future Consideration: Rust Rewrite

Rust (Option C) is noted as a potential future development path for two reasons:

1. **Resource efficiency:** Lower memory footprint would benefit the Raspberry Pi
   deployment
2. **Learning opportunity:** This project serves dual purposes—building a useful
   dashboard and learning new technologies

The abstracted architecture from ADR-001 makes a future Rust rewrite feasible:

- The `StateStore` protocol defines a clear interface
- Smart home adapters are isolated behind protocols
- Frontend contract (REST + SSE) remains unchanged regardless of backend language

A Rust rewrite could be approached incrementally or as a complete replacement once
Python version is stable and feature-complete.

## Consequences

### Positive

- Fast development with familiar tools
- Excellent documentation and community support
- pydantic v2 provides runtime validation matching TypeScript frontend types
- uv makes dependency management painless
- Easy to find contributors who know Python

### Negative

- Two languages in stack (Python + TypeScript)
- Higher baseline memory than Bun or Rust
- Must use mypy/pyright for type checking (not built into language)

### Mitigations

1. **Memory:** Profile and optimize; Python 3.12+ has significant memory improvements
2. **Type safety:** Enforce strict mypy in CI; use pydantic for runtime validation
3. **Two languages:** Accept this as reasonable for BFF + SPA architecture

_Accepted: December 2025_
