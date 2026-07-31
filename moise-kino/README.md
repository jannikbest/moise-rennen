# Moise Kino

Browser display for Moise-Rennen. Opened in Chromium kiosk via `file://` (see `start-moise.sh`).

Classic `<script>` tags only — no bundler / ES modules (blocked under `file://`).

## Modes

- **Run** — public race display
- **Konfig** — password: controllers, lane mapping, cash/credit, game price
- **Debug** — password: I/O, motor/LED, serial monitor

Password: `MOISE_ADMIN_PASSWORD` in `moise-brain/.env`.
