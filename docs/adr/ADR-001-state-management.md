# ADR-001: State Management Architecture

## Status

Accepted

## Context

A common architecture for real-time smart home dashboards, analyzed in a PoC, uses Redis as an intermediate state store and message broker between separate backend services:

1. **Observer service** - Consumes SSE events from the smart home system, writes item states to Redis, publishes change notifications
2. **API service** - Subscribes to Redis pub/sub, serves state to frontend via REST and SSE

This architecture enables horizontal scaling and service decoupling. However, an assumed likely target deployment is a single Raspberry Pi 4 serving a household dashboard—a much simpler scenario that may not benefit from this complexity.

The question: keep Redis for its flexibility, or simplify to a single-process backend?

## Decision Drivers

1. **Operational simplicity** - Fewer moving parts = fewer failure modes
2. **Resource efficiency** - Raspberry Pi 4 has limited RAM (1-8GB depending on model)
3. **Development velocity** - Simpler architecture = faster iteration
4. **Deployment complexity** - Docker Compose is the deployment method; container count is a factor
5. **Future flexibility** - Ability to scale or add features later
6. **Debugging ease** - Tracing issues across services vs. single process

## Considered Options

### Option A: Multi-Service with Redis
Two backend services communicating via Redis as state store and pub/sub broker.

```
┌─────────────┐     ┌──────────┐     ┌─────────────┐     ┌──────────┐     ┌──────────┐
│  OpenHAB    │────▶│ Observer │────▶│   Redis     │────▶│   API    │────▶│ Frontend │
│  (SSE)      │     │ Service  │     │ (state+pub) │     │ Service  │     │  (SSE)   │
└─────────────┘     └──────────┘     └─────────────┘     └──────────┘     └──────────┘
```

### Option B: Single Backend Process (no Redis)
Merge observer and API into one FastAPI service with in-memory state.

```
┌─────────────┐     ┌─────────────────────────────┐     ┌──────────┐
│  OpenHAB    │────▶│  Backend (FastAPI)          │────▶│ Frontend │
│  (SSE)      │     │  - SSE consumer (async)     │     │  (SSE)   │
│             │     │  - In-memory state dict     │     │          │
│             │     │  - REST + SSE endpoints     │     │          │
└─────────────┘     └─────────────────────────────┘     └──────────┘
```

### Option C: Single Backend with Abstracted Storage
Design for in-memory by default, but abstract state storage to allow Redis later.

```python
class StateStore(Protocol):
    async def get(self, key: str) -> Item | None: ...
    async def set(self, key: str, item: Item) -> None: ...
    async def subscribe(self) -> AsyncIterator[Item]: ...

class InMemoryStore(StateStore): ...  # Default
class RedisStore(StateStore): ...      # Optional, for scaling
```

## Decision Matrix

| Criterion                | Weight | A: Redis | B: Single Process | C: Abstracted |
|--------------------------|--------|----------|-------------------|---------------|
| Future flexibility       | 2x     | 5 (10)   | 2 (4)             | 4 (8)         |
| Resource efficiency      | 2x     | 3 (6)    | 5 (10)            | 5 (10)        |
| Operational simplicity   | 1x     | 2        | 5                 | 4             |
| Development velocity     | 1x     | 3        | 5                 | 4             |
| Deployment complexity    | 1x     | 3        | 5                 | 4             |
| Debugging ease           | 1x     | 2        | 5                 | 4             |
| **Weighted Total**       |        | **26**   | **34**            | **34**        |

*Scale: 1 (poor) to 5 (excellent). Weighted criteria marked with multiplier.*

With equal weighted scores, **Option C** is preferred because it matches Option B's resource efficiency while providing a clear upgrade path (future flexibility score of 4 vs 2).

## Analysis

### What Redis Provides

1. **State persistence** - Items survive backend restart
2. **Pub/Sub** - Decouples producer from consumer
3. **Service isolation** - Services can be deployed/scaled independently
4. **Atomic operations** - Pipeline for batch updates

### What Is Lost Without Redis

1. **State persistence across restarts** - Items must be re-fetched from the smart home system on startup (this is fast and ensures consistency anyway)
2. **Service decoupling** - Single point of failure (acceptable for home dashboard)
3. **Horizontal scaling** - Cannot run multiple API instances (not needed for single-household use)

### What Is Gained Without Redis

1. **~50MB less RAM** - Redis baseline memory usage
2. **One fewer container** - Simpler deployment
3. **No network hops** - State access is instant (dict lookup vs. Redis round-trip)
4. **Simpler debugging** - All state visible in one process
5. **No Redis expertise needed** - Lower barrier to contribution

### Docker Compose Complexity

Docker Compose handles multi-container orchestration, but Redis still adds operational surface area:

| Aspect | Without Redis | With Redis |
|--------|---------------|------------|
| Containers | 2 (backend + frontend) | 4 (observer + api + redis + frontend) |
| Config files | 1 service config | 2 service configs + Redis config |
| Networking | Simple | Redis connectivity required |
| Data volumes | None needed | Redis persistence volume |
| Startup order | Simple | Redis must start before services |
| Memory overhead | ~0 | ~50-100MB for Redis |
| Failure modes | Backend crash | Observer crash, API crash, Redis crash, Redis OOM |

Redis adds meaningful operational complexity beyond "just another container."

## Decision

**Use Option C: Single Backend with Abstracted State Storage**

Use a single FastAPI backend with in-memory state storage for the initial implementation, but design the state storage as a pluggable abstraction. This provides:

- Immediate simplicity (Option B benefits)
- Future flexibility (Option A benefits) without paying the cost now
- Clean architecture regardless of storage choice

The abstraction is lightweight (~50 lines of code) and enforces good separation of concerns.

## Consequences

### Positive

- Simpler deployment: 2 containers instead of 4
- Lower memory footprint on Raspberry Pi
- Faster development iteration
- State loss on restart is acceptable (full refresh from smart home takes <1 second)
- Abstraction enables Redis addition later if needed (e.g., multiple dashboard instances)

### Negative

- State is lost on backend restart (mitigated: immediate re-fetch from smart home)
- Cannot scale horizontally (acceptable: single-household use case)
- Must implement pub/sub internally for SSE broadcasting (mitigated: `asyncio.Queue` or `broadcaster` library)

### Mitigations

1. **Startup re-fetch:** On backend start, fetch all items from the smart home system
2. **Internal pub/sub:** Use `asyncio` primitives or the `broadcaster` library for in-process event distribution
3. **Graceful degradation:** If abstraction proves unnecessary after 6 months, remove it

## Implementation Notes

```python
# Minimal abstraction example
from typing import Protocol, AsyncIterator
from dataclasses import dataclass
import asyncio

@dataclass
class Item:
    name: str
    value: str
    unit: str

class StateStore(Protocol):
    async def get_all(self) -> dict[str, Item]: ...
    async def set(self, key: str, item: Item) -> None: ...
    async def subscribe(self) -> AsyncIterator[Item]: ...

class InMemoryStore:
    def __init__(self):
        self._items: dict[str, Item] = {}
        self._subscribers: list[asyncio.Queue] = []
    
    async def get_all(self) -> dict[str, Item]:
        return self._items.copy()
    
    async def set(self, key: str, item: Item) -> None:
        self._items[key] = item
        for queue in self._subscribers:
            await queue.put(item)
    
    async def subscribe(self) -> AsyncIterator[Item]:
        queue = asyncio.Queue()
        self._subscribers.append(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self._subscribers.remove(queue)
```

*Accepted: December 2025*
*Weighted decision matrix prioritizing future flexibility and resource efficiency.*
