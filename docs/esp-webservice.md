# ESP WebSocket API (v3)

Contract for the race controller. Consumer: `moise-stats` (`ESP_WS_URL`).
Kino never talks to the ESP.

## Endpoint

| | |
|---|---|
| URL | `ws://moise-rennen.local:81/` |
| Direction | ESP → clients only (push) |
| Frames | text, one JSON object per frame |
| Auth | none |

Reachable under a stable DNS name (`moise-rennen.local`), not by hardcoding an IP.
How Wi-Fi / SoftAP / mDNS is set up is the controller's business — as long as that URL works for a client on the same network.

## Snapshot

```json
{
  "seq": 128,
  "state": "race",
  "winner": 2,
  "raceId": 12,
  "durationMs": 8120,
  "lanes": [
    { "id": 1, "points": 7 },
    { "id": 2, "points": 15 }
  ]
}
```

Race end is hardware (end switch), not a points threshold. When a lane hits the switch → `state: "win"` and `winner` set.

| Field | Meaning |
|---|---|
| `seq` | Monotonic counter (resets on reboot is fine) |
| `state` | `config` \| `homing` \| `ready` \| `race` \| `win` \| `error` |
| `winner` | Winning lane id in `win`, else `0` |
| `raceId` | Increments on each race start (may restart after reboot) |
| `durationMs` | Elapsed ms while `race`; frozen at final value in `win` |
| `lanes[].id` | 1-based lane id |
| `lanes[].points` | Cumulative points this race (display only) |

Extra fields are ignored. Missing required fields break the consumer.

### States used by stats

| `state` | Stats phase |
|---|---|
| `homing`, `ready`, `config` | idle (login / lobby) |
| `race` | racing |
| `win` | result (race is recorded) |
| `error` / silence > 5 s | offline |

## Push rules

1. Push a full snapshot whenever any field changes.
2. Also push at least every **1 s** (heartbeat). Stats marks the machine offline after **5 s** without a message.
3. On connect, send the current snapshot immediately.
4. Broadcast to all connected clients. Ignore inbound frames.
5. `seq` increments on every push, including heartbeats.
