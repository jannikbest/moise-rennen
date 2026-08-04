# Moise-Rennen

Arcade-style mouse racing (like horse racing). Players insert coins, start a race, and throw balls into holes on lanes. Each hit moves the corresponding mouse forward. First mouse to the finish wins.

## Components

| Folder | Role |
|--------|------|
| `moise-brain` | Python brain on the Raspberry Pi: game logic, serial to ESP32s, WebSocket to the display, coin/start GPIO |
| `moise-controller` | ESP32 firmware: motors, LEDs, score/home/win switches (one board drives 1–2 lanes) |
| `moise-kino` | Browser display (kiosk via `file://`). Modes: Run / Konfig / Debug |
| `moise-support` | Telegram bot (legacy, not part of the active stack) |

```
Kino (browser)  <──WebSocket──>  Brain (Python)  <──Serial──>  ESP32 × N
```

## System modes

The mode is **system-wide**, not only a UI view. Switching in Kino also switches Brain and all controllers.

| Mode | Access | Purpose |
|------|--------|---------|
| **Run** | Public | Normal play |
| **Konfig** | Password | Map controllers to USB / lanes, set game price, credit |
| **Debug** | Password | Live I/O, motor jog, LED test, serial monitor |

Password is `MOISE_ADMIN_PASSWORD` in `moise-brain/.env` (see `.env.example`). Auth is a plain token over local WebSocket — fine for a LAN arcade machine, not a real security boundary.

## Commissioning a new controller

1. Flash the same firmware binary to every ESP32 (`pio run -t upload`).
2. Open Kino → Konfig (password), run Discover.
3. Use **Identify** (LEDs flash) to see which board is which.
4. Set NVS `id` and `lanes` (1 or 2) from the UI.
5. Assign local lanes to global mouse numbers in config.

## Serial protocol v2

Line-based ASCII, 115200 8N1, newline-terminated.

**Every line from the controller starts with `#`.** Anything without `#` is noise and must be discarded without changing state.

### Boot banner

After boot the controller sends once:

```
#rdy id=<n> lanes=<n> fw=<version>
```

Brain discards everything until this banner, then re-syncs mode and lane mapping. Seeing bootloader noise (`ets `, `rst:0x`, …) means the controller rebooted.

### Host → Controller

Always valid:

| Command | Effect |
|---------|--------|
| `id?` / `id <n>` | Query / set controller ID (NVS) |
| `lanes?` / `lanes <1\|2>` | Query / set physical lane count (NVS) |
| `mode?` / `mode run\|debug\|idle` | Query / set runtime mode |
| `identify` | Flash LEDs for physical identification |

Only in `run`:

| Command | Effect |
|---------|--------|
| `go` | Start race (only if READY) |
| `home` | Force homing |
| `lose` | External game over |
| `reset` | Stop motors → IO_CHECK |
| `ready?` | Query readiness |
| `speed <lane> <0-255>` | Set race PWM for local lane |

Only in `debug`:

| Command | Effect |
|---------|--------|
| `dbg motor <lane> fwd\|rev\|stop [ms]` | Jog motor (deadman timeout) |
| `dbg led <lane> on\|off\|<r,g,b>` | Direct LED control |
| `dbg io?` | One-shot dump of all inputs |
| `dbg stream on\|off` | Stream input edge events |

### Controller → Host

All lines prefixed with `#`:

| Message | Meaning |
|---------|---------|
| `#evt score <lane> <points>` | Score event (lane local 1\|2, points 1–3) |
| `#evt win <lane>` | Win switch |
| `#evt io <lane> <home\|win\|s1\|s2\|s3> <0\|1>` | Input change (debug stream) |
| `#st <startup\|homing\|ready\|racing\|stop\|debug\|error\|idle>` | State change |
| `#err <code> <text>` | Error |
| `#id <n>`, `#lanes <n>`, `#mode <m>` | Responses |
| `#rdy id=<n> lanes=<n> fw=<version>` | Boot banner |
| `#ready` / `#no` / `#error` | Answers to `ready?` |

Local lane numbers map to global mice only in the Brain config.

## WebSocket API v2

URL from config (default `ws://localhost:8765`).

### Broadcast (server → clients)

```json
{
  "guthaben": 500,
  "einzahlungen": 1000,
  "service_gutschriften": 200,
  "ausgaben": 700,
  "gespielte_spiele": 42,
  "game_price_cent": 100,
  "game_state": "racing",
  "system_mode": "run",
  "maus_punktzahlen": { "1": 3, "2": 5 },
  "maus_namen": { "1": "Alice" },
  "gewonnen": { "id": "Maus 2", "Zeit": 4523.5 },
  "controllers": [],
  "errors": [],
  "io_states": {},
  "game_error": "none",
  "error_message": ""
}
```

### Client → server actions

Public: `get_game_data`, `ping`, `set_maus_name`, `freispiel`, `login`.

Token required (Konfig / Debug / Kasse):

| Action | Purpose |
|--------|---------|
| `login` | `{password}` → `{token, ttl}` |
| `get_config` / `set_config` | Full config read/write |
| `discover_controllers` | Scan USB ports, query `id?` |
| `set_controller_id` | Write NVS id on a port |
| `identify_controller` | Flash LEDs |
| `set_mode` | `run` / `config` / `debug` |
| `debug_motor` / `debug_led` / `debug_io_stream` | Hardware debug |
| `add_credit` | Service credit (cent), does not touch cash `einzahlungen` |
| `set_price` | `game.price_cent` |
| `reset_counters` | Reset accounting counters |
| `serial_log_subscribe` / `serial_log_unsubscribe` | Serial monitor stream |
| `serial_send` | Manual command to a controller |

Cash accounting: `guthaben = einzahlungen + service_gutschriften - ausgaben`.

## Run

macOS / Linux:

```bash
./dev.sh          # mock ESP + stats + Kino (./dev-mac.sh is an alias)
./run.sh          # production: stats + Kino, real ESP via moise-stats/.env
./start-moise.sh  # Pi kiosk: same as run.sh + Chromium fullscreen
```

Windows (PowerShell):

```powershell
.\dev.ps1         # mock ESP + stats + Kino
.\run.ps1         # production: real ESP via moise-stats/.env
```

If execution is blocked: `powershell -ExecutionPolicy Bypass -File .\dev.ps1`

Kino is served at `http://127.0.0.1:8080` (classic `<script>` tags, no bundler).

## Raspberry Pi (Kino + Stats)

On the Pi (Raspberry Pi OS with desktop):

```bash
# one-time: packages, venv, .env — optional --autostart
./setup-pi.sh
./setup-pi.sh --autostart

# set ESP addressing (auto = UDP discovery on the LAN)
nano moise-stats/.env   # ESP_WS_URL=auto

# start now
./start-moise.sh        # stats + Kino + Chromium kiosk
# or without browser:
./run.sh
```

Autostart (systemd, detects current user + repo path):

```bash
./install-autostart.sh install   # enable + persist across reboot
./install-autostart.sh start     # start now
./install-autostart.sh status
./install-autostart.sh stop
./install-autostart.sh uninstall
```

Logs: `journalctl -u moise-autostart.service -f`

## Timing / debounce (do not casually change)

On the ESP32, `MAIN_LOOP_DELAY 10` **is** the debounce. Edge detection has no separate software debounce. Also leave alone: 2 s score grace at race start, score motor times, LED intervals, pull-up/pull-down polarity.
