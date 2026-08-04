#!/usr/bin/env bash
# Production launcher (any OS): stats + Kino + local fullscreen browser — real ESP, no mock
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=moise-common.sh
. "$ROOT/moise-common.sh"

moise_ensure_stats_venv "$ROOT"

# Drop leftovers from a previous Ctrl+C that didn't clean up
for port in 8080 8770; do
  pids="$(lsof -nP -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  if [ -n "$pids" ]; then
    echo "Freeing port $port (pid $pids)"
    # shellcheck disable=SC2086
    kill $pids 2>/dev/null || true
    sleep 0.4
  fi
done

# Never expose the mock control button in production
export MOCK_CONTROL_URL=""

PIDS=()
cleanup() {
  local pid
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

"$MOISE_PY" "$ROOT/moise-stats/main.py" &
PIDS+=($!)

(
  cd "$ROOT/moise-kino"
  "$(moise_python)" -m http.server 8080 --bind 127.0.0.1
) &
PIDS+=($!)

sleep 2

if pid="$(moise_open_kiosk http://127.0.0.1:8080/)"; then
  PIDS+=("$pid")
fi

echo "Stats: ws://0.0.0.0:8770/"
echo "ESP:   ESP_WS_URL from moise-stats/.env (auto = UDP discover, or fixed IP)"
echo "Kino:  http://127.0.0.1:8080 (fullscreen)"
echo "Ctrl+C stops all."

wait
