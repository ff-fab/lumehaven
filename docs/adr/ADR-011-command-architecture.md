# ADR-011: Command Architecture

## Status

Accepted **Date:** 2026-02-08

## Context

The dashboard must support **interactive controls** — toggle switches, dimmer sliders,
thermostat setpoints, scene triggers. ADR-005 and ADR-010 define the read path
(signals flowing from smart home → backend → frontend via SSE). This ADR defines the
**write path** (commands flowing from frontend → backend → smart home).

The PoC was read-only (display only, no controls). The current backend adapter protocol
(`SmartHomeAdapter`) has no `send_command()` method. The command path must be designed
to work with the BFF pattern (frontend never talks to smart home APIs directly) and
the enriched Signal model (ADR-010).

## Decision Drivers

1. **BFF compliance** — commands route through the backend, never directly to smart
   home APIs
2. **Platform abstraction** — the frontend sends a generic command; the adapter
   translates to platform-specific API calls
3. **Responsiveness** — optimistic updates provide immediate feedback; SSE confirms
   the actual state
4. **Simplicity** — command API should be as simple as the signal display API
   (one-liner in the frontend)
5. **Adapter independence** — each adapter implements commands in its platform-native
   way

## Considered Options

### Option A: Simple String Commands

```
Frontend: POST /api/signals/{signal_id}/command  { "value": "ON" }
Backend:  adapter.send_command(signal_id, "ON")
Adapter:  OpenHAB POST /rest/items/{name}  body: "ON"
```

Commands are always string values, matching how OpenHAB's REST API works (plain text
command body). The adapter interprets the string in platform context.

**Strengths:**

- Matches OpenHAB's native command model (plain string commands)
- Simple API surface — one endpoint, one field
- Frontend doesn't need to know command types

**Weaknesses:**

- No type validation (sending "ON" to a number item is a caller error)
- HomeAssistant service calls have structured payloads that don't map cleanly to
  a single string

### Option B: Typed Commands

```
Frontend: POST /api/signals/{signal_id}/command  { "value": true, "type": "boolean" }
Backend:  adapter.send_command(signal_id, True)
Adapter:  OpenHAB POST /rest/items/{name}  body: "ON"  (adapter maps True → "ON")
```

Commands carry typed values matching `signal_type` from ADR-010. The backend validates
the type before forwarding to the adapter.

**Strengths:**

- Type safety — backend rejects invalid commands before they reach the smart home
- Consistent with the typed Signal model

**Weaknesses:**

- More complex API surface
- Type validation logic in the backend
- HomeAssistant service calls still need adapter-level translation

### Option C: Command Verbs

```
Frontend: POST /api/signals/{signal_id}/command  { "command": "INCREASE", "value": "5" }
Backend:  adapter.send_command(signal_id, Command("INCREASE", "5"))
Adapter:  OpenHAB POST /rest/items/{name}  body: "INCREASE"
```

Rich command model with verbs (ON, OFF, INCREASE, DECREASE, STOP, etc.).

**Strengths:**

- Supports complex interactions (e.g., "increase dimmer by 5%")
- Maps naturally to OpenHAB's command types

**Weaknesses:**

- Over-engineered for most use cases
- Verb set must be maintained and may differ per platform
- Frontend must know valid verbs per signal type

## Decision

**Use Option A: Simple string commands.**

The command flow:

```
┌──────────────┐     POST /api/signals/{id}/command     ┌──────────────────┐
│   Frontend   │ ──────────────────────────────────────▸ │     Backend      │
│              │     { "value": "ON" }                   │                  │
│  useCommand()│                                         │  resolve adapter │
│              │                                         │  send_command()  │
│              │     SSE: signal update                  │                  │
│              │ ◂────────────────────────────────────── │  ◂── SSE from   │
│              │     { "id": "oh:Light", "value": true,  │      smart home  │
│              │       "display_value": "An", ... }      │                  │
└──────────────┘                                         └──────────────────┘
```

### Adapter Protocol Extension

```python
class SmartHomeAdapter(Protocol):
    # ... existing read methods ...

    async def send_command(self, signal_id: str, command: str) -> None:
        """Send a command to a signal/device.

        The command is a plain string value matching the platform's native
        command format. The adapter translates as needed.

        Args:
            signal_id: The signal's ID (without prefix).
            command: The command value as a string.

        Raises:
            SmartHomeConnectionError: If the command cannot be delivered.
            SignalNotFoundError: If the signal_id doesn't exist.
        """
        ...
```

