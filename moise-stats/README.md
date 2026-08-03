# Moise Stats

Python service on the Pi: listens to the ESP race WebSocket, stores users + race
times in an encrypted DB, and serves the Kino API v4 on `:8770`.

Stats are time-based only (best time, wins, average, hourly chart). Points from
the ESP are used for the live race animation and are not recorded.

After each race the winner has `CLAIM_WINDOW_S` seconds (default 20, resets on
typing) to enter name + PIN. Unclaimed races still count toward global totals
under the mouse name.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # key is auto-generated on first run if empty
.venv/bin/python main.py
```

See `docs/kino-api.md`.
