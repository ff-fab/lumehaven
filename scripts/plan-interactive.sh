#!/usr/bin/env bash
# Interactive epic browser using fzf with adaptive preview pane.
# Called by: task plan:ui
#
# Shows all epics (phases) with colored progress bars in an fzf picker.
# Preview pane displays the children (backlog) of the highlighted epic.
#
# Layout adapts to terminal width:
#   ≥120 cols  → preview on the right (60%)
#   80–119     → preview below (50%)
#   <80        → preview hidden (toggle with ?)
#
# Keybindings:
#   Enter  → show selected epic's backlog (children) and exit
#   Esc    → exit without selection
#   ?      → toggle preview pane

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- Guard: fzf required -------------------------------------------------- #
if ! command -v fzf &>/dev/null; then
  echo "fzf is required for interactive mode." >&2
  echo "Install: apt install fzf" >&2
  echo "Use 'task plan' for non-interactive overview." >&2
  exit 1
fi

# --- Data fetch ------------------------------------------------------------ #
BAR_WIDTH=20

EPIC_STATUS=$(bd epic status --json 2>/dev/null)

ALL_EPICS=$(bd list --type epic --all --json 2>/dev/null \
  | jq -r 'sort_by(.title) | .[] | [.id, .status, .title] | @tsv')

if [ -z "$ALL_EPICS" ]; then
  echo "No epics found." >&2
  exit 1
fi

# --- Build fzf input lines ------------------------------------------------ #
# Each line: <epic_id>  <bullet> <title_padded> <bar> <pct>% (<closed>/<total>)
# The epic_id as first token lets fzf's {1} extract it for preview.

# Calculate max title width for aligned columns
MAX_TITLE=0
while IFS=$'\t' read -r _ _ title; do
  len=${#title}
  (( len > MAX_TITLE )) && MAX_TITLE=$len
done <<< "$ALL_EPICS"

FZF_LINES=""
while IFS=$'\t' read -r id status title; do
  if [ "$status" = "closed" ]; then
    total=$(bd list --parent "$id" --all --json --limit 0 2>/dev/null | jq 'length')
    closed=$total
  else
    total=$(echo "$EPIC_STATUS" | jq -r --arg id "$id" \
      '.[] | select(.epic.id == $id) | .total_children // 0')
    closed=$(echo "$EPIC_STATUS" | jq -r --arg id "$id" \
      '.[] | select(.epic.id == $id) | .closed_children // 0')
  fi

  # Normalize empty/null to 0 for safe arithmetic
  total=${total:-0}; [ "$total" = "null" ] && total=0
  closed=${closed:-0}; [ "$closed" = "null" ] && closed=0

  # Calculate bar segments and percentage
  if [ "$total" -gt 0 ] 2>/dev/null; then
    filled=$(( closed * BAR_WIDTH / total ))
    empty=$(( BAR_WIDTH - filled ))
    pct=$(( closed * 100 / total ))
  else
    filled=0; empty=$BAR_WIDTH; pct=0
  fi

  # Build bar characters
  bar_fill=""; bar_empty=""
  for ((i=0; i<filled; i++)); do bar_fill+="█"; done
  for ((i=0; i<empty; i++)); do bar_empty+="░"; done

  # Color scheme: green=done, yellow=in-progress, dim=not started
  if [ "$pct" -eq 100 ]; then
    bullet="\033[32m●\033[0m"
    bar="\033[32m${bar_fill}\033[0m"
  elif [ "$pct" -gt 0 ]; then
    bullet="\033[33m○\033[0m"
    bar="\033[33m${bar_fill}\033[2m${bar_empty}\033[0m"
  else
    bullet="\033[2m○\033[0m"
    bar="\033[2m${bar_empty}\033[0m"
  fi

  line=$(printf "%-8s  %b  %-${MAX_TITLE}s  %b  %3d%%  (%d/%d)" \
    "$id" "$bullet" "$title" "$bar" "$pct" "$closed" "$total")

  if [ -z "$FZF_LINES" ]; then
    FZF_LINES="$line"
  else
    FZF_LINES="${FZF_LINES}"$'\n'"${line}"
  fi
done <<< "$ALL_EPICS"

# --- Launch fzf ----------------------------------------------------------- #
# Adaptive preview layout based on terminal width.
# {1} extracts the epic ID (first whitespace-delimited token) for the preview.
SELECTED=$(echo -e "$FZF_LINES" \
  | fzf \
      --ansi \
      --no-sort \
      --cycle \
      --header 'Enter: drill in │ Esc: quit │ ?: toggle preview' \
      --preview "bash \"$SCRIPT_DIR/plan-preview.sh\" {1}" \
      --preview-window 'right,60%,border-left,wrap,<120(down,50%,border-top,wrap),<80(hidden)' \
      --bind '?:toggle-preview,left:up,right:down' \
  || true)

# --- Output --------------------------------------------------------------- #
# Show the full children backlog for the selected epic (same as task plan:phase).
if [ -n "$SELECTED" ]; then
  EPIC_ID=$(echo "$SELECTED" | awk '{print $1}')
  TITLE=$(bd show "$EPIC_ID" --json 2>/dev/null | jq -r '.[0].title')
  echo ""
  echo "$TITLE ($EPIC_ID)"
  echo "─────────────────────────────────────────"
  bd children "$EPIC_ID"
fi
