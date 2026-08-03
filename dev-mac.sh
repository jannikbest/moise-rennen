#!/usr/bin/env bash
# Local Mac/dev launcher: mock ESP + stats service + kino static server
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

STATS_VENV="$ROOT/moise-stats/.venv"
if [ ! -d "$STATS_VENV" ]; then
  python3 -m venv "$STATS_VENV"
  "$STATS_VENV/bin/pip" install -r "$ROOT/moise-stats/requirements.txt"
fi

# Ensure .env exists (main.py also generates a key if missing)
if [ ! -f "$ROOT/moise-stats/.env" ]; then
  cp "$ROOT/moise-stats/.env.example" "$ROOT/moise-stats/.env"
fi

"$STATS_VENV/bin/python" "$ROOT/moise-kino/mock-esp.py" &
MOCK_PID=$!

"$STATS_VENV/bin/python" "$ROOT/moise-stats/main.py" &
STATS_PID=$!

cd "$ROOT/moise-kino"
python3 -m http.server 8080 &
KINO_PID=$!

echo "Mock ESP: ws://localhost:81/     (pid $MOCK_PID)"
echo "Stats:    ws://localhost:8770/   (pid $STATS_PID)"
echo "Kino:     http://localhost:8080  (pid $KINO_PID)"
echo "Ctrl+C stops all."

trap 'kill $MOCK_PID $STATS_PID $KINO_PID 2>/dev/null' EXIT
wait
