#!/usr/bin/env python3
"""Mock ESP WebSocket server (Kino API v3) — manual start via HTTP /go."""

from __future__ import annotations

import asyncio
import json
import random
import socket
import time
from typing import Optional, Set

from aiohttp import web
import websockets
from websockets.server import WebSocketServerProtocol

HOST = "0.0.0.0"
WS_PORT = 81
HTTP_PORT = 82
DISCOVER_PORT = 4210
MAX_POINTS = 15
LANE_COUNT = 5
HEARTBEAT_S = 1.0

clients: Set[WebSocketServerProtocol] = set()
seq = 0
state = "ready"
winner = 0
points = [0] * LANE_COUNT
race_id = 0
race_start = 0.0
duration_ms = 0
busy = False
go_event: Optional[asyncio.Event] = None


def snapshot() -> dict:
    global duration_ms
    if state == "race" and race_start:
        duration_ms = int((time.time() - race_start) * 1000)
    return {
        "seq": seq,
        "state": state,
        "maxPoints": MAX_POINTS,
        "winner": winner,
        "raceId": race_id,
        "durationMs": duration_ms,
        "lanes": [{"id": i + 1, "points": points[i]} for i in range(LANE_COUNT)],
        "manual": True,
        "busy": busy,
    }


async def broadcast() -> None:
    global seq
    seq += 1
    msg = json.dumps(snapshot())
    dead = []
    for ws in clients:
        try:
            await ws.send(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        clients.discard(ws)


async def handler(ws: WebSocketServerProtocol) -> None:
    clients.add(ws)
    try:
        await ws.send(json.dumps(snapshot()))
        async for raw in ws:
            # Optional: accept {"cmd":"go"} over WS too
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict) and data.get("cmd") == "go" and go_event:
                go_event.set()
    finally:
        clients.discard(ws)


async def run_one_race() -> None:
    global state, winner, points, race_id, race_start, duration_ms, busy
    busy = True
    try:
        state, winner, points = "homing", 0, [0] * LANE_COUNT
        duration_ms = 0
        await broadcast()
        await asyncio.sleep(2)

        state = "ready"
        await broadcast()
        await asyncio.sleep(1.2)

        race_id += 1
        race_start = 0.0
        duration_ms = 0
        state = "race"
        await broadcast()
        # Let the Kino finish Get ready / 3-2-1 / 🏁 before points move
        await asyncio.sleep(3.5)
        race_start = time.time()

        # Natural 5-lane race: different paces, small score ticks, first past 15 wins
        speeds = [random.uniform(0.75, 1.25) for _ in range(LANE_COUNT)]
        speeds[random.randrange(LANE_COUNT)] *= 1.2
        winner = 0
        while winner == 0:
            lane = random.choices(range(LANE_COUNT), weights=speeds, k=1)[0]
            add = random.choices([1, 2, 3], weights=[55, 35, 10], k=1)[0]
            points[lane] += add
            await broadcast()
            await asyncio.sleep(random.uniform(0.28, 0.65))
            if points[lane] > MAX_POINTS:
                winner = lane + 1

        duration_ms = int((time.time() - race_start) * 1000)
        state = "win"
        await broadcast()
        await asyncio.sleep(6)

        # Back to ready so you can login again
        state, winner, points = "ready", 0, [0] * LANE_COUNT
        duration_ms = 0
        await broadcast()
    finally:
        busy = False
        await broadcast()


async def race_controller() -> None:
    assert go_event is not None
    while True:
        await go_event.wait()
        go_event.clear()
        if busy:
            continue
        await run_one_race()


async def heartbeat() -> None:
    while True:
        await asyncio.sleep(HEARTBEAT_S)
        if clients:
            await broadcast()


def _cors(resp: web.Response) -> web.Response:
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "*"
    return resp


async def http_go(_: web.Request) -> web.Response:
    if busy:
        return _cors(web.json_response({"ok": False, "error": "busy"}, status=409))
    if go_event:
        go_event.set()
    return _cors(web.json_response({"ok": True}))


async def http_status(_: web.Request) -> web.Response:
    return _cors(web.json_response(snapshot()))


async def http_options(_: web.Request) -> web.Response:
    return _cors(web.Response())


async def discovery_responder() -> None:
    """Answer LAN UDP probes so stats can find this mock (ESP_WS_URL=auto)."""
    loop = asyncio.get_running_loop()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", DISCOVER_PORT))
    sock.setblocking(False)

    def _on_readable() -> None:
        try:
            while True:
                data, addr = sock.recvfrom(64)
                text = data.decode("ascii", errors="ignore").strip()
                if not text.startswith("MOISE?"):
                    continue
                reply = f"MOISE 1 127.0.0.1 {WS_PORT}".encode("ascii")
                sock.sendto(reply, addr)
        except BlockingIOError:
            return
        except OSError:
            return

    loop.add_reader(sock.fileno(), _on_readable)
    try:
        await asyncio.Future()  # run forever
    finally:
        loop.remove_reader(sock.fileno())
        sock.close()


async def main() -> None:
    global go_event
    go_event = asyncio.Event()

    app = web.Application()
    app.router.add_route("OPTIONS", "/go", http_options)
    app.router.add_get("/go", http_go)
    app.router.add_post("/go", http_go)
    app.router.add_get("/status", http_status)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, HOST, HTTP_PORT)
    await site.start()

    print(f"Mock ESP WS   ws://localhost:{WS_PORT}/")
    print(f"Mock control  http://localhost:{HTTP_PORT}/go  (GET/POST starts one race)")
    print(f"UDP discover  :{DISCOVER_PORT}  (probe MOISE?)")
    print("Waiting in ready — press the Kino test button or curl /go")

    async with websockets.serve(handler, HOST, WS_PORT):
        await asyncio.gather(race_controller(), heartbeat(), discovery_responder())


if __name__ == "__main__":
    asyncio.run(main())
