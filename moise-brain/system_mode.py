#!/usr/bin/env python3
"""System-wide mode manager: RUN / CONFIG / DEBUG."""
import logging
from enum import Enum


class SystemMode(Enum):
    RUN = "run"
    CONFIG = "config"
    DEBUG = "debug"


class SystemModeManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.mode = SystemMode.RUN
        self._on_change = []

    def get(self):
        return self.mode

    def get_value(self):
        return self.mode.value

    def on_change(self, callback):
        self._on_change.append(callback)

    def set(self, mode):
        if isinstance(mode, str):
            mode = SystemMode(mode.lower())
        if mode == self.mode:
            return False
        old = self.mode
        self.mode = mode
        self.logger.info(f"System mode: {old.value} -> {mode.value}")
        for cb in self._on_change:
            try:
                cb(old, mode)
            except Exception as e:
                self.logger.error(f"Mode change callback error: {e}")
        return True

    def is_run(self):
        return self.mode == SystemMode.RUN

    def is_debug(self):
        return self.mode == SystemMode.DEBUG

    def is_config(self):
        return self.mode == SystemMode.CONFIG
