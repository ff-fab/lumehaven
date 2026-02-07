# CI Integration Tests — Subprocess-based Mock Infrastructure

## Context

Integration tests (Robot Framework) currently run **locally only** — they start mock
OpenHAB and Lumehaven backend as subprocess-spawned uvicorn servers
(`ServerKeywords.py`). This works because locally the devcontainer already has all
Python dependencies installed and ports are freely available.

In CI, the `devcontainers/ci@v0.3` action runs commands **inside a devcontainer**. This
creates a challenge: we need two long-running servers (mock OpenHAB on `:8081`,
Lumehaven on `:8000`) plus the Robot Framework test runner, all coordinated. The current
subprocess approach _should_ work inside the devcontainer since Python, uvicorn, and all
dependencies are available. But there's a design choice about whether to use Docker
Compose for better isolation and CI parity.

### What the integration tests do

1. `ServerKeywords.py` starts **mock OpenHAB** (FastAPI on `:8081`) using fixture data
2. `ServerKeywords.py` starts **Lumehaven backend** (FastAPI on `:8000`) pointing at
   mock
3. Robot Framework runs API tests, SSE stream tests, and error handling tests
4. `ServerKeywords.py` stops both servers in suite teardown

### Current test files

| File                   | Tests                                     |
| ---------------------- | ----------------------------------------- |
| `api_tests.robot`      | REST endpoints: health, signals, metrics  |
| `sse_tests.robot`      | SSE stream: connection, real-time updates |
| `error_handling.robot` | Failure scenarios, recovery, 404s         |

---

## Option A: Run Subprocess Servers Inside Devcontainer (Minimal Change)

**What it does:** Keep the existing `ServerKeywords.py` subprocess approach. The
`devcontainers/ci` action runs `task ci:test:integration:be` inside the devcontainer,
which calls `robot tests/integration/`. Robot Framework's suite setup starts mock
OpenHAB + Lumehaven as subprocesses, runs tests, then tears down.

**Implementation:**

```yaml
# Taskfile.yml — new task
ci:test:integration:be:
  dir: packages/backend
  cmds:
    - uv run robot --outputdir . --xunit results-integration.xml tests/integration/
```

```yaml
# ci.yml — integration-tests-be job
- name: Run integration tests inside devcontainer
  uses: devcontainers/ci@v0.3
  with:
    cacheFrom: ${{ env.DEVCONTAINER_IMAGE }}
    push: never
    runCmd: task ci:test:integration:be
```

**Why this approach:**

- **Zero infrastructure change** — uses existing `ServerKeywords.py` as-is
- **Identical local/CI behavior** — same code paths, same process model
- **No Docker-in-Docker complexity** — avoids `docker compose` inside devcontainer
- **Fast** — no container startup overhead beyond the devcontainer itself

**Trade-offs:**

- Subprocess lifecycle tied to Robot Framework process — if RF crashes, servers become
  orphans (mitigated by CI job timeout)
- No network isolation between mock and backend (both on localhost)
- If future integration tests need external services (database, message queue), this
  approach doesn't scale

**Tooling note:** Docker-in-Docker (`docker-in-docker` feature) is already installed in
the devcontainer — so Docker _is_ available if we need it later.

---

## Option B: Docker Compose for Mock Infrastructure

**What it does:** Define a `docker-compose.integration.yml` with mock OpenHAB as a
container service. Lumehaven backend either runs as a second service or stays as a
subprocess (hybrid). Robot Framework runs as the entrypoint/test command.

**Implementation:**

```yaml
# docker-compose.integration.yml
services:
  mock-openhab:
    build:
      context: packages/backend
      dockerfile: tests/integration/Dockerfile.mock-openhab
    ports:
      - '8081:8081'
    healthcheck:
      test: ['CMD', 'curl', '-f', 'http://localhost:8081/rest/items']
      interval: 2s
      timeout: 5s
      retries: 5

  lumehaven:
    build:
      context: packages/backend
      dockerfile: Dockerfile # or reuse devcontainer
    environment:
      - OPENHAB_URL=http://mock-openhab:8081
    ports:
      - '8000:8000'
    depends_on:
      mock-openhab:
        condition: service_healthy

  tests:
    build:
      context: packages/backend
      dockerfile: Dockerfile.test
    depends_on:
      - lumehaven
    command: robot tests/integration/
```

**Why this approach:**

- **True network isolation** — services communicate via Docker network, closer to
  production
- **Health checks and dependency ordering** — Compose handles startup order
- **Reusable for Phase 4** — E2E tests with frontend can reuse the same Compose setup
- **Standard pattern** — commonly used for CI integration testing

**Trade-offs:**

- **Significant complexity increase** — 2-3 Dockerfiles, Compose file, build contexts
- **Duplicated Python environment** — mock and backend need separate images (or shared
  base)
- **Docker-in-Docker penalty** — building images inside devcontainer is slow in CI
- **Divergence from local dev** — locally we run subprocesses, CI uses Compose
  (different code paths)
- **ServerKeywords.py becomes dead code** in CI (still used locally)

---

## Option C: Hybrid — Subprocess Now, Compose Later (Recommended)

**What it does:** Ship Option A now to unblock integration tests in CI. Document the
Compose approach as a future milestone for Phase 4 / E2E tests when real infrastructure
complexity justifies it.

**Why this approach:**

- **Ship fast** — minimal changes, integration tests run in CI today
- **Validate first** — confirm subprocess approach works in devcontainer before
  investing in Compose
- **Right-size the investment** — Docker Compose makes sense when we have 3+ services
  (mock OpenHAB, Lumehaven, frontend, maybe a database). For 2 Python subprocesses, it's
  overhead.
- **YAGNI** — we can always add Compose later; removing it later is harder

**Implementation is identical to Option A**, with the addition of a Taskfile task and CI
job. The roadmap item "Docker Compose CI mock infra" gets reframed as "Integration tests
in CI" (done now) + "Docker Compose infrastructure" (Phase 4).

**Trade-offs:**

- Same subprocess limitations as Option A
- Roadmap item was specifically about Docker Compose, so this is a scope adjustment

---

## Recommendation

**Option C (Hybrid)** — the existing mock server and `ServerKeywords.py` are well-built
and complete. They start/stop cleanly, handle healthchecks, and reset state between
tests. Adding Docker Compose layers on top provides no concrete benefit right now — it
only adds Dockerfiles, build time, and divergence from local dev.

Ship the subprocess approach in CI. Revisit Compose when Phase 4 (E2E with frontend +
backend + mock) justifies the orchestration complexity.

## Outcome

**Option C (Hybrid)** was adopted. The subprocess-based integration tests now run in CI
via PR #40. All 18 tests (API, SSE, error handling) pass inside the devcontainer.

What was implemented:

- `ci:test:integration:be` Taskfile task with `--outputdir` and `--xunit` flags
- `integration-tests-be` CI job gated behind `unit-tests-be` (test pyramid)
- Robot Framework reports + server logs uploaded as CI artifacts
- Roadmap updated: Phase 2 item ✅, Docker Compose deferred to Phase 4

## Remaining Work (Phase 4)

1. Revisit Docker Compose infrastructure when E2E tests (frontend + backend + mock)
   justify the orchestration complexity
2. If Docker Compose is adopted, capture the decision in a new ADR
