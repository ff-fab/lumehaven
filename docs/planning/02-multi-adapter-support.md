# Multi-Adapter Support Planning

Design document for supporting multiple smart home adapters simultaneously (e.g.,
OpenHAB + HomeAssistant).

**Status:** Planning **Related:** D11 (HomeAssistant Support), ADR-005 (Signal
Abstraction)

---

## Current State

### What Works for Multi-Adapter ✅

| Component                   | Status | Notes                              |
| --------------------------- | ------ | ---------------------------------- |
| `SmartHomeAdapter` protocol | Ready  | Defines contract for all adapters  |
| `Signal` model              | Ready  | Adapter-agnostic value object      |
| `SignalStore`               | Ready  | Accepts signals from any source    |
| Health check                | Ready  | Iterates `app.state.adapters` list |

### Gaps ⚠️

| Component               | Issue                                      | Effort |
| ----------------------- | ------------------------------------------ | ------ |
| Signal ID collisions    | `temperature` from both systems overwrites | Medium |
| Protocol incomplete     | Missing `name`, `adapter_type`, `close()`  | Small  |
| `main.py` orchestration | Hardcoded single adapter                   | Medium |
| Sync task               | Single adapter, wrong type hint            | Small  |
| Configuration           | No multi-adapter config schema             | Medium |

---

## Design Decisions Needed

### 1. Signal ID Namespacing

**Problem:** OpenHAB item `LivingRoom_Temp` and HA entity `living_room_temp` could
collide or be ambiguous.

**Options:**

| Option                       | Example ID                | Pros                       | Cons                             |
| ---------------------------- | ------------------------- | -------------------------- | -------------------------------- |
| A. Adapter prefix            | `openhab:LivingRoom_Temp` | Clear origin, no collision | Longer IDs, frontend must handle |
| B. User-configured prefix    | `oh:LivingRoom_Temp`      | User control, shorter      | Config complexity                |
| C. No prefix, require unique | `LivingRoom_Temp`         | Simple IDs                 | User must ensure uniqueness      |

**Recommendation:** Option A (adapter prefix) — explicit, zero ambiguity, easy to filter
by adapter in frontend.

### 2. Protocol Additions

Add to `SmartHomeAdapter`:

```python
@property
def name(self) -> str:
    """Unique instance identifier (e.g., 'openhab-main', 'ha-garage')."""
    ...

@property
def adapter_type(self) -> str:
    """System type: 'openhab' | 'homeassistant'."""
    ...

async def close(self) -> None:
    """Clean up resources."""
    ...
```

**Rationale:**

- `name` — User-friendly identifier for health checks, logs, UI grouping
- `adapter_type` — For ID prefixing, icon selection, type-specific behavior
- `close()` — Required for clean multi-adapter shutdown

### 3. Configuration Schema

Current (single adapter):

```env
SMART_HOME_TYPE=openhab
OPENHAB_URL=http://localhost:8080
OPENHAB_TAG=Dashboard
```

Proposed (multi-adapter, YAML or structured env):

```yaml
adapters:
  - name: main-openhab
    type: openhab
    url: http://openhab:8080
    tag: Dashboard

  - name: garage-ha
    type: homeassistant
    url: http://homeassistant:8123
    token: ${HA_TOKEN}
```

**Decision needed:** YAML config file vs structured environment variables vs
pydantic-settings with nested models.

---

## Implementation Plan

### Phase 1: Protocol Hardening (Do Now)

Small changes that don't break anything:

1. Add `name`, `adapter_type`, `close()` to protocol
2. Implement in `OpenHABAdapter`
3. Update health check to use `adapter.name` instead of `base_url`
4. Fix `sync_from_smart_home` type hint to use protocol

### Phase 2: ID Namespacing (Before HomeAssistant)

1. Add ID prefix logic to adapters or store
2. Update `Signal` creation to include adapter prefix
3. Ensure frontend handles prefixed IDs gracefully

### Phase 3: Multi-Adapter Orchestration (With HomeAssistant)

1. Design config schema for multiple adapters
2. Refactor `main.py` lifespan to create adapter list
3. Create sync task per adapter
4. Update `app.state.adapters` usage

### Phase 4: HomeAssistant Adapter

1. Implement `HomeAssistantAdapter` following protocol
2. Handle HA-specific quirks (WebSocket vs REST, auth tokens)
3. Add to config options

---

## Open Questions

1. **Should adapters own their ID prefix, or should the store apply it?**

   - Adapter: cleaner separation, adapter knows its identity
   - Store: centralized, easier to change strategy

2. **How to handle adapter failure?**

   - If OpenHAB goes down, should HA signals still flow?
   - Independent tasks with isolated error handling?

3. **Signal deduplication across adapters?**
   - Same physical sensor exposed in both systems?
   - User-configured aliases?

---

## References

- [ADR-005: Signal Abstraction](../adr/ADR-005-signal-abstraction.md)
- [SmartHomeAdapter Protocol](../../packages/backend/src/lumehaven/adapters/protocol.py)
- [OpenHAB Adapter](../../packages/backend/src/lumehaven/adapters/openhab/adapter.py)
