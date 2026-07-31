# Moise Controller (ESP32)

One ESP32 drives 1–2 lanes (motors, NeoPixels, home/win/score switches).

## Build / flash

```bash
pio run -t upload
pio device monitor
```

Single binary for all boards. Identity (`id`, `lanes`) is stored in NVS and set from the Kino Konfig UI (or serial: `id 1`, `lanes 2`).

## Runtime modes

| Mode | How | Behavior |
|------|-----|----------|
| `idle` | no NVS id, or `mode idle` | Waiting for identity |
| `run` | `mode run` | Homing / race state machine |
| `debug` | `mode debug` | Motor jog, LED, IO stream |

Do **not** change `MAIN_LOOP_DELAY`, score grace (2 s), motor times, or pull-up/pull-down polarity without hardware retest — see root README.

## Protocol

See root [README.md](../README.md) — Serial protocol v2 (`#`-prefixed lines, `#rdy` boot banner).
