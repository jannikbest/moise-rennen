"""UDP discovery for Moise race controllers on the local LAN."""

from __future__ import annotations

import asyncio
import logging
import socket
from typing import Optional

log = logging.getLogger("esp_discover")

DISCOVER_PORT = 4210
PROBE = b"MOISE?\n"
REPLY_PREFIX = "MOISE 1 "


def parse_reply(raw: bytes) -> Optional[str]:
    """Parse `MOISE 1 <ip> <port>` → `ws://ip:port/`."""
    text = raw.decode("ascii", errors="ignore").strip()
    if not text.startswith(REPLY_PREFIX):
        return None
    parts = text.split()
    if len(parts) < 4:
        return None
    ip, port_s = parts[2], parts[3]
    try:
        port = int(port_s)
    except ValueError:
        return None
    if not ip or port <= 0 or port > 65535:
        return None
    return f"ws://{ip}:{port}/"


async def discover_esp(
    timeout: float = 1.5,
    probes: int = 3,
    port: int = DISCOVER_PORT,
) -> Optional[str]:
    """Broadcast MOISE? and return the first WebSocket URL, or None."""
    loop = asyncio.get_running_loop()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", 0))
    sock.setblocking(False)

    found: asyncio.Future[str] = loop.create_future()

    def _on_readable() -> None:
        if found.done():
            return
        try:
            while True:
                data, _addr = sock.recvfrom(256)
                url = parse_reply(data)
                if url and not found.done():
                    found.set_result(url)
                    return
        except BlockingIOError:
            return
        except OSError as e:
            if not found.done():
                found.set_exception(e)

    loop.add_reader(sock.fileno(), _on_readable)
    try:
        interval = timeout / max(probes, 1)
        for _ in range(probes):
            try:
                sock.sendto(PROBE, ("255.255.255.255", port))
            except OSError as e:
                log.warning("UDP probe failed: %s", e)
            try:
                return await asyncio.wait_for(asyncio.shield(found), timeout=interval)
            except asyncio.TimeoutError:
                continue
        return None
    finally:
        loop.remove_reader(sock.fileno())
        sock.close()
