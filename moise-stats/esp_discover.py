"""UDP discovery for Moise race controllers on the local LAN."""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket
import struct
import sys
from typing import Optional

try:
    import fcntl
except ImportError:  # Windows
    fcntl = None  # type: ignore[assignment]

log = logging.getLogger("esp_discover")

DISCOVER_PORT = 4210
PROBE = b"MOISE?\n"
REPLY_PREFIX = "MOISE 1 "
GLOBAL_BROADCAST = "255.255.255.255"

# ioctl codes differ per platform, but the IPv4 address always sits at bytes
# 20:24 of the returned ifreq (16 byte name + sockaddr header).
if sys.platform.startswith("linux"):
    _SIOCGIFADDR, _SIOCGIFNETMASK = 0x8915, 0x891B
else:  # macOS / BSD
    _SIOCGIFADDR, _SIOCGIFNETMASK = 0xC0206921, 0xC0206925


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


def _ifreq_ipv4(sock: socket.socket, name: str, request: int) -> Optional[str]:
    try:
        raw = fcntl.ioctl(sock.fileno(), request, struct.pack("256s", name.encode()[:15]))
    except OSError:
        return None
    return socket.inet_ntoa(raw[20:24])


def interface_targets() -> list[tuple[str, str]]:
    """(source ip, broadcast ip) for every IPv4 interface with a broadcast domain.

    Sending from an explicit source address is what makes discovery survive a VPN:
    a socket bound to 0.0.0.0 follows the default route, which on a point-to-point
    tunnel cannot carry broadcasts (EADDRNOTAVAIL) and never reaches the LAN.
    """
    if fcntl is None:
        return []

    targets: list[tuple[str, str]] = []
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        for _index, name in socket.if_nameindex():
            ip = _ifreq_ipv4(probe, name, _SIOCGIFADDR)
            mask = _ifreq_ipv4(probe, name, _SIOCGIFNETMASK)
            if not ip or not mask:
                continue
            try:
                addr = ipaddress.IPv4Address(ip)
                net = ipaddress.IPv4Network(f"{ip}/{mask}", strict=False)
            except ValueError:
                continue
            # Loopback, link-local and /32 tunnels have nobody to broadcast to.
            if addr.is_loopback or addr.is_link_local or net.prefixlen >= 31:
                continue
            targets.append((ip, str(net.broadcast_address)))
    finally:
        probe.close()
    return targets


def _open_socket(bind_ip: str) -> Optional[socket.socket]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((bind_ip, 0))
    except OSError as e:
        log.debug("cannot bind discovery socket to %s: %s", bind_ip or "0.0.0.0", e)
        sock.close()
        return None
    sock.setblocking(False)
    return sock


async def discover_esp(
    timeout: float = 4.0,
    probes: int = 4,
    port: int = DISCOVER_PORT,
) -> Optional[str]:
    """Broadcast MOISE? on every LAN interface and return the first WebSocket URL."""
    loop = asyncio.get_running_loop()
    targets = interface_targets() or [("", GLOBAL_BROADCAST)]

    senders: list[tuple[socket.socket, str]] = []
    for source_ip, broadcast_ip in targets:
        sock = _open_socket(source_ip)
        if sock:
            senders.append((sock, broadcast_ip))
    if not senders:
        log.warning("no usable interface for UDP discovery")
        return None

    found: asyncio.Future[str] = loop.create_future()

    def _on_readable(sock: socket.socket) -> None:
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

    for sock, _ in senders:
        loop.add_reader(sock.fileno(), _on_readable, sock)

    try:
        interval = timeout / max(probes, 1)
        for _ in range(probes):
            sent = 0
            for sock, broadcast_ip in senders:
                try:
                    sock.sendto(PROBE, (broadcast_ip, port))
                    sent += 1
                except OSError as e:
                    log.debug("UDP probe to %s failed: %s", broadcast_ip, e)
            if not sent:
                log.warning("UDP probe failed on all interfaces")
                return None
            try:
                return await asyncio.wait_for(asyncio.shield(found), timeout=interval)
            except asyncio.TimeoutError:
                continue
        return None
    finally:
        for sock, _ in senders:
            loop.remove_reader(sock.fileno())
            sock.close()
