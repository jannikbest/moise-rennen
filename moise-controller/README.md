# Moise Controller (ESP32)

One ESP32 drives 1–2 lanes (motors, NeoPixels, home/win/score switches).

## Build / flash

```bash
cp wifi_secrets.h.example wifi_secrets.h   # set WIFI_SSID / WIFI_PASSWORD
pio run -t upload
pio device monitor
```

`wifi_secrets.h` is gitignored. The board joins your LAN as STA (`moise-rennen` hostname) and serves the race WebSocket on port **81**.

UDP discovery: answers `MOISE?` on port **4210** with `MOISE 1 <ip> 81` so `moise-stats` can find it (`ESP_WS_URL=auto`).

## Runtime modes

| Mode | How | Behavior |
|------|-----|----------|
| `idle` | no NVS id, or `mode idle` | Waiting for identity |
| `run` | `mode run` | Homing / race state machine |
| `debug` | `mode debug` | Motor jog, LED, IO stream |

Do **not** change `MAIN_LOOP_DELAY`, score grace (2 s), motor times, or pull-up/pull-down polarity without hardware retest — see root README.

## Protocol

See root [README.md](../README.md) and [docs/esp-webservice.md](../docs/esp-webservice.md).
