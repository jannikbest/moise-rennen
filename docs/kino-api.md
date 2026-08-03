# Kino API

Two layers: ESP → Stats (v3), Stats → Kino (v4).

## ESP → Stats (v3)

| | |
|---|---|
| ESP SoftAP SSID | `moise-rennen` |
| ESP SoftAP IP | `192.168.4.1` |
| WebSocket URL | `ws://192.168.4.1:81/` |
| Direction | ESP → clients only |

### Snapshot

```json
{
  "seq": 128,
  "state": "race",
  "maxPoints": 15,
  "winner": 2,
  "raceId": 12,
  "durationMs": 8120,
  "lanes": [
    { "id": 1, "points": 7 },
    { "id": 2, "points": 15 }
  ]
}
```

| Field | Meaning |
|---|---|
| `seq` | Monotonic counter |
| `state` | `config` \| `homing` \| `ready` \| `race` \| `win` \| `error` |
| `maxPoints` | Display clamp (15) — live race animation only |
| `winner` | Winning lane id in `win`, else `0` |
| `raceId` | Increments each race start |
| `durationMs` | Elapsed ms while racing; frozen at end in `win` |
| `lanes[].points` | Live points for the track animation only (not stored in stats) |

Push on change + 1 s heartbeat.

## Stats → Kino (v4)

| | |
|---|---|
| WebSocket URL | `ws://localhost:8770/` |
| Direction | Stats pushes snapshots; Kino may send claim / sim_start |

### Broadcast

```json
{
  "seq": 128,
  "state": "ready",
  "phase": "idle",
  "maxPoints": 15,
  "winner": 0,
  "raceId": 12,
  "durationMs": 0,
  "espConnected": true,
  "lanes": [
    { "id": 1, "points": 0, "label": "Speedy" },
    { "id": 2, "points": 0, "label": "Pilzy" }
  ],
  "stats": {
    "cards": [ { "id": "overview", "title": "…", "lines": ["…"] } ],
    "detail": [ { "title": "Beste Zeiten", "kind": "list", "rows": [] } ]
  }
}
```

- `label` is the default mouse name (or the claimed winner name on the result screen).
- `stats` is included in phase `idle` and when offline. Cards rotate on idle screens; `detail` feeds the full leaderboard overlay.
- Stats are **time-based only**. Points from the ESP are never stored.

### Session phases

| `phase` | Meaning |
|---|---|
| `idle` | Waiting / homing / ready — no login |
| `racing` | Race in progress |
| `result` | Race recorded; winner claim window open (or short confirm) |
| `offline` | No ESP snapshot for 5 s |

Lifecycle:

- `racing` → `result`: race is saved immediately with `user: null` and `durationMs`. A claim window opens for `CLAIM_WINDOW_S` (default 20).
- The claim window lives in the stats service. The ESP may already return to `homing`/`ready` while the Kino still shows `state: "win"` / `phase: "result"`.
- Typing (`claim_typing`) resets the deadline to now + `CLAIM_WINDOW_S`.
- After a successful claim the window stays for ~6 s with a confirmation message, then the phase follows the ESP again.
- A new race discards any open claim. An aborted race (racing → anything but result) records nothing.

`claim` (while open or confirming):

```json
{
  "open": true,
  "secondsLeft": 17,
  "claimed": false,
  "winnerLane": 2,
  "label": "Pilzy",
  "user": null
}
```

`lastResult` (phase `result`):

```json
{
  "raceId": 42,
  "winnerLane": 2,
  "winner": "Pilzy",
  "user": null,
  "durationMs": 8120,
  "message": "Want on the leaderboard and in the big final? Enter your name and PIN now — remember your PIN!"
}
```

After claim, `user` / `winner` become the display name and `message` is e.g. `"Saved! · rank 3 on best times · 5 wins"`.

### Client actions

```json
{ "action": "claim", "request_id": "r1", "name": "alice", "pin": "1234" }
{ "action": "claim_typing", "request_id": "r2" }
```

Reply: `{ "ok": true|false, "request_id": "r1", "error": "wrong_pin|invalid|rate_limited|no_claim|expired|already_claimed", "data": {…} }`.

- New name + 4-digit PIN → register.
- Existing name → PIN must match (scrypt hash in encrypted DB).
- Rate limit: 5 wrong PINs per name per minute.
- Dev only: `{ "action": "sim_start" }` triggers the mock ESP one-shot race (`MOCK_CONTROL_URL`). Broadcast includes `"testMode": true` when configured.

### Storage

Encrypted file `moise-stats/data/moise.db.enc` (Fernet). Key in `moise-stats/.env` as `MOISE_STATS_KEY`.

Race record:

```json
{ "id": 7, "espRaceId": 3, "ts": 1750000000, "durationMs": 8120, "winnerLane": 2, "user": null }
```

Each race gets a consecutive `id` from the store; the ESP counter is kept as `espRaceId` because it restarts at 1 after every controller reboot. `user` is filled in later via claim.
