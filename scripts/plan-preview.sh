#!/usr/bin/env bash
# Format bd children output for the fzf preview pane in plan-interactive.sh.
#
# Transforms:
#   - Strips issue type tags ([task], [bug], etc.) — redundant in epic context
#   - Strips "blocks: ..." info — irrelevant in preview context
#   - Strips parent-only "blocked by" — bd shows (blocked by: <parent>) for all
#     children, which is the parent-child link, not a real blocker
#   - Dims genuinely blocked tasks (ANSI faint) for visual de-emphasis

set -euo pipefail

if [ "$#" -lt 1 ] || [ -z "${1:-}" ]; then
  echo "Usage: $0 <epic-id>" >&2
  exit 1
fi

EPIC_ID="$1"

# --- Handle virtual "Orphaned tasks" entry -------------------------------- #
if [ "$EPIC_ID" = "_orphan" ]; then
  ORPHAN_CACHE="${TMPDIR:-/tmp}/beads-orphans-$$"
  # Re-detect orphans (cache may be stale across subshells)
  ALL_TASK_IDS=$(bd list --all --json --limit 0 2>/dev/null \
    | jq -r '.[] | select(.issue_type != "epic") | .id' | sort)
  EPIC_IDS=$(bd list --type epic --all --json 2>/dev/null | jq -r '.[].id')
  PARENTED_IDS=""
  for eid in $EPIC_IDS; do
    children=$(bd list --parent "$eid" --all --json --limit 0 2>/dev/null | jq -r '.[].id')
    [ -n "$children" ] && PARENTED_IDS="${PARENTED_IDS:+$PARENTED_IDS
}$children"
  done
  PARENTED_IDS=$(echo "$PARENTED_IDS" | sort -u)
  if [ -n "$PARENTED_IDS" ]; then
    ORPHANS=$(comm -23 <(echo "$ALL_TASK_IDS") <(echo "$PARENTED_IDS"))
  else
    ORPHANS="$ALL_TASK_IDS"
  fi

  if [ -z "$ORPHANS" ]; then
    echo "No orphaned tasks."
    exit 0
  fi

  printf "\033[31m⚠ Tasks not parented to any epic\033[0m\n\n"
  for oid in $ORPHANS; do
    info=$(bd show "$oid" --json 2>/dev/null \
      | jq -r '.[0] | "\(.status)\t\(.priority // 2)\t\(.title)"')
    status=$(echo "$info" | cut -f1)
    priority=$(echo "$info" | cut -f2)
    title=$(echo "$info" | cut -f3)
    case "$status" in
      closed)      icon="✓" ;;
      in_progress) icon="●" ;;
      *)           icon="○" ;;
    esac
    printf "%s P%s  %s  %s\n" "$icon" "$priority" "$oid" "$title"
  done
  exit 0
fi

bd children "$EPIC_ID" 2>/dev/null \
  | sed \
      -e 's/\[[a-z]*\] - //' \
      -e 's/, blocks: [^)]*//' \
      -e 's/ (blocks: [^)]*)//' \
      -e "s/ (blocked by: ${EPIC_ID})//" \
      -e "s/blocked by: ${EPIC_ID}, \([^.]\)/blocked by: \1/" \
      -e "s/blocked by: ${EPIC_ID})/blocked by:)/" \
      -e 's/ (blocked by:)//' \
      -e "s/^○ ${EPIC_ID}\./○ \./" \
      -e 's/blocked by: /← /g' \
  | sed -e ':a' -e 's/\(← [^)]*\)lh-/\1/g' -e 'ta' \
  | awk '/←/{printf "\033[2m%s\033[0m\n",$0; next} {print}'
