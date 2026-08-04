#!/usr/bin/env bash
# One-shot Raspberry Pi setup for Moise Kino + Stats.
# Installs OS packages, Python venv, optional Chromium, then can enable autostart.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=moise-common.sh
. "$ROOT/moise-common.sh"

WITH_AUTOSTART=0
WITH_CHROMIUM=1

usage() {
  cat <<EOF
Usage: $0 [--autostart] [--no-chromium]

  Prepares this machine to run Kino + Stats on a Raspberry Pi.

  --autostart     Also run ./install-autostart.sh (systemd enable)
  --no-chromium   Skip apt install of Chromium (headless / SSH-only)

Then start manually:
  ./run.sh          # stats + Kino (no browser)
  ./start-moise.sh  # same + fullscreen Chromium
EOF
}

for arg in "$@"; do
  case "$arg" in
    -h|--help) usage; exit 0 ;;
    --autostart) WITH_AUTOSTART=1 ;;
    --no-chromium) WITH_CHROMIUM=0 ;;
    *) echo "Unknown option: $arg" >&2; usage >&2; exit 1 ;;
  esac
done

if ! command -v apt-get >/dev/null 2>&1; then
  echo "This script expects Debian/Raspberry Pi OS (apt-get)." >&2
  exit 1
fi

echo "==> System packages"
PKGS=(python3 python3-venv python3-pip fonts-noto-color-emoji)
if [ "$WITH_CHROMIUM" -eq 1 ]; then
  # Bookworm: package is usually "chromium"; older images used chromium-browser
  PKGS+=(chromium)
fi
sudo apt-get update
sudo apt-get install -y "${PKGS[@]}" || {
  if [ "$WITH_CHROMIUM" -eq 1 ]; then
    echo "chromium package missing — trying chromium-browser…"
    sudo apt-get install -y python3 python3-venv python3-pip fonts-noto-color-emoji chromium-browser
  else
    exit 1
  fi
}

echo "==> Stats venv + .env"
moise_ensure_stats_venv "$ROOT"

echo
echo "Edit ESP address if needed:"
echo "  nano $ROOT/moise-stats/.env"
echo

if [ "$WITH_AUTOSTART" -eq 1 ]; then
  echo "==> Autostart"
  "$ROOT/install-autostart.sh" install
else
  echo "Autostart not enabled. Later:"
  echo "  ./install-autostart.sh install"
fi

echo
echo "Done. Manual start: ./start-moise.sh   (or ./run.sh without browser)"
