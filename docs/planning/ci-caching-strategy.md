# CI Caching Strategy — Research & Options

**Beads task:** `lh-clk.4` — Research GitHub Actions caching
**Date:** 2026-02-08

---

## Current State

### Workflows

| Workflow            | File                  | Trigger                     |
| ------------------- | --------------------- | --------------------------- |
| CI                  | `ci.yml`              | push/PR on `main`           |
| Documentation       | `docs.yml`            | push/PR (docs/mkdocs paths) |
| DevContainer Build  | `devcontainer-build.yml` | `.devcontainer/**`, weekly, manual |

### CI job timings (latest run)

| Job                          | Duration | Notes                            |
| ---------------------------- | -------- | -------------------------------- |
| Detect Changes               | ~6s      | Lightweight, paths-filter        |
| Backend: Lint & Type Check   | ~2m 7s   | devcontainer pull + uv sync + lint |
| Backend: Unit Tests           | ~2m 4s   | devcontainer pull + uv sync + pytest |
| Backend: Code Complexity     | ~2m 14s  | devcontainer pull + uv sync + radon |
| Backend: Integration (Robot) | ~1m 40s  | Sequential after unit tests       |
| **Total wall-clock**         | **~4m**  | Parallel jobs + sequential Robot  |

### What's already cached

- **DevContainer image** — pushed to GHCR by `devcontainer-build.yml`, reused by all
  CI jobs via `cacheFrom`. This is the **biggest win already realized**: the
  `devcontainers/ci` action pulls pre-built image layers instead of building from
  scratch.

### What's NOT cached

- **Python dependencies (uv venv)** — every job runs `uv sync` from scratch inside the
  devcontainer. `uv` is fast (~3-5s typically), but it still downloads wheels each time.
- **GitHub Actions cache** — the repository has **0 cache entries** and **0 bytes** used.
  The `actions/cache` action is not used anywhere.
- **Pre-commit hooks** — not relevant in CI (hooks run locally).

---

## GitHub Caching Mechanisms Available

### 1. `actions/cache` (Dependency Caching)

**What it is:** General-purpose key-value cache for arbitrary paths (directories, files).
Persisted across workflow runs within branch scoping rules.

**How it works:**

- Save paths (e.g. `~/.cache/uv`, `node_modules/`) keyed by a hash of lock files
- On cache hit: restore paths, skip install → fast
- On cache miss: install normally, then save to cache at end of job
- **Scope:** branch → default branch fallback. PR caches are scoped to
  `refs/pull/.../merge`
- **Limits:** 10 GB per repo (default, configurable up to 10 TB with billing). Entries
  evicted after 7 days of no access. LRU eviction when over limit.

**Relevant for us:**

| What to cache         | Cache key                        | Path                        |
| --------------------- | -------------------------------- | --------------------------- |
| uv package cache      | `uv-${{ hashFiles('uv.lock') }}` | `~/.cache/uv`               |
| bun install cache     | `bun-${{ hashFiles('bun.lock') }}`| `~/.bun/install/cache`     |
| MkDocs build cache    | `mkdocs-${{ hashFiles('...') }}` | `site/.cache`               |

### 2. `setup-*` actions with built-in caching

**What it is:** Package-manager-specific setup actions (`setup-python`, `setup-node`)
that integrate `actions/cache` internally — one line: `cache: pip` or `cache: npm`.

**Relevant for us:** **Not applicable.** We run everything inside a devcontainer, so
`setup-python` / `setup-node` on the runner host won't help — the tools are inside the
container, not on the host.

### 3. Docker layer caching (what we already use)

**What it is:** The `devcontainers/ci` action's `cacheFrom` parameter pulls a pre-built
image from GHCR, reusing Docker layers for the Dockerfile. Our
`devcontainer-build.yml` pushes this image weekly and on `.devcontainer/**` changes.

**Current status:** ✅ Already implemented and working well.

### 4. GitHub Packages / GHCR image cache

**What it is:** Container images stored in GitHub Container Registry.

**Current status:** ✅ Already used for the devcontainer image.

### 5. Repository Cache Settings (github.com → Settings → Actions → Caches)

**What it is:** GitHub.com UI for viewing, searching, and deleting cache entries. Also
configurable storage limits.

