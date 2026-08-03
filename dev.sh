#!/usr/bin/env bash
# Dev launcher (any OS): mock ESP + stats + Kino static server
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=moise-common.sh
. "$ROOT/moise-common.sh"

moise_ensure_stats_venv "$ROOT"

# Point stats at the local mock (override anything leftover in .env)
export ESP_WS_URL="${ESP_WS_URL:-ws://127.0.0.1:81/}"
export MOCK_CONTROL_URL="${MOCK_CONTROL_URL:-http://127.0.0.1:82/go}"

PIDS=()
cleanup() {
  local pid
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT INT TERM

"$MOISE_PY" "$ROOT/moise-kino/mock-esp.py" &
PIDS+=($!)

"$MOISE_PY" "$ROOT/moise-stats/main.py" &
PIDS+=($!)

(
  cd "$ROOT/moise-kino"
  "$(moise_python)" -m http.server 8080
) &
PIDS+=($!)

echo "Mock ESP: ws://127.0.0.1:81/   (control http://127.0.0.1:82/go)"
echo "Stats:    ws://127.0.0.1:8770/"
echo "Kino:     http://127.0.0.1:8080"
echo "Ctrl+C stops all."

wait
