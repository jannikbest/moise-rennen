#!/usr/bin/env python3
"""Moise stats service: ESP listener + encrypted DB + Kino WebSocket API v4."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

from cryptography.fernet import Fernet
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

from esp_client import EspClient  # noqa: E402
from server import StatsServer  # noqa: E402
from stats import StatsEngine  # noqa: E402
from store import Store  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("main")


def parse_lane_labels(raw: str) -> dict[int, str]:
    out: dict[int, str] = {}
    for part in (raw or "").split(","):
        part = part.strip()
        if not part or ":" not in part:
            continue
        k, v = part.split(":", 1)
        try:
            out[int(k.strip())] = v.strip()
        except ValueError:
            continue
    if not out:
        out = {1: "Speedy", 2: "Pilzy", 3: "Emdy", 4: "Kety", 5: "Koky"}
    return out


def ensure_key() -> str:
    key = (os.getenv("MOISE_STATS_KEY") or "").strip()
    env_path = ROOT / ".env"
    if key:
        return key
    key = Fernet.generate_key().decode()
    lines = []
    if env_path.exists():
        lines = env_path.read_text().splitlines()
        replaced = False
        for i, line in enumerate(lines):
            if line.startswith("MOISE_STATS_KEY="):
                lines[i] = f"MOISE_STATS_KEY={key}"
                replaced = True
                break
        if not replaced:
            lines.append(f"MOISE_STATS_KEY={key}")
    else:
        example = ROOT / ".env.example"
        base = example.read_text() if example.exists() else "MOISE_STATS_KEY=\n"
        lines = []
        for line in base.splitlines():
            if line.startswith("MOISE_STATS_KEY="):
                lines.append(f"MOISE_STATS_KEY={key}")
            else:
                lines.append(line)
        if not any(l.startswith("MOISE_STATS_KEY=") for l in lines):
            lines.append(f"MOISE_STATS_KEY={key}")
    env_path.write_text("\n".join(lines) + "\n")
    try:
        os.chmod(env_path, 0o600)
    except OSError:
        pass
    log.info("generated MOISE_STATS_KEY in %s", env_path)
    return key


def main() -> None:
    key = ensure_key()
    load_dotenv(ROOT / ".env", override=True)

    db_path = ROOT / "data" / "moise.db.enc"
    store = Store(db_path, key)
    labels = parse_lane_labels(os.getenv("LANE_LABELS", ""))
    stats = StatsEngine(store, labels)

    host = os.getenv("KINO_WS_HOST", "0.0.0.0")
    port = int(os.getenv("KINO_WS_PORT", "8770"))
    esp_url = os.getenv("ESP_WS_URL", "ws://127.0.0.1:81/")
    mock_control = os.getenv("MOCK_CONTROL_URL", "http://127.0.0.1:82/go")
    try:
        claim_window = float(os.getenv("CLAIM_WINDOW_S", "20"))
    except ValueError:
        claim_window = 20.0

    server = StatsServer(
        store,
        stats,
        labels,
        host=host,
        port=port,
        mock_control_url=mock_control,
        claim_window_s=claim_window,
    )

    async def on_snap(data):
        await server.on_esp_snapshot(data)

    esp = EspClient(esp_url, on_snap)

    async def amain():
        esp.start()
        await server.run()

    try:
        asyncio.run(amain())
    except KeyboardInterrupt:
        log.info("shutting down")
        sys.exit(0)


if __name__ == "__main__":
    main()
