#!/usr/bin/env bash
# Pi / kiosk: production stack (stats + Kino) + fullscreen Chromium
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=moise-common.sh
. "$ROOT/moise-common.sh"

moise_ensure_stats_venv "$ROOT"
export MOCK_CONTROL_URL=""

# Wait for a graphical display (autostart often races the desktop)
export DISPLAY="${DISPLAY:-:0}"
moise_wait_for_display 60 || echo "No display yet — continuing without browser wait" >&2

PIDS=()
cleanup() {
  local pid
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Starting Moise Stats…"
"$MOISE_PY" "$ROOT/moise-stats/main.py" &
PIDS+=($!)

echo "Starting Kino static server…"
(
  cd "$ROOT/moise-kino"
  "$(moise_python)" -m http.server 8080 --bind 127.0.0.1
) &
PIDS+=($!)

sleep 2

if pid="$(moise_open_kiosk http://127.0.0.1:8080/)"; then
  PIDS+=("$pid")
fi

echo "Stats: ws://127.0.0.1:8770/"
echo "Kino:  http://127.0.0.1:8080"
wait
