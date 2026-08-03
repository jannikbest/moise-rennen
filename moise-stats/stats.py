"""Aggregate race history into time-based leaderboards and stats cards."""

from __future__ import annotations

import time
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from store import Store

IDLE_STATES = {"homing", "ready", "config"}


def _fmt_ms(ms: int) -> str:
    return f"{max(0, ms) / 1000:.1f}s"


def _race_user(race: dict) -> Optional[str]:
    """Prefer the new top-level user; fall back to winner lane in legacy records."""
    user = race.get("user")
    if user:
        return str(user)
    wl = race.get("winnerLane")
    for lane in race.get("lanes") or []:
        if lane.get("lane") == wl and lane.get("user"):
            return str(lane["user"])
    return None


def _winner_display(race: dict, lane_labels: Optional[Dict[int, str]] = None) -> str:
    user = _race_user(race)
    if user:
        return user
    wl = int(race.get("winnerLane") or 0)
    for lane in race.get("lanes") or []:
        if lane.get("lane") == wl and lane.get("label"):
            return str(lane["label"])
    if wl and lane_labels and wl in lane_labels:
        return lane_labels[wl]
    return f"Mouse {wl}" if wl else "—"


class StatsEngine:
    def __init__(self, store: Store, lane_labels: Optional[Dict[int, str]] = None) -> None:
        self.store = store
        self.lane_labels = lane_labels or {}
        self._cache: dict[str, Any] = {}
        self.rebuild()

    def rebuild(self) -> dict[str, Any]:
        self._cache = compute_stats(self.store.races, self.lane_labels)
        return self._cache

    @property
    def snapshot(self) -> dict[str, Any]:
        return self._cache


def compute_stats(races: List[dict], lane_labels: Optional[Dict[int, str]] = None) -> dict[str, Any]:
    lane_labels = lane_labels or {}
    total_races = len(races)
    games_by_hour = Counter()

    player_wins: Dict[str, int] = defaultdict(int)
    player_best: Dict[str, int] = {}
    player_sum: Dict[str, int] = defaultdict(int)

    best: Optional[dict] = None
    durations: List[int] = []
    ticker: List[dict] = []

    ordered = sorted(races, key=lambda r: r.get("ts", 0))

    for race in ordered:
        duration = int(race.get("durationMs") or 0)
        ts = int(race.get("ts") or 0)
        hour = datetime.fromtimestamp(ts).hour if ts else 0
        games_by_hour[hour] += 1

        if duration > 0:
            durations.append(duration)
            who = _winner_display(race, lane_labels)
            if best is None or duration < best["durationMs"]:
                best = {"durationMs": duration, "winner": who, "raceId": race.get("id")}

        user = _race_user(race)
        if user and duration > 0:
            player_wins[user] += 1
            player_sum[user] += duration
            if user not in player_best or duration < player_best[user]:
                player_best[user] = duration

    for race in reversed(ordered[-5:]):
        ticker.append(
            {
                "raceId": race.get("id"),
                "durationMs": race.get("durationMs"),
                "winner": _winner_display(race, lane_labels),
                "winnerLane": race.get("winnerLane"),
                "ts": race.get("ts"),
            }
        )

    avg_ms = round(sum(durations) / len(durations)) if durations else 0

    def top_times(n: int = 10) -> List[dict]:
        items = sorted(player_best.items(), key=lambda kv: (kv[1], kv[0]))[:n]
        return [{"name": k, "value": v, "display": _fmt_ms(v)} for k, v in items]

    def top_wins(n: int = 10) -> List[dict]:
        items = sorted(player_wins.items(), key=lambda kv: (-kv[1], kv[0]))[:n]
        return [{"name": k, "value": v} for k, v in items if v]

    def top_avg(n: int = 10, min_wins: int = 3) -> List[dict]:
        rows = []
        for name, wins in player_wins.items():
            if wins < min_wins:
                continue
            avg = round(player_sum[name] / wins)
            rows.append({"name": name, "value": avg, "display": _fmt_ms(avg), "wins": wins})
        rows.sort(key=lambda r: (r["value"], r["name"]))
        return rows[:n]

    times_board = top_times()
    wins_board = top_wins()
    avg_board = top_avg()

    peak_hour = games_by_hour.most_common(1)[0] if games_by_hour else (None, 0)
    games_by_hour_list = [int(games_by_hour.get(h, 0)) for h in range(24)]

    cards = _build_cards(
        total_races=total_races,
        best=best,
        avg_ms=avg_ms,
        top_times=times_board,
        top_wins=wins_board,
        games_by_hour=games_by_hour_list,
        peak_hour=peak_hour,
    )
    detail = _build_detail(
        times=times_board,
        wins=wins_board,
        avg_times=avg_board,
        games_by_hour=games_by_hour_list,
        ticker=ticker,
        best=best,
        total_races=total_races,
        avg_ms=avg_ms,
    )

    return {
        "totalRaces": total_races,
        "best": best,
        "avgMs": avg_ms,
        "peakHourGames": {"hour": peak_hour[0], "count": peak_hour[1]},
        "gamesByHour": games_by_hour_list,
        "leaderboards": {
            "times": times_board,
            "wins": wins_board,
            "avgTimes": avg_board,
        },
        "ticker": ticker,
        "cards": cards,
        "detail": detail,
        "updatedAt": int(time.time()),
    }


