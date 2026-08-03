#!/bin/bash

# Moise Autostart: stats service + static Kino + Chromium kiosk
PROJECT_DIR="/home/noi/moise-rennen"

echo "Starting Moise Stats..."
cd "$PROJECT_DIR/moise-stats"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi
if [ ! -f .env ]; then
  cp .env.example .env
fi
.venv/bin/python main.py &
STATS_PID=$!

echo "Starting Kino static server..."
cd "$PROJECT_DIR/moise-kino"
python3 -m http.server 8080 &
HTTP_PID=$!

sleep 2

echo "Starting Chromium..."
chromium-browser --kiosk --disable-web-security --user-data-dir=/tmp/chrome-kiosk \
  http://localhost:8080/ &
CHROME_PID=$!

wait $CHROME_PID $STATS_PID $HTTP_PID