**What you probably saw:** The **"Caches"** link under **Actions → Management** in the
repository settings sidebar on github.com. And possibly the **"Caching dependencies"**
section in the Actions documentation.

**Current status:** Empty (0 caches, 0 bytes). Nothing to configure here until we start
using `actions/cache`.

**Settings available:**

- View/delete individual cache entries by branch or key
- Increase cache storage limit beyond 10 GB default (requires billing)
- No other settings to tweak — the 10 GB default is generous for our needs

---

## Analysis: Where's the Time Going?

Each backend CI job follows this pattern:

```
Set up job          ~2s
actions/checkout    ~1s
mkdir ~/.ssh        <1s
docker/login-action ~1s
devcontainers/ci    ~1m 50s   ← THE BOTTLENECK
  ├─ Pull image     ~30-40s   (pulling GHCR layers)
  ├─ Start container ~10s
  ├─ uv sync        ~15-20s   (install Python deps from network)
  └─ Actual task    ~30-60s   (lint/test/complexity)
Post steps          ~5s
```

**Key insight:** The devcontainer image pull (~30-40s) and container startup (~10s) are
fixed costs per job. `uv` is already extremely fast, so caching Python deps saves ~10-15s
per job at best.

The **real question** is whether the complexity of adding `actions/cache` is worth the
~10-15s savings per job, given that:

1. `uv` is designed to be fast even without a cache (it downloads wheels in parallel)
2. Each job runs in an isolated devcontainer — mounting host caches into the container
   requires extra `devcontainers/ci` configuration
3. The total CI pipeline is already at ~4 minutes

---

## Options

### Option A: No Changes (Status Quo)

**What it does:** Keep the current setup. DevContainer image caching handles the big win.

**Advantages:**

- Zero complexity — nothing to maintain
- CI is already fast (~4 min wall clock)
- `uv` is designed for speed without persistent caches
- No cache invalidation bugs to debug

**Disadvantages:**

- ~10-15s wasted per job on re-downloading Python packages
- Will add up more when frontend (bun) jobs come online

**When this makes sense:** If the team is small and CI minutes aren't a concern.

### Option B: Cache uv Package Store via `actions/cache`

**What it does:** Add `actions/cache` before the `devcontainers/ci` step to cache uv's
download cache, then mount it into the devcontainer.

**Implementation sketch:**

```yaml
- name: Cache uv packages
  uses: actions/cache@v4
  with:
    path: /tmp/uv-cache
    key: uv-${{ hashFiles('packages/backend/uv.lock') }}
    restore-keys: uv-

- name: Run inside devcontainer
  uses: devcontainers/ci@v0.3
  with:
    cacheFrom: ${{ env.DEVCONTAINER_IMAGE }}
    push: never
    # Mount the host cache into the container
    runCmd: |
      export UV_CACHE_DIR=/tmp/uv-cache
      task ci:test:unit:be
```

**Problem:** The `devcontainers/ci` action doesn't support arbitrary volume mounts. The
`runCmd` executes inside the container, and `/tmp/uv-cache` on the *host* isn't visible
inside. We'd need to either:

1. Use the `env` input to pass the cache path + hope the workspace mount covers it
2. Add a `mounts` entry in `devcontainer.json` (but this changes local dev too)
3. Pre-populate the workspace-mounted path before container start

**Feasibility:** Medium. The workspace is bind-mounted at `/workspace`, so we could cache
to a path inside the workspace:

```yaml
- name: Cache uv packages
  uses: actions/cache@v4
  with:
    path: .uv-cache
    key: uv-${{ hashFiles('packages/backend/uv.lock') }}
    restore-keys: uv-

# The devcontainer bind-mounts the workspace, so .uv-cache is visible inside
- name: Run inside devcontainer
  uses: devcontainers/ci@v0.3
  with:
    cacheFrom: ${{ env.DEVCONTAINER_IMAGE }}
    push: never
    runCmd: |
      export UV_CACHE_DIR=/workspace/.uv-cache
      task ci:lint:be
```

**Advantages:**

- Saves ~10-15s per job on dependency downloads
- Across 4 parallel backend jobs: ~40-60s total saved
- Clean cache invalidation via `uv.lock` hash
- Pattern ready for bun cache when frontend arrives

**Disadvantages:**

