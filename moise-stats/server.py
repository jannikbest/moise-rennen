"""Kino-facing WebSocket server (API v4) — times + winner claim."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import defaultdict, deque
from typing import Any, Deque, Dict, Optional, Set

import websockets
from websockets.server import WebSocketServerProtocol

from recorder import Recorder
from stats import IDLE_STATES, StatsEngine
from store import Store
from users import name_key, register_or_login

log = logging.getLogger("server")

IDLE_ESP_STATES = {"homing", "ready", "config"}
ESP_STALE_S = 5.0
CLAIM_CONFIRM_S = 6.0
INVITE_MESSAGE = (
    "Want on the leaderboard and in the big final? "
    "Enter your name and PIN now — remember your PIN!"
)


def phase_for(state: Optional[str]) -> str:
    if state == "race":
        return "racing"
    if state == "win":
        return "result"
    if state in IDLE_ESP_STATES:
        return "idle"
    return "offline"


class StatsServer:
    def __init__(
        self,
        store: Store,
        stats: StatsEngine,
        lane_labels: Dict[int, str],
        host: str = "0.0.0.0",
        port: int = 8770,
        mock_control_url: str = "",
        claim_window_s: float = 20.0,
    ) -> None:
        self.store = store
        self.stats = stats
        self.lane_labels = lane_labels
        self.host = host
        self.port = port
        self.mock_control_url = (mock_control_url or "").strip()
        self.claim_window_s = float(claim_window_s or 20.0)

        self.phase = "offline"
        self.claim: Optional[dict[str, Any]] = None
        self.last_result: Optional[dict[str, Any]] = None
        self.clients: Set[WebSocketServerProtocol] = set()
        self.seq = 0
        self.esp_snapshot: Optional[dict[str, Any]] = None
        self.last_snapshot_at = 0.0
        self._last_broadcast: Optional[str] = None
        self._fail_log: Dict[str, Deque[float]] = defaultdict(deque)

        self.recorder = Recorder(
            store=store,
            lane_labels=lane_labels,
            on_recorded=self.stats.rebuild,
        )

    def _rate_limited(self, key: str, limit: int = 5, window: float = 60.0) -> bool:
        now = time.time()
        q = self._fail_log[key]
        while q and now - q[0] > window:
            q.popleft()
        return len(q) >= limit

    def _note_fail(self, key: str) -> None:
        self._fail_log[key].append(time.time())

    def _rank_of(self, board: list, name: str) -> Optional[int]:
        for i, row in enumerate(board or []):
            if row.get("name") == name:
                return i + 1
        return None

    def _lane_label(self, lane: int) -> str:
        return self.lane_labels.get(lane) or f"Mouse {lane}"

    def _claim_open(self) -> bool:
        return bool(self.claim) and time.time() < float(self.claim.get("deadline") or 0)

    def _close_claim(self) -> None:
        self.claim = None

    def _build_last_result(
        self,
        race: dict[str, Any],
        *,
        user: Optional[str] = None,
        message: Optional[str] = None,
    ) -> dict[str, Any]:
        winner_lane = int(race.get("winnerLane") or 0)
        label = user or self._lane_label(winner_lane)
        return {
            "raceId": race.get("id"),
            "winnerLane": winner_lane,
            "winner": label,
            "user": user,
            "durationMs": int(race.get("durationMs") or 0),
            "message": message or INVITE_MESSAGE,
        }

    def _claim_success_message(self, user: str) -> str:
        snap = self.stats.snapshot or {}
        boards = snap.get("leaderboards") or {}
        rank_times = self._rank_of(boards.get("times") or [], user)
        wins_row = next((r for r in (boards.get("wins") or []) if r.get("name") == user), None)
        wins = int((wins_row or {}).get("value") or 0)

        parts = ["Saved!"]
        if rank_times is not None:
            parts.append(f"rank {rank_times} on best times")
        if wins:
            parts.append(f"{wins} win" if wins == 1 else f"{wins} wins")
        return " · ".join(parts)

    def _esp_stale(self) -> bool:
        return (time.time() - self.last_snapshot_at) > ESP_STALE_S

    def _phase_from_esp(self) -> str:
        if self.esp_snapshot is None or self._esp_stale():
            return "offline"
        return phase_for(self.esp_snapshot.get("state"))

    def _tick_claim(self) -> None:
        if not self.claim:
            return
        if time.time() >= float(self.claim.get("deadline") or 0):
            log.info("claim window closed for race %s", self.claim.get("raceId"))
            self._close_claim()

    def _apply_phase(self, esp_phase: str) -> None:
        """Drive session from ESP phase, but keep result while a claim is open."""
        old = self.phase

        # A new race kills any leftover claim immediately.
        if esp_phase == "racing" and self.claim:
            log.info("new race — discarding open claim")
            self._close_claim()

        if old == "racing" and esp_phase == "result":
            self._open_claim_from_race()
        elif old == "racing" and esp_phase != "result":
            log.info("race aborted — nothing recorded")
            self._close_claim()
            self.last_result = None

        self._tick_claim()

        # Claim window (open typing or short post-claim confirm) holds result.
        if self.claim:
            new_phase = "result"
        elif esp_phase == "result":
            # ESP still on win but claim already closed.
            new_phase = "idle"
        else:
            new_phase = esp_phase

        if new_phase == "racing" and old != "racing":
            self.last_result = None

        if old == "result" and new_phase != "result":
            self.last_result = None
            self._close_claim()

        self.phase = new_phase

    def _open_claim_from_race(self) -> None:
        race = self.recorder.record(self.esp_snapshot or {})
        winner_lane = int(race.get("winnerLane") or 0)
        label = self._lane_label(winner_lane)
        now = time.time()
        self.claim = {
            "raceId": race.get("id"),
            "winnerLane": winner_lane,
            "label": label,
            "deadline": now + self.claim_window_s,
            "claimed": False,
            "user": None,
            "durationMs": int(race.get("durationMs") or 0),
        }
        self.last_result = self._build_last_result(race, message=INVITE_MESSAGE)
        log.info(
            "recorded race %s (esp %s) — claim open for %ss",
            race.get("id"),
            race.get("espRaceId"),
            int(self.claim_window_s),
        )

    async def on_esp_snapshot(self, data: dict[str, Any]) -> None:
        self.esp_snapshot = data
        self.last_snapshot_at = time.time()
        self._apply_phase(self._phase_from_esp())
        await self.broadcast()

    def _claim_payload(self) -> Optional[dict[str, Any]]:
        if not self.claim:
            return None
        now = time.time()
        deadline = float(self.claim.get("deadline") or 0)
        left = max(0, int(deadline - now + 0.999))
        open_ = (not self.claim.get("claimed")) and left > 0
        return {
            "open": open_,
            "secondsLeft": left if open_ else 0,
            "claimed": bool(self.claim.get("claimed")),
            "winnerLane": self.claim.get("winnerLane"),
            "label": self.claim.get("label"),
            "user": self.claim.get("user"),
        }

    def build_payload(self) -> dict[str, Any]:
        esp = self.esp_snapshot or {
            "state": "offline",
            "maxPoints": 15,
            "winner": 0,
            "raceId": 0,
            "durationMs": 0,
            "lanes": [{"id": i, "points": 0} for i in sorted(self.lane_labels)],
        }

        if self.phase == "offline":
            state = "offline"
        elif self.phase == "result":
            # Keep win screen while claim is open even if ESP already left win.
            state = "win"
        else:
            state = esp.get("state") or "offline"

        raw_lanes = esp.get("lanes") or []
        by_id = {int(l["id"]): l for l in raw_lanes if "id" in l}
        if state in IDLE_STATES or state == "offline" or self.phase == "result":
            lane_ids = sorted(set(list(by_id.keys()) + list(self.lane_labels.keys())))
        else:
            lane_ids = sorted(by_id.keys()) or sorted(self.lane_labels.keys())

        lanes_out = []
        for lid in lane_ids:
            pts = int(by_id.get(lid, {}).get("points", 0))
            label = self.lane_labels.get(lid) or f"Mouse {lid}"
            lanes_out.append({"id": lid, "points": pts, "label": label})

        # During result, highlight the winner lane name from claim/lastResult.
        if self.phase == "result" and self.last_result:
            wl = int(self.last_result.get("winnerLane") or 0)
            winner_name = self.last_result.get("user") or self.last_result.get("winner")
            if wl and winner_name:
                for lane in lanes_out:
                    if int(lane["id"]) == wl:
                        lane["label"] = winner_name

        self.seq += 1
        payload: dict[str, Any] = {
            "seq": self.seq,
            "state": state,
            "phase": self.phase,
            "maxPoints": int(esp.get("maxPoints") or 15),
            "winner": int(esp.get("winner") or 0) or int((self.last_result or {}).get("winnerLane") or 0),
            "raceId": int(esp.get("raceId") or 0),
            "durationMs": int(
                (self.last_result or {}).get("durationMs")
                if self.phase == "result" and self.last_result
                else (esp.get("durationMs") or 0)
            ),
            "lanes": lanes_out,
            "espConnected": self.phase != "offline",
        }
        if self.phase in ("idle", "offline"):
            payload["stats"] = self.stats.snapshot
        if self.phase == "result" and self.last_result:
            payload["lastResult"] = self.last_result
        claim = self._claim_payload()
        if claim:
            payload["claim"] = claim
        if self.mock_control_url:
            payload["testMode"] = True
        return payload

    async def broadcast(self) -> None:
        if not self.clients:
            self._last_broadcast = json.dumps(self.build_payload())
            return
        msg = json.dumps(self.build_payload())
        self._last_broadcast = msg
        dead = []
        for ws in self.clients:
            try:
                await ws.send(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.clients.discard(ws)

    async def _reply(
        self, ws: WebSocketServerProtocol, request_id: Any, ok: bool, error: str = "", data: Any = None
    ) -> None:
        body: dict[str, Any] = {"ok": ok, "request_id": request_id}
        if error:
            body["error"] = error
        if data is not None:
            body["data"] = data
        await ws.send(json.dumps(body))

    async def _handle_action(self, ws: WebSocketServerProtocol, msg: dict[str, Any]) -> None:
        action = msg.get("action")
        request_id = msg.get("request_id")

        if action == "claim_typing":
            if not self.claim or self.claim.get("claimed"):
                await self._reply(ws, request_id, False, "no_claim")
                return
            if time.time() >= float(self.claim.get("deadline") or 0):
                await self._reply(ws, request_id, False, "expired")
                return
            self.claim["deadline"] = time.time() + self.claim_window_s
            await self._reply(ws, request_id, True)
            await self.broadcast()
            return

        if action == "claim":
            if not self.claim:
                await self._reply(ws, request_id, False, "no_claim")
                return
            if self.claim.get("claimed"):
                await self._reply(ws, request_id, False, "already_claimed")
                return
            if time.time() >= float(self.claim.get("deadline") or 0):
                await self._reply(ws, request_id, False, "expired")
                return

            name = msg.get("name") or ""
            pin = msg.get("pin") or ""
            key = name_key(name) or "_"
            if self._rate_limited(key):
                await self._reply(ws, request_id, False, "rate_limited")
                return

            ok, err, display = register_or_login(self.store, name, pin)
            if not ok:
                if err == "wrong_pin":
                    self._note_fail(key)
                await self._reply(ws, request_id, False, err or "invalid")
                return

            race_id = int(self.claim.get("raceId") or 0)
            if not self.store.set_race_user(race_id, display):
                await self._reply(ws, request_id, False, "no_claim")
                return

            self.stats.rebuild()
            message = self._claim_success_message(display)
            self.claim["claimed"] = True
            self.claim["user"] = display
            self.claim["label"] = display
            self.claim["deadline"] = time.time() + CLAIM_CONFIRM_S

            race = next((r for r in self.store.races if r.get("id") == race_id), None) or {
                "id": race_id,
                "winnerLane": self.claim.get("winnerLane"),
                "durationMs": self.claim.get("durationMs"),
            }
            self.last_result = self._build_last_result(race, user=display, message=message)
            log.info("race %s claimed by %s", race_id, display)
            await self._reply(ws, request_id, True, data={"name": display, "message": message})
            await self.broadcast()
            return

        if action == "ping":
            await self._reply(ws, request_id, True, data={"pong": True})
            return

        if action == "sim_start":
            if not self.mock_control_url:
                await self._reply(ws, request_id, False, "not_available")
                return
            try:
                import urllib.request

                def _hit() -> int:
                    req = urllib.request.Request(self.mock_control_url, method="POST")
                    with urllib.request.urlopen(req, timeout=3) as resp:
                        return int(resp.status)

                status = await asyncio.to_thread(_hit)
                if status >= 400:
                    await self._reply(ws, request_id, False, "busy" if status == 409 else "failed")
                    return
                await self._reply(ws, request_id, True)
            except Exception as e:
                log.warning("sim_start failed: %s", e)
                await self._reply(ws, request_id, False, "failed")
            return

        await self._reply(ws, request_id, False, "unknown_action")

    async def handler(self, ws: WebSocketServerProtocol) -> None:
        self.clients.add(ws)
        try:
            await ws.send(self._last_broadcast or json.dumps(self.build_payload()))
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if isinstance(msg, dict) and msg.get("action"):
                    await self._handle_action(ws, msg)
        finally:
            self.clients.discard(ws)

    async def heartbeat(self) -> None:
        while True:
            await asyncio.sleep(1.0)
            self._apply_phase(self._phase_from_esp())
            await self.broadcast()

    async def run(self) -> None:
        log.info("Kino WS on ws://%s:%s/", self.host, self.port)
        async with websockets.serve(self.handler, self.host, self.port):
            await self.heartbeat()
