#!/usr/bin/env bash
# Local Mac/dev launcher: brain + kino static server
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/moise-brain"

if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi
[ -f .env ] || cp .env.example .env

.venv/bin/python main.py &
BRAIN_PID=$!

cd "$ROOT/moise-kino"
python3 -m http.server 8080 &
KINO_PID=$!

echo "Brain: ws://localhost:8765  (pid $BRAIN_PID)"
echo "Kino:  http://localhost:8080  (pid $KINO_PID)"
echo "Admin password: see moise-brain/.env (default: moise)"
echo "Ctrl+C stops both."

trap 'kill $BRAIN_PID $KINO_PID 2>/dev/null' EXIT
wait