- Adds 3-4 lines per job (manageable with a composite action or YAML anchor)
- Cache is in the workspace dir — needs `.gitignore` entry
- `actions/cache` save/restore adds ~5-8s overhead — might eat into the savings
- If uv.lock changes frequently, cache misses negate the benefit

**Estimated net savings:** ~5-10s per job after cache overhead. Modest.

### Option C: Composite Action to DRY Up Boilerplate

**What it does:** Extract the repeated devcontainer setup pattern (checkout → mkdir →
login → devcontainers/ci) into a local composite action, optionally adding caching.

**Advantages:**

- Eliminates the ~20 lines of boilerplate repeated 5× in `ci.yml`
- Single place to add caching logic later
- Easier to maintain when frontend jobs come online

**Disadvantages:**

- Composite actions have limitations (no `if:` on steps, limited `outputs`)
- More indirection — harder to read the workflow at a glance
- Premature abstraction if the pattern is still evolving

### Option D: Pre-install Dependencies in DevContainer Image

**What it does:** Modify the Dockerfile to include `uv sync` so Python deps are baked
into the image. CI jobs skip the install step entirely.

**Implementation:**

```dockerfile
# In .devcontainer/Dockerfile
COPY packages/backend/pyproject.toml packages/backend/uv.lock /workspace/packages/backend/
RUN cd /workspace/packages/backend && uv sync --group dev
```

**Advantages:**

- Eliminates `uv sync` entirely in CI — 0s dependency install
- Dependencies change less often than code, so image rebuilds are rare
- Already have `devcontainer-build.yml` handling the rebuild pipeline

**Disadvantages:**

- **Couples lockfile to image** — every `uv.lock` change requires a devcontainer rebuild
  before CI can use the new deps. This breaks the "push and go" workflow.
- Image size increases (includes all wheels)
- Complicates local development if deps drift between image and lockfile
- Weekly rebuild might use stale deps for up to 7 days

**This is an anti-pattern** for a project with evolving dependencies. Best suited for
stable, production-focused images.

---

## Recommendation

**Option A (Status Quo)** for now, with **Option B prepared** for when the frontend
arrives.

### Rationale

1. **The big caching win is already in place.** The devcontainer image cache means we're
   not building a Dockerfile from scratch on every run. That saves 3-5 minutes per job.

2. **`uv` is intentionally fast.** It parallelizes downloads and resolves from a lockfile.
   The difference between cached and uncached `uv sync` is ~10-15s. After subtracting
   `actions/cache` overhead (~5-8s for save/restore), the net saving is marginal.

3. **Complexity vs benefit.** Adding caching to 5 jobs means 5× more YAML to maintain,
   debug cache misses, handle eviction edge cases. Not worth ~5-10s per job.

4. **The real savings come with the frontend.** When Phase 3 adds `bun install` (which
   downloads a `node_modules` tree that's typically 100-500MB), caching becomes
   essential. At that point, Option B + C (composite action with caching) will be high
   value.

### GitHub.com Settings

**No changes needed now:**

- The 10 GB cache limit is more than enough (we're at 0 bytes)
- Cache viewing/management UI becomes useful once we have cache entries
- No repository-level Actions settings to toggle for caching — it's all workflow-driven

### When to Revisit

- **Phase 3 frontend work** — bun's `node_modules` will absolutely benefit from caching
- **If CI exceeds 5 minutes** — reassess whether uv caching is worth the complexity
- **If multiple contributors push frequently** — cache thrashing on PR branches may need
  the cleanup workflow from the GitHub docs

---

## Summary

| Mechanism                    | Status          | Action Needed     |
| ---------------------------- | --------------- | ----------------- |
| DevContainer image (GHCR)   | ✅ Implemented  | None              |
| `actions/cache` for uv      | Not used        | Defer to Phase 3  |
| `actions/cache` for bun     | Not applicable  | Add in Phase 3    |
| `setup-python` / `setup-node`| Not applicable | N/A (devcontainer)|
| Cache settings on github.com| Default (10 GB) | None              |
| PR cache cleanup workflow   | Not needed      | Add if thrashing  |

## Next Steps

1. Close `lh-clk.4` with findings documented here
2. Create a gate task on the Phase 3 epic to add caching when frontend jobs are enabled
3. Consider Option C (composite action) as a separate improvement task — the DRY benefit
   is independent of caching
