#!/usr/bin/env bash
# Production launcher (any OS): stats + Kino static server — real ESP, no mock
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=moise-common.sh
. "$ROOT/moise-common.sh"

moise_ensure_stats_venv "$ROOT"

# Never expose the mock control button in production
export MOCK_CONTROL_URL=""

PIDS=()
cleanup() {
  local pid
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT INT TERM

"$MOISE_PY" "$ROOT/moise-stats/main.py" &
PIDS+=($!)

(
  cd "$ROOT/moise-kino"
  "$(moise_python)" -m http.server 8080
) &
PIDS+=($!)

echo "Stats: ws://0.0.0.0:8770/"
echo "ESP:   ESP_WS_URL from moise-stats/.env (IP or host, e.g. 192.168.4.1)"
echo "Kino:  http://127.0.0.1:8080"
echo "Ctrl+C stops all."

wait
