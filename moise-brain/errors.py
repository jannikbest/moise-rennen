#!/usr/bin/env python3
"""Structured error list for Moise-Brain."""
import time
import threading
import logging


class ErrorStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._errors = []
        self._next_id = 1
        self.logger = logging.getLogger(__name__)

    def raise_error(self, code, message, source="", severity="error"):
        with self._lock:
            # De-dup active errors with same code+source
            for err in self._errors:
                if err["active"] and err["code"] == code and err["source"] == source:
                    err["message"] = message
                    err["timestamp"] = time.time()
                    return err
            entry = {
                "id": self._next_id,
                "code": code,
                "severity": severity,
                "source": source,
                "message": message,
                "timestamp": time.time(),
                "active": True,
            }
            self._next_id += 1
            self._errors.append(entry)
            self.logger.error(f"[{code}] {source}: {message}")
            return entry

    def clear(self, code=None, source=None):
        with self._lock:
            for err in self._errors:
                if not err["active"]:
                    continue
                if code is not None and err["code"] != code:
                    continue
                if source is not None and err["source"] != source:
                    continue
                err["active"] = False

    def clear_id(self, error_id):
        with self._lock:
            for err in self._errors:
                if err["id"] == error_id:
                    err["active"] = False
                    return True
        return False

    def list_active(self):
        with self._lock:
            return [e.copy() for e in self._errors if e["active"]]

    def list_all(self, limit=50):
        with self._lock:
            return [e.copy() for e in self._errors[-limit:]]
