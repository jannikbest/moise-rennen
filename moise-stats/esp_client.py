"""WebSocket client that listens to the ESP race feed."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Awaitable, Callable, Optional

import websockets
from websockets.exceptions import ConnectionClosed

log = logging.getLogger("esp_client")

OnSnapshot = Callable[[dict[str, Any]], Awaitable[None] | None]


class EspClient:
    def __init__(self, url: str, on_snapshot: OnSnapshot) -> None:
        self.url = url
        self.on_snapshot = on_snapshot
        self.connected = False
        self.last: Optional[dict[str, Any]] = None
        self._task: Optional[asyncio.Task] = None

    def start(self) -> None:
        self._task = asyncio.get_running_loop().create_task(self._run())

    async def _run(self) -> None:
        backoff = 1.0
        while True:
            try:
                async with websockets.connect(self.url, ping_interval=20, ping_timeout=20) as ws:
                    self.connected = True
                    backoff = 1.0
                    log.info("connected to ESP %s", self.url)
                    async for raw in ws:
                        try:
                            data = json.loads(raw)
                        except json.JSONDecodeError:
                            continue
                        if not isinstance(data, dict):
                            continue
                        self.last = data
                        result = self.on_snapshot(data)
                        if asyncio.iscoroutine(result):
                            await result
            except (ConnectionClosed, OSError, asyncio.CancelledError) as e:
                self.connected = False
                if isinstance(e, asyncio.CancelledError):
                    raise
                log.warning("ESP disconnected: %s — retry in %.1fs", e, backoff)
                await asyncio.sleep(backoff)
                backoff = min(10.0, backoff * 1.5)
            except Exception as e:
                self.connected = False
                log.exception("ESP client error: %s", e)
                await asyncio.sleep(backoff)
                backoff = min(10.0, backoff * 1.5)
