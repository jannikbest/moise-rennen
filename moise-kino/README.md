# Moise Kino

Browser display for Moise Race. Connects to the stats service (Kino API v4 —
see `docs/kino-api.md`). Classic `<script>` tags only. UI language: English.

## Screens

- Idle (`homing` / `ready` / `config`): Moise image + rotating time-based stats;
  **Leaderboard** button (top-right) opens the full table
- `race`: live points drive the mice; clock shows duration
- `win` / result: winner + time, then a 20 s claim window for name + PIN
- `error` / offline

There is no login before a race. Only the winner can claim a place on the
leaderboard after the finish.

## Local development

```bash
./dev-mac.sh
```

Opens mock ESP (`:81` + control `:82`), stats service (`:8770`), and Kino on
`http://localhost:8080`.

In test mode the mock stays on **ready** until you click **Start race**
(top-left). Or: `curl -X POST http://localhost:82/go`
