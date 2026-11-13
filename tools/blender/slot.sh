#!/usr/bin/env bash
# Run a command while holding one of the PC's full-build slots (at most 2 heavy Blender builds at once).
#   tools/blender/slot.sh npm run art:ultra -- <breed> --blender > <log> 2>&1 &
# A slot is a directory under tools/blender/out/.slots/ (mkdir is atomic, so two builders can't take the
# same one). It holds the holder's pid; a slot whose holder is gone is reclaimed. The slot is freed when the
# command exits, however it exits.
# First come, first served (Nov 13: a waiter once starved for 10 hours): each waiter takes a ticket in
# .slots/queue/ named by its start time, and only the oldest live ticket may take a free slot. A dead
# waiter's ticket is cleared. Waits (checking every 20 s) until it is first in line and a slot is free.
# Don't edit this file while builds are waiting in it: bash reads scripts as it runs them.
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DIR="$ROOT/tools/blender/out/.slots"
Q="$DIR/queue"
SLOTS="${WS_BUILD_SLOTS:-2}"
mkdir -p "$DIR" "$Q"

alive() { [ -n "$1" ] && kill -0 "$1" 2>/dev/null; }

TICKET_NAME="$(date +%s%N)-$$"
TICKET="$Q/$TICKET_NAME"
echo "$*" > "$TICKET"
SLOT=""
trap 'rm -f "$TICKET"; [ -n "$SLOT" ] && rm -rf "$SLOT"' EXIT INT TERM

# 0 when this waiter's ticket is the oldest live one; clears dead waiters' tickets on the way
first_in_line() {
  local t pid
  for t in $(ls -1 "$Q" 2>/dev/null | sort); do
    [ "$t" = "$TICKET_NAME" ] && return 0
    pid="${t##*-}"
    if alive "$pid"; then return 1; fi
    rm -f "$Q/$t"
  done
  return 1
}

take() {
  local i
  for i in $(seq 1 "$SLOTS"); do
    local s="$DIR/slot$i"
    if [ -d "$s" ] && ! alive "$(cat "$s/pid" 2>/dev/null)"; then
      rm -rf "$s" 2>/dev/null # its holder is gone: reclaim it
    fi
    if mkdir "$s" 2>/dev/null; then
      echo "$$" > "$s/pid"
      echo "$*" > "$s/what"
      SLOT="$s"
      return 0
    fi
  done
  return 1
}

until first_in_line && take "$@"; do
  ahead=$(ls -1 "$Q" 2>/dev/null | sort | awk -v me="$TICKET_NAME" '$0 == me { exit } { n++ } END { print n + 0 }')
  echo "slot.sh: waiting (${ahead} ahead; busy: $(cat "$DIR"/slot*/what 2>/dev/null | tr '\n' ';'))…" >&2
  sleep 20
done
rm -f "$TICKET"
echo "slot.sh: took $(basename "$SLOT") for: $*" >&2
"$@"
