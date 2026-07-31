#!/bin/bash

# Moise Autostart Script - Nur Chromium
PROJECT_DIR="/home/noi/moise-rennen"

echo "Starting Chromium with Kino..."
cd $PROJECT_DIR/moise-kino
chromium-browser --kiosk --disable-web-security --user-data-dir=/tmp/chrome-kiosk file://$PROJECT_DIR/moise-kino/index.html &
CHROME_PID=$!

echo "Starting Moise Brain..."
cd $PROJECT_DIR/moise-brain
python3 main.py &
BRAIN_PID=$!

# Warte auf beide Prozesse
wait $CHROME_PID $BRAIN_PID
