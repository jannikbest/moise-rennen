"""Fernet-encrypted JSON store with atomic writes."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken


class Store:
    def __init__(self, path: Path, key: str) -> None:
        if not key:
            raise ValueError("MOISE_STATS_KEY is empty")
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fernet = Fernet(key.encode() if isinstance(key, str) else key)
        self._data: dict[str, Any] = {"users": {}, "races": []}
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            self._data = {"users": {}, "races": []}
            self.save()
            return
        raw = self.path.read_bytes()
        try:
            plain = self._fernet.decrypt(raw)
        except InvalidToken as e:
            raise RuntimeError(f"Cannot decrypt {self.path} — wrong key?") from e
        self._data = json.loads(plain.decode("utf-8"))
        self._data.setdefault("users", {})
        self._data.setdefault("races", [])

    def save(self) -> None:
        blob = self._fernet.encrypt(json.dumps(self._data, separators=(",", ":")).encode("utf-8"))
        fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), prefix=".moise-", suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(blob)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.path)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    @property
    def users(self) -> dict[str, Any]:
        return self._data["users"]

    @property
    def races(self) -> list[dict[str, Any]]:
        return self._data["races"]

    def add_race(self, race: dict[str, Any]) -> None:
        self._data["races"].append(race)
        self.save()

    def set_race_user(self, race_id: int, user: str) -> bool:
        for race in self._data["races"]:
            if race.get("id") == race_id:
                race["user"] = user
                self.save()
                return True
        return False

    def set_user(self, key: str, record: dict[str, Any]) -> None:
        self._data["users"][key] = record
        self.save()