### REST Endpoint

```
POST /api/signals/{signal_id}/command
Content-Type: application/json

{ "value": "ON" }

Response: 202 Accepted  (command dispatched, await SSE for confirmation)
Response: 404 Not Found (signal_id unknown)
Response: 502 Bad Gateway (adapter failed to deliver command)
```

**202 Accepted** (not 200 OK) because the command is asynchronous — the actual state
change arrives via SSE. The frontend should not block on the response.

### Frontend: `useCommand()` Hook

Lives in `@lumehaven/react`:

```typescript
interface UseCommandOptions {
  optimistic?: boolean;  // Default: true — show value immediately
  timeout?: number;      // Revert optimistic update after N ms (default: 5000)
}

function useCommand(options?: UseCommandOptions) {
  const sendCommand = (signalId: string, value: string) => Promise<void>;
  const isPending = (signalId: string) => boolean;
  return { sendCommand, isPending };
}
```

**Optimistic update flow (default):**

1. User taps "ON" → `sendCommand("oh:Light", "ON")`
2. Frontend immediately updates local signal state: `value = true`,
   `display_value = "An"`
3. POST fires to backend (202 response)
4. SSE delivers confirmed state update → replaces optimistic value
5. If no SSE confirmation within timeout → revert to previous value

**Non-optimistic flow** (opt-out: `{ optimistic: false }`):

1. User taps "ON" → `sendCommand("oh:Light", "ON")`
2. Frontend shows pending indicator (`isPending("oh:Light") === true`)
3. POST fires to backend
4. SSE delivers confirmed state update → UI updates naturally
5. Pending clears on SSE update or timeout

### Core: `CommandClient`

Lives in `@lumehaven/core` (framework-agnostic):

```typescript
class CommandClient {
  constructor(private backendUrl: string) {}

  async sendCommand(signalId: string, value: string): Promise<void> {
    const response = await fetch(
      `${this.backendUrl}/api/signals/${signalId}/command`,
      { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ value }) }
    );
    if (!response.ok) throw new CommandError(response.status, signalId);
  }
}
```

## Implementation Phasing

| Phase | What | When |
|-------|------|------|
| **Now** | Add `send_command()` to adapter protocol definition | Backend enrichment phase |
| **Now** | Design the REST endpoint and response model | Backend enrichment phase |
| **Later** | Implement `send_command()` in OpenHAB adapter | When building interactive widgets |
| **Later** | Implement REST endpoint in `routes.py` | When building interactive widgets |
| **Later** | Implement `CommandClient` in `@lumehaven/core` | Frontend widget phase |
| **Later** | Implement `useCommand()` in `@lumehaven/react` | Frontend widget phase |

The protocol extension and endpoint design are decided now. Implementation is deferred
to the interactive widget phase.

## Consequences

### Positive

- Simple, uniform command API — one endpoint, one string value
- BFF pattern preserved — frontend never touches smart home APIs
- Optimistic updates by default provide snappy UX
- Adapter protocol cleanly separates read (signals) from write (commands)
- Non-optimistic opt-out available for cases where accuracy matters more than speed

### Negative

- String commands lose type safety (mitigated: adapters validate platform-side)
- HomeAssistant service calls may need richer command payloads in the future
  (mitigated: adapter can parse structured strings or we extend the API later)
- Optimistic updates can show incorrect state briefly if commands fail

### Risks & Mitigations

| Risk                                        | Mitigation                                    |
| ------------------------------------------- | --------------------------------------------- |
| String commands are too limited for HA       | Adapter translates; extend API if needed       |
| Optimistic updates cause UX inconsistency    | Configurable timeout + revert + opt-out        |
| Command failures not visible to user         | `isPending` indicator + timeout revert in UI   |

## Related Decisions

- [ADR-005](ADR-005-signal-abstraction.md) / [ADR-010](ADR-010-signal-model-enrichment.md)
  — Signal model (read path)
- [ADR-008](ADR-008-frontend-package-architecture.md) — `CommandClient` in core,
  `useCommand()` in react
- [ADR-001](ADR-001-state-management.md) — State management (commands don't change the
  store directly; SSE confirmation does)

_February 2026_
