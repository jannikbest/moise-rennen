#!/usr/bin/env bash
# Install / remove / status for the Moise systemd autostart (Pi kiosk).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
SERVICE_NAME="moise-autostart.service"
UNIT_PATH="/etc/systemd/system/${SERVICE_NAME}"
USER_NAME="$(id -un)"
GROUP_NAME="$(id -gn)"
HOME_DIR="$(getent passwd "$USER_NAME" | cut -d: -f6)"
XAUTH="${HOME_DIR}/.Xauthority"
DISPLAY_VAL="${DISPLAY:-:0}"

usage() {
  cat <<EOF
Usage: $0 [install|uninstall|status|start|stop]

  install    Install and enable systemd unit (needs sudo)
  uninstall  Disable and remove unit (needs sudo)
  status     Show service status
  start      Start now
  stop       Stop now

Detects this checkout and the current user automatically.
Repo: $ROOT
User: $USER_NAME
EOF
}

write_unit() {
  sudo tee "$UNIT_PATH" >/dev/null <<EOF
[Unit]
Description=Moise Kino + Stats (kiosk)
After=network-online.target graphical.target
Wants=network-online.target

[Service]
Type=simple
User=${USER_NAME}
Group=${GROUP_NAME}
Environment=DISPLAY=${DISPLAY_VAL}
Environment=XAUTHORITY=${XAUTH}
WorkingDirectory=${ROOT}
ExecStart=${ROOT}/start-moise.sh
Restart=on-failure
RestartSec=5
KillMode=control-group
TimeoutStopSec=15

[Install]
WantedBy=graphical.target
EOF
}

cmd="${1:-install}"

case "$cmd" in
  -h|--help|help)
    usage
    exit 0
    ;;
  install)
    if [ ! -x "$ROOT/start-moise.sh" ]; then
      echo "Missing executable $ROOT/start-moise.sh" >&2
      exit 1
    fi
    # Ensure venv + .env exist before enabling autostart
    # shellcheck source=moise-common.sh
    . "$ROOT/moise-common.sh"
    moise_ensure_stats_venv "$ROOT"

    echo "Installing ${SERVICE_NAME} as user ${USER_NAME}…"
    write_unit
    sudo systemctl daemon-reload
    sudo systemctl enable "$SERVICE_NAME"
    echo
    echo "Enabled. After reboot the kiosk starts with the graphical target."
    echo "  Start now:  sudo systemctl start ${SERVICE_NAME}"
    echo "  Status:     systemctl status ${SERVICE_NAME}"
    echo "  Logs:       journalctl -u ${SERVICE_NAME} -f"
    echo
    echo "Set ESP_WS_URL in moise-stats/.env before going live."
    ;;
  uninstall)
    echo "Removing ${SERVICE_NAME}…"
    sudo systemctl disable --now "$SERVICE_NAME" 2>/dev/null || true
    sudo rm -f "$UNIT_PATH"
    sudo systemctl daemon-reload
    echo "Removed."
    ;;
  status)
    systemctl status "$SERVICE_NAME" --no-pager || true
    ;;
  start)
    sudo systemctl start "$SERVICE_NAME"
    systemctl status "$SERVICE_NAME" --no-pager || true
    ;;
  stop)
    sudo systemctl stop "$SERVICE_NAME"
    ;;
  *)
    usage >&2
    exit 1
    ;;
esac