def _build_cards(**kw: Any) -> List[dict]:
    cards: List[dict] = []
    best = kw.get("best")
    overview_lines = [f"{kw['total_races']} races"]
    if best:
        overview_lines.append(f"Record: {_fmt_ms(best['durationMs'])} · {best.get('winner') or '—'}")
    if kw.get("avg_ms"):
        overview_lines.append(f"Avg {_fmt_ms(kw['avg_ms'])}")
    cards.append({"id": "overview", "title": "Moise Arena", "lines": overview_lines})

    times = kw.get("top_times") or []
    if times:
        lines = [f"{i + 1}. {e['name']} · {e['display']}" for i, e in enumerate(times[:5])]
        cards.append({"id": "times", "title": "Best Times", "lines": lines, "kind": "list"})

    wins = kw.get("top_wins") or []
    if wins:
        lines = [f"{i + 1}. {e['name']} · {e['value']} wins" for i, e in enumerate(wins[:5])]
        cards.append({"id": "wins", "title": "Most Wins", "lines": lines, "kind": "list"})

    hours = kw.get("games_by_hour") or []
    if any(hours):
        peak_h = max(range(24), key=lambda h: hours[h]) if hours else 0
        cards.append(
            {
                "id": "hour_chart",
                "title": "When do people play?",
                "kind": "chart",
                "hours": hours,
                "lines": [f"Peak: {peak_h:02d}:00 · {hours[peak_h]} games"],
            }
        )

    return cards


def _build_detail(**kw: Any) -> List[dict]:
    detail: List[dict] = []
    best = kw.get("best")
    overview_rows = [{"rank": None, "name": "Total races", "value": str(kw.get("total_races") or 0)}]
    if best:
        overview_rows.append(
            {
                "rank": None,
                "name": f"Record · {best.get('winner') or '—'}",
                "value": _fmt_ms(best["durationMs"]),
            }
        )
    if kw.get("avg_ms"):
        overview_rows.append({"rank": None, "name": "Average", "value": _fmt_ms(kw["avg_ms"])})
    detail.append({"title": "Overview", "kind": "list", "rows": overview_rows})

    times = kw.get("times") or []
    if times:
        detail.append(
            {
                "title": "Best Times",
                "kind": "list",
                "rows": [
                    {"rank": i + 1, "name": e["name"], "value": e["display"]}
                    for i, e in enumerate(times)
                ],
            }
        )

    wins = kw.get("wins") or []
    if wins:
        detail.append(
            {
                "title": "Most Wins",
                "kind": "list",
                "rows": [
                    {"rank": i + 1, "name": e["name"], "value": f"{e['value']}"}
                    for i, e in enumerate(wins)
                ],
            }
        )

    avg_times = kw.get("avg_times") or []
    if avg_times:
        detail.append(
            {
                "title": "Best avg time (3+ wins)",
                "kind": "list",
                "rows": [
                    {"rank": i + 1, "name": e["name"], "value": e["display"]}
                    for i, e in enumerate(avg_times)
                ],
            }
        )

    hours = kw.get("games_by_hour") or []
    if any(hours):
        detail.append({"title": "When do people play?", "kind": "chart", "hours": hours, "rows": []})

    ticker = kw.get("ticker") or []
    if ticker:
        detail.append(
            {
                "title": "Recent",
                "kind": "list",
                "rows": [
                    {
                        "rank": None,
                        "name": t.get("winner") or "—",
                        "value": _fmt_ms(int(t.get("durationMs") or 0)),
                    }
                    for t in ticker
                ],
            }
        )

    return detail
