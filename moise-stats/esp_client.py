"""WebSocket client that listens to the ESP race feed."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Awaitable, Callable, Optional

import websockets
from websockets.exceptions import ConnectionClosed

from esp_discover import discover_esp

log = logging.getLogger("esp_client")

OnSnapshot = Callable[[dict[str, Any]], Awaitable[None] | None]


class EspClient:
    def __init__(
        self,
        on_snapshot: OnSnapshot,
        preferred_url: Optional[str] = None,
    ) -> None:
        # preferred_url=None → always UDP-discover (ESP_WS_URL=auto)
        self.preferred_url = preferred_url
        self.url = preferred_url or ""
        self.on_snapshot = on_snapshot
        self.connected = False
        self.last: Optional[dict[str, Any]] = None
        self._task: Optional[asyncio.Task] = None

    def start(self) -> None:
        self._task = asyncio.get_running_loop().create_task(self._run())

    async def _session(self, url: str) -> None:
        async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
            self.connected = True
            self.url = url
            log.info("connected to ESP %s", url)
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

    async def _resolve_url(self) -> Optional[str]:
        if self.preferred_url:
            return self.preferred_url

        url = await discover_esp()
        if url:
            log.info("discovered ESP at %s", url)
            return url
        log.warning("UDP discovery found no controller")
        return None

    async def _run(self) -> None:
        backoff = 1.0
        while True:
            try:
                url = await self._resolve_url()
                if not url:
                    await asyncio.sleep(backoff)
                    backoff = min(10.0, backoff * 1.5)
                    continue

                try:
                    await self._session(url)
                    backoff = 1.0
                except (ConnectionClosed, OSError) as e:
                    self.connected = False
                    log.warning("ESP disconnected (%s): %s", url, e)
                    # Preferred URL failed → try discovery before next preferred retry
                    if self.preferred_url and url == self.preferred_url:
                        discovered = await discover_esp()
                        if discovered and discovered != url:
                            log.info("falling back to discovered ESP %s", discovered)
                            try:
                                await self._session(discovered)
                                backoff = 1.0
                                continue
                            except (ConnectionClosed, OSError) as e2:
                                self.connected = False
                                log.warning("discovered ESP failed: %s", e2)
                    await asyncio.sleep(backoff)
                    backoff = min(10.0, backoff * 1.5)

            except asyncio.CancelledError:
                self.connected = False
                raise
            except Exception as e:
                self.connected = False
                log.exception("ESP client error: %s", e)
                await asyncio.sleep(backoff)
                backoff = min(10.0, backoff * 1.5)
