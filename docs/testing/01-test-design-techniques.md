# Test Design Techniques

> **ISTQB Alignment:** This chapter applies ISTQB Foundation Level test design
> techniques to lumehaven components. We focus on techniques, not organizational
> aspects.

## Overview

We use a mix of black-box and white-box techniques, selected based on component
characteristics:

| Technique                    | When We Use It                              |
| ---------------------------- | ------------------------------------------- |
| **Equivalence Partitioning** | Implicitly through pytest parametrization   |
| **Boundary Value Analysis**  | Numeric thresholds, timeouts, limits        |
| **State Transition Testing** | Adapter lifecycle, connection states        |
| **Decision Tables**          | Config validation with discriminated unions |
| **Statement Coverage**       | Primary coverage metric                     |
| **Branch Coverage**          | Secondary metric (advisory, later enforced) |

---

## Black-Box Techniques

### Equivalence Partitioning (EP)

**What it is:** Divide the input domain into classes where all values in a class should
produce equivalent behavior. Test one representative from each class.

**Our approach:** We let equivalence classes emerge organically through pytest
parametrization rather than documenting them upfront. This keeps tests as the single
source of truth and avoids documentation drift.

**Example pattern:**

```python
@pytest.mark.parametrize("item_type,expected_unit", [
    # Numeric types with units
    ("Number:Temperature", "°C"),
    ("Number:Power", "W"),
    # Binary types (no unit)
    ("Switch", None),
    ("Contact", None),
    # Text types (no unit)
    ("String", None),
])
def test_extract_unit_from_item_type(item_type: str, expected_unit: str | None) -> None:
    """Each parametrized case represents an equivalence class."""
    ...
```

**Rationale:** Major Python projects like CPython and requests document test categories
implicitly through test organization and parametrization. This reduces maintenance
burden while preserving coverage.

---

### Boundary Value Analysis (BVA)

**What it is:** Test at the edges of equivalence classes—minimum, maximum, just inside,
just outside valid ranges. Off-by-one errors cluster at boundaries.

**Apply to:**

| Component        | Boundaries to Test                                                 |
| ---------------- | ------------------------------------------------------------------ |
| `AdapterManager` | Retry delays: `INITIAL_RETRY_DELAY` (5s), `MAX_RETRY_DELAY` (300s) |
| `SignalStore`    | Queue size limits: `subscriber_queue_size` setting                 |
| `config.py`      | Port ranges (0-65535), empty vs non-empty strings                  |
| Unit formatting  | Precision digits (0, max), numeric edge cases                      |

**Example pattern:**

```python
@pytest.mark.parametrize("retry_count,expected_delay", [
    (0, 5.0),      # Initial
    (1, 10.0),     # First backoff
    (5, 160.0),    # Mid-range
    (10, 300.0),   # At max cap
    (11, 300.0),   # Beyond max (should stay capped)
])
def test_retry_delay_backoff(retry_count: int, expected_delay: float) -> None:
    """Boundary: verify delay caps at MAX_RETRY_DELAY."""
    ...
```

---

### State Transition Testing

**What it is:** Model the system as a state machine, test valid transitions and verify
invalid transitions are rejected or handled gracefully.

**Apply to:** `AdapterManager` lifecycle—the most stateful component.

#### Adapter Lifecycle State Diagram

```
                                    ┌─────────────────────────────────────┐
                                    │                                     │
                                    ▼                                     │
┌──────────┐   add()   ┌────────────────┐   start_all()   ┌───────────┐  │
│  (none)  │ ────────► │   REGISTERED   │ ───────────────►│ CONNECTING│  │
└──────────┘           └────────────────┘                 └─────┬─────┘  │
                                                                │        │
                              ┌──────────────────────────┬──────┴────────┤
                              │                          │               │
                              ▼                          ▼               │
                       ┌─────────────┐           ┌─────────────┐         │
                       │  CONNECTED  │           │   FAILED    │         │
                       │  (syncing)  │           │  (waiting)  │         │
                       └──────┬──────┘           └──────┬──────┘         │
                              │                         │                │
                         stream ends                 retry timer         │
                         or error                    fires               │
                              │                         │                │
                              ▼                         │                │
                       ┌─────────────┐                  │                │
                       │DISCONNECTED │──────────────────┘                │
                       │  (backoff)  │                                   │
                       └──────┬──────┘                                   │
                              │                                          │
                         reconnect                                       │
                         succeeds                                        │
                              │                                          │
                              └──────────────────────────────────────────┘

                       ════════════════════════════════════════════════
                                          stop_all()
                       ════════════════════════════════════════════════
                                              │
                                              ▼
                                       ┌───────────┐
                                       │  STOPPED  │
                                       └───────────┘
```

#### State Definitions

