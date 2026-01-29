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

### Phase 1: Protocol Hardening ✅ Complete

Small changes that don't break anything:

1. ✅ Add `name`, `adapter_type`, `prefix`, `close()` to protocol
2. ✅ Implement in `OpenHABAdapter`
3. ✅ Update health check to use `adapter.name` instead of `base_url`
4. ✅ Fix `sync_from_smart_home` type hint to use protocol

### Phase 2: ID Namespacing ✅ Complete

1. ✅ Add `prefix` property to protocol (default "oh" for OpenHAB)
2. ✅ Add `_prefixed_id()` helper to OpenHABAdapter
3. ✅ Update all Signal creations to use prefixed IDs (`prefix:item_name`)
4. Frontend will receive prefixed IDs transparently

### Phase 3: Multi-Adapter Orchestration ✅ Complete

1. ✅ YAML config schema with discriminated union (`AdapterConfig`)
2. ✅ Env var fallback for simple single-adapter setups
3. ✅ `AdapterManager` class with independent sync tasks
4. ✅ Graceful degradation (start even if some adapters fail)
5. ✅ Automatic retry with exponential backoff
6. ✅ Health check uses `adapter_manager.states` for connection status

### Phase 4: HomeAssistant Adapter

1. Implement `HomeAssistantAdapter` following protocol
2. Handle HA-specific quirks (WebSocket vs REST, auth tokens)
3. Add to config options

---

## Decisions Made

1. **Signal ID format:** `prefix:item_name` (e.g., `oh:LivingRoom_Temperature`)

2. **Where prefix is applied:** In the adapter, via `_prefixed_id()` helper

3. **Prefix is user-controllable:** Via `prefix` parameter in adapter constructor
   (default "oh" for OpenHAB, will be "ha" for HomeAssistant)

---

## Open Questions

1. **How to handle adapter failure?**

   - If OpenHAB goes down, should HA signals still flow?
   - Independent tasks with isolated error handling?

2. **Signal deduplication across adapters?**
   - Same physical sensor exposed in both systems?
   - User-configured aliases?

---

## References

- [ADR-005: Signal Abstraction](../adr/ADR-005-signal-abstraction.md)
- [SmartHomeAdapter Protocol](../../packages/backend/src/lumehaven/adapters/protocol.py)
- [OpenHAB Adapter](../../packages/backend/src/lumehaven/adapters/openhab/adapter.py)
