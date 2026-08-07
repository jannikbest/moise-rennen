#!/usr/bin/env bash
# Shared helpers for Moise launchers (macOS / Linux / Git Bash).
# shellcheck disable=SC2034

moise_root() {
  cd "$(dirname "${BASH_SOURCE[0]}")" && pwd
}

moise_python() {
  if command -v python3 >/dev/null 2>&1; then
    echo python3
  elif command -v python >/dev/null 2>&1; then
    echo python
  else
    echo "Python 3 is required" >&2
    return 1
  fi
}

# Resolve venv python/pip for Unix (bin/) or Windows (Scripts/).
moise_venv_bins() {
  local venv="$1"
  if [ -x "$venv/bin/python" ]; then
    MOISE_PY="$venv/bin/python"
    MOISE_PIP="$venv/bin/pip"
  elif [ -x "$venv/Scripts/python.exe" ]; then
    MOISE_PY="$venv/Scripts/python.exe"
    MOISE_PIP="$venv/Scripts/pip.exe"
  elif [ -x "$venv/Scripts/python" ]; then
    MOISE_PY="$venv/Scripts/python"
    MOISE_PIP="$venv/Scripts/pip"
  else
    return 1
  fi
}

moise_ensure_stats_venv() {
  local root="$1"
  local venv="$root/moise-stats/.venv"
  local py
  py="$(moise_python)" || return 1

  if [ ! -d "$venv" ]; then
    echo "Creating moise-stats venv…"
    "$py" -m venv "$venv"
    moise_venv_bins "$venv" || return 1
    "$MOISE_PIP" install -r "$root/moise-stats/requirements.txt"
  else
    moise_venv_bins "$venv" || {
      echo "Broken venv at $venv — remove it and retry" >&2
      return 1
    }
  fi

  if [ ! -f "$root/moise-stats/.env" ]; then
    cp "$root/moise-stats/.env.example" "$root/moise-stats/.env"
    echo "Created moise-stats/.env from example"
  fi
}

moise_find_browser() {
  local b
  for b in chromium-browser chromium google-chrome google-chrome-stable; do
    if command -v "$b" >/dev/null 2>&1; then
      echo "$b"
      return 0
    fi
  done
  # macOS app bundles
  for b in \
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    "/Applications/Chromium.app/Contents/MacOS/Chromium" \
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"; do
    if [ -x "$b" ]; then
      echo "$b"
      return 0
    fi
  done
  return 1
}

# Launch Chromium/Chrome in kiosk mode; echoes PID on success (via stdout last line is awkward —
# instead append to caller's PIDS by printing the browser path and starting in caller).
# Usage: moise_open_kiosk <url> → starts browser in background, prints PID to stdout.
moise_open_kiosk() {
  local url="${1:-http://127.0.0.1:8080/}"
  local browser kiosk_dir
  browser="$(moise_find_browser || true)"
  if [ -z "$browser" ]; then
    echo "No Chromium/Chrome found — open $url manually" >&2
    return 1
  fi
  kiosk_dir="${MOISE_KIOSK_PROFILE:-/tmp/moise-chrome-kiosk}"
  mkdir -p "$kiosk_dir"
  echo "Starting $browser (kiosk)…" >&2
  # Pi Chromium often software-composites without these; Mac ignores them harmlessly.
  "$browser" \
    --kiosk \
    --noerrdialogs \
    --disable-infobars \
    --disable-session-crashed-bubble \
    --disable-restore-session-state \
    --check-for-update-interval=31536000 \
    --disable-features=TranslateUI \
    --autoplay-policy=no-user-gesture-required \
    --ignore-gpu-blocklist \
    --enable-gpu-rasterization \
    --enable-zero-copy \
    --enable-accelerated-2d-canvas \
    --use-gl=egl \
    --user-data-dir="$kiosk_dir" \
    "$url" &
  echo $!
}

# Wait until X11/Wayland socket is up (Pi autostart races the desktop).
moise_wait_for_display() {
  local max="${1:-60}"
  local i
  export DISPLAY="${DISPLAY:-:0}"
  for i in $(seq 1 "$max"); do
    if [ -S "/tmp/.X11-unix/X${DISPLAY#:}" ] || [ -n "${WAYLAND_DISPLAY:-}" ]; then
      return 0
    fi
    # xdpyinfo is optional; ignore if missing
    if command -v xdpyinfo >/dev/null 2>&1 && xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  return 1
}
