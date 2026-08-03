"""Persist a finished race by time and winner lane."""

from __future__ import annotations

import time
from typing import Any, Callable, Optional

from store import Store


class Recorder:
    def __init__(
        self,
        store: Store,
        lane_labels: Optional[dict[int, str]] = None,
        on_recorded: Optional[Callable[[], None]] = None,
    ) -> None:
        self.store = store
        self.lane_labels = lane_labels or {}
        self.on_recorded = on_recorded

    def _next_id(self) -> int:
        highest = 0
        for race in self.store.races:
            rid = race.get("id")
            if isinstance(rid, int) and rid > highest:
                highest = rid
        return highest + 1

    def record(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        race = {
            # Own counter: the ESP raceId restarts at 1 after every reboot.
            "id": self._next_id(),
            "espRaceId": int(snapshot.get("raceId") or 0),
            "ts": int(time.time()),
            "durationMs": int(snapshot.get("durationMs") or 0),
            "winnerLane": int(snapshot.get("winner") or 0),
            "user": None,
        }
        self.store.add_race(race)
        if self.on_recorded:
            self.on_recorded()
        return race
