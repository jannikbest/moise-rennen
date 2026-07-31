#!/usr/bin/env python3
"""In-memory runtime snapshot for WebSocket clients."""
import logging
import threading
from enum import Enum


class GameError(Enum):
    NONE = "none"
    COMMUNICATION_ERROR = "communication_error"
    HARDWARE_ERROR = "hardware_error"
    TIMEOUT_ERROR = "timeout_error"


class GameData:
    def __init__(self, game_state, config=None, error_store=None, system_mode=None):
        self.logger = logging.getLogger(__name__)
        self._lock = threading.Lock()
        self.game_state_ref = game_state
        self.config = config
        self.error_store = error_store
        self.system_mode = system_mode

        self.maus_punktzahlen = {}
        self.maus_namen = {}
        self.gewonnen_id = None
        self.gewonnen_zeit = None
        self.game_error = GameError.NONE
        self.error_message = ""
        self.current_game_state = None
        self.controllers_status = []
        self.io_states = {}

    def get_guthaben(self):
        return self.game_state_ref.get_guthaben()

    def get_einzahlungen(self):
        return self.game_state_ref.get_einzahlungen()

    def get_ausgaben(self):
        return self.game_state_ref.get_ausgaben()

    def get_service_gutschriften(self):
        return self.game_state_ref.get_service_gutschriften()

    def get_gespielte_spiele(self):
        return self.game_state_ref.get_gespielte_spiele()

    def get_game_price_cent(self):
        if self.config:
            return self.config.get_game_price_cent()
        return 100

    def set_maus_punktzahl(self, maus_id, punktzahl):
        with self._lock:
            self.maus_punktzahlen[maus_id] = punktzahl

    def get_maus_punktzahl(self, maus_id):
        with self._lock:
            return self.maus_punktzahlen.get(maus_id, 0)

    def get_all_maus_punktzahlen(self):
        with self._lock:
            return {str(k): v for k, v in self.maus_punktzahlen.items()}

    def set_maus_name(self, maus_id, name):
        with self._lock:
            maus_id = int(maus_id)
            for existing_id, existing_name in list(self.maus_namen.items()):
                if existing_name == name and existing_id != maus_id:
                    del self.maus_namen[existing_id]
            self.maus_namen[maus_id] = name

    def get_all_maus_namen(self):
        with self._lock:
            return {str(k): v for k, v in self.maus_namen.items()}

    def reset_maus_namen(self):
        with self._lock:
            self.maus_namen.clear()

    def set_gewonnen_info(self, maus_id, zeit):
        with self._lock:
            self.gewonnen_id = maus_id
            self.gewonnen_zeit = zeit

    def get_gewonnen_id(self):
        with self._lock:
            return self.gewonnen_id

    def get_gewonnen_zeit(self):
        with self._lock:
            return self.gewonnen_zeit

    def set_game_error(self, error, error_message=""):
        with self._lock:
            self.game_error = error
            self.error_message = error_message
        if error != GameError.NONE:
            self.logger.error(error_message or error.value)
            if self.error_store:
                self.error_store.raise_error(
                    error.value, error_message or error.value, source="game"
                )
        elif self.error_store:
            self.error_store.clear(source="game")

    def get_game_error(self):
        with self._lock:
            return self.game_error

    def get_error_message(self):
        with self._lock:
            return self.error_message

    def set_game_state(self, state):
        with self._lock:
            self.current_game_state = state

    def get_game_state(self):
        with self._lock:
            return self.current_game_state

    def set_controllers_status(self, status_list):
        with self._lock:
            self.controllers_status = status_list

    def set_io_states(self, states):
        with self._lock:
            self.io_states = states

    def add_ausgaben(self, betrag):
        return self.game_state_ref.add_ausgaben(betrag)

    def increment_spiele(self):
        return self.game_state_ref.increment_spiele()

    def get_game_summary(self):
        with self._lock:
            errors = self.error_store.list_active() if self.error_store else []
            mode = self.system_mode.get_value() if self.system_mode else "run"
            return {
                "guthaben": self.game_state_ref.get_guthaben(),
                "einzahlungen": self.game_state_ref.get_einzahlungen(),
                "service_gutschriften": self.game_state_ref.get_service_gutschriften(),
                "ausgaben": self.game_state_ref.get_ausgaben(),
                "gespielte_spiele": self.game_state_ref.get_gespielte_spiele(),
                "game_price_cent": self.get_game_price_cent(),
                "game_state": self.current_game_state,
                "system_mode": mode,
                "maus_punktzahlen": {str(k): v for k, v in self.maus_punktzahlen.items()},
                "maus_namen": {str(k): v for k, v in self.maus_namen.items()} or None,
                "gewonnen": {
                    "id": self.gewonnen_id,
                    "Zeit": self.gewonnen_zeit,
                },
                "controllers": list(self.controllers_status),
                "errors": errors,
                "io_states": dict(self.io_states),
                "game_error": self.game_error.value,
                "error_message": self.error_message,
                "lanes": self.config.get_lanes_config() if self.config else [],
            }
