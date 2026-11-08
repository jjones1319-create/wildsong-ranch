#!/usr/bin/env bash
# Run a command while holding one of the PC's full-build slots (at most 2 heavy Blender builds at once).
#   tools/blender/slot.sh npm run art:ultra -- <breed> --blender > <log> 2>&1 &
# A slot is a directory under tools/blender/out/.slots/ (mkdir is atomic, so two builders can't take the
# same one). It holds the holder's pid; a slot whose holder is gone is reclaimed. The slot is freed when the
# command exits, however it exits. Waits (checking every 20 s) until a slot is free.
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DIR="$ROOT/tools/blender/out/.slots"
SLOTS="${WS_BUILD_SLOTS:-2}"
mkdir -p "$DIR"

alive() { [ -n "$1" ] && kill -0 "$1" 2>/dev/null; }

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

SLOT=""
until take "$@"; do
  echo "slot.sh: both build slots busy ($(cat "$DIR"/slot*/what 2>/dev/null | tr '\n' ';')), waiting…" >&2
  sleep 20
done
trap 'rm -rf "$SLOT"' EXIT INT TERM
echo "slot.sh: took $(basename "$SLOT") for: $*" >&2
"$@"
