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

EPIC_ID="$1"

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