| State        | `AdapterState` Fields                             | Description                                  |
| ------------ | ------------------------------------------------- | -------------------------------------------- |
| REGISTERED   | `connected=False`, `sync_task=None`, `error=None` | Added but not started                        |
| CONNECTING   | (transitional)                                    | Attempting initial connection                |
| CONNECTED    | `connected=True`, `sync_task=Task`, `error=None`  | Actively syncing                             |
| FAILED       | `connected=False`, `sync_task=None`, `error=str`  | Initial connect failed, retry scheduled      |
| DISCONNECTED | `connected=False`, `sync_task=Task`, `error=str`  | Was connected, lost connection, reconnecting |
| STOPPED      | Adapter closed                                    | Graceful shutdown complete                   |

#### Required Test Transitions

| #   | From         | Trigger               | To                       | Test Priority |
| --- | ------------ | --------------------- | ------------------------ | ------------- |
| T1  | (none)       | `add()`               | REGISTERED               | Medium        |
| T2  | REGISTERED   | `start_all()` success | CONNECTED                | High          |
| T3  | REGISTERED   | `start_all()` failure | FAILED                   | High          |
| T4  | CONNECTED    | stream ends           | DISCONNECTED             | High          |
| T5  | CONNECTED    | stream error          | DISCONNECTED             | High          |
| T6  | DISCONNECTED | reconnect success     | CONNECTED                | High          |
| T7  | DISCONNECTED | reconnect failure     | DISCONNECTED             | Medium        |
| T8  | FAILED       | retry success         | CONNECTED                | High          |
| T9  | FAILED       | retry failure         | FAILED (delay increased) | Medium        |
| T10 | Any          | `stop_all()`          | STOPPED                  | High          |

#### Invalid Transitions to Verify

- `add()` with duplicate name → raises `ValueError`
- `start_all()` when already started → should be idempotent or error

---

### Decision Tables

**What it is:** Enumerate combinations of conditions and their expected outcomes. Useful
when multiple inputs interact to determine behavior.

**Apply to:** Configuration validation only (highest combinatorial complexity).

#### Config Source Decision Table

The system can be configured via environment variables OR YAML file. This table captures
the resolution logic:

| #   | YAML exists | YAML valid            | Env vars set | Result                       |
| --- | ----------- | --------------------- | ------------ | ---------------------------- |
| 1   | No          | —                     | No           | Use defaults                 |
| 2   | No          | —                     | Yes          | Use env vars                 |
| 3   | Yes         | Yes                   | No           | Use YAML                     |
| 4   | Yes         | Yes                   | Yes          | YAML wins (env vars ignored) |
| 5   | Yes         | No (parse error)      | —            | Raise `ConfigError`          |
| 6   | Yes         | No (validation error) | —            | Raise `ConfigError`          |

#### Adapter Type Discriminator Table

Pydantic uses the `type` field to select the correct adapter config model:

| #   | `type` value      | Other fields         | Result                       |
| --- | ----------------- | -------------------- | ---------------------------- |
| 1   | `"openhab"`       | Valid OpenHAB fields | `OpenHABAdapterConfig`       |
| 2   | `"homeassistant"` | Valid HA fields      | `HomeAssistantAdapterConfig` |
| 3   | `"openhab"`       | Invalid fields       | Validation error             |
| 4   | `"unknown"`       | Any                  | Validation error             |
| 5   | Missing           | Any                  | Validation error             |

---

## White-Box Techniques

### Statement Coverage (Primary Metric)

**What it is:** Percentage of executable statements exercised by tests.

**Target:** See [Coverage Strategy](03-coverage-strategy.md) for targets per component.

**Why primary:** Statement coverage is the industry baseline. CPython, FastAPI, and
requests all track line coverage as their primary metric. It's simple to measure and
understand.

### Branch Coverage (Secondary Metric)

**What it is:** Percentage of decision branches (both true and false paths) exercised.

**Status:** Advisory only initially. We'll enable `--branch` in coverage reports after
achieving statement coverage targets.

**Why deferred:** Branch coverage requires higher test investment. Achieving solid
statement coverage first ensures we have tests before optimizing their thoroughness.

### MC/DC (Not Used)

**What it is:** Modified Condition/Decision Coverage—each condition independently
affects the decision outcome.

**Decision:** Skip. MC/DC is designed for safety-critical systems (avionics, medical). A
smart home dashboard doesn't warrant this level of rigor. The ROI is negative.

---

## Technique Selection by Component

| Component        | Primary Techniques        | Rationale                                   |
| ---------------- | ------------------------- | ------------------------------------------- |
| `Signal` model   | EP (parametrized), BVA    | Simple dataclass, test valid/invalid inputs |
| `SignalStore`    | State transition, BVA     | Pub/sub has state, queue has limits         |
| `AdapterManager` | **State transition**, BVA | Complex lifecycle is the main risk          |
| `OpenHABAdapter` | EP (parametrized)         | Many item types, parsing branches           |
| `config.py`      | **Decision table**, BVA   | Discriminated unions, env var logic         |
| API routes       | EP (status codes)         | Request/response validation                 |

---

## References

- [ISTQB Foundation Level Syllabus v4.0](https://www.istqb.org/) — Chapter 4: Test
  Design Techniques
- [pytest parametrize](https://docs.pytest.org/en/stable/how-to/parametrize.html)
- [ADR-006: Testing Strategy](../adr/ADR-006-testing-strategy.md)
