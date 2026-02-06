"""Module-level coverage threshold configuration (single source of truth).

This module defines risk-based coverage thresholds enforced at the directory
(module) level.  Both the pytest session-finish hook (``conftest.py``) and
the standalone CLI script (``scripts/check_coverage_thresholds.py``) import
from here — **do not duplicate these definitions elsewhere**.

Threshold semantics
-------------------
* Files are grouped by directory prefix (longest match wins).
* Coverage is aggregated per group as a **weighted average** — each file
  contributes proportional to its statement / branch count.
* A wildcard key like ``adapters/*`` matches any immediate subdirectory
  (``adapters/openhab/``, ``adapters/homeassistant/``, …) so new adapter
  implementations inherit the correct risk level without an explicit entry.
* Single-file modules (e.g. ``config``) match ``config.py`` at the package
  root.
* ``__root__`` is the fallback for files not matched by any other key.

See ``docs/testing/03-coverage-strategy.md`` for rationale.
"""

from __future__ import annotations

# =============================================================================
# Module-Level Risk Thresholds
# =============================================================================
# Format: "module_key": (line_threshold, branch_threshold)

MODULE_THRESHOLDS: dict[str, tuple[int, int]] = {
    # High risk — adapter framework (lifecycle manager, protocol, factory)
    "adapters": (85, 80),
    # Critical risk — any adapter implementation (auto-discovered)
    "adapters/*": (90, 85),
    # High risk
    "config": (85, 80),
    "state": (85, 80),
    # Medium risk — thin REST / SSE layer
    "api": (80, 75),
    # Low risk — simple models, exceptions
    "core": (80, 70),
    # Low risk — package init, version resolution only
    "__root__": (30, 0),
}


# =============================================================================
# Helper Functions
# =============================================================================


def normalize_path(filepath: str) -> str:
    """Extract path relative to ``lumehaven/`` from a coverage filepath.

    >>> normalize_path("src/lumehaven/adapters/openhab/adapter.py")
    'adapters/openhab/adapter.py'
    """
    for prefix in ("src/lumehaven/", "lumehaven/"):
        if prefix in filepath:
            return filepath.split(prefix)[-1]
    return filepath


def get_module_for_file(normalized_path: str) -> str:
    """Determine which module a file belongs to.

    Matching rules (evaluated together, longest concrete match wins):

    1. **Exact key + "/"** — ``adapters/`` matches ``adapters/manager.py``
    2. **Single-file key + ".py"** — ``config`` matches ``config.py``
    3. **Wildcard ``key/*``** — ``adapters/*`` matches any
       ``adapters/<name>/…`` subdirectory *unless* a more-specific concrete
       key also matches.
    4. **Fallback** — ``__root__``

    >>> get_module_for_file("adapters/openhab/adapter.py")
    'adapters/openhab'
    >>> get_module_for_file("adapters/manager.py")
    'adapters'
    >>> get_module_for_file("config.py")
    'config'
    """
    best_match = "__root__"
    best_len = 0

    for module_key in MODULE_THRESHOLDS:
        if module_key == "__root__":
            continue

        if module_key.endswith("/*"):
            # Wildcard: "adapters/*" matches "adapters/<subdir>/..."
            # but NOT "adapters/manager.py" (direct child file).
            base = module_key[:-2]  # strip "/*"
            # Must start with base + "/" and have another "/" after the subdir
            rest = normalized_path.removeprefix(base + "/")
            if rest != normalized_path and "/" in rest:
                # Resolve the concrete subdir name for the match key
                subdir = rest.split("/", 1)[0]
                effective_key = f"{base}/{subdir}"
                effective_len = len(effective_key)
                if effective_len > best_len:
                    best_match = module_key
                    best_len = effective_len
        else:
            # Concrete match: directory prefix or single-file module
            is_dir_match = normalized_path.startswith(module_key + "/")
            is_file_match = normalized_path == module_key + ".py"
            if (is_dir_match or is_file_match) and len(module_key) > best_len:
                best_match = module_key
                best_len = len(module_key)

    return best_match


def get_threshold(module_key: str) -> tuple[int, int]:
    """Return ``(line_threshold, branch_threshold)`` for a module key.

    Falls back to ``__root__`` for unknown keys.
    """
    return MODULE_THRESHOLDS.get(module_key, MODULE_THRESHOLDS["__root__"])
