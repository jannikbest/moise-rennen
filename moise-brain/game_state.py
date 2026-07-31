#!/usr/bin/env python3
"""Persistent accounting state (cash + service credits)."""
import json
import logging
from pathlib import Path


class GameState:
    def __init__(self, state_file="game_state.json"):
        self.logger = logging.getLogger(__name__)
        self.state_file = state_file
        self.state = self._load_state()

    def _load_state(self):
        try:
            state_path = Path(self.state_file)
            if not state_path.exists():
                return self._get_default_state()
            with open(state_path, "r", encoding="utf-8") as f:
                state = json.load(f)
            # Migrate older files
            state.setdefault("service_gutschriften", 0)
            return state
        except Exception as e:
            self.logger.error(f"State load error: {e}")
            return self._get_default_state()

    def _get_default_state(self):
        return {
            "einzahlungen": 0,
            "ausgaben": 0,
            "gespielte_spiele": 0,
            "freispiel_betrag": 0,
            "service_gutschriften": 0,
        }

    def _save_state(self):
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"State save error: {e}")

    def get_einzahlungen(self):
        return self.state.get("einzahlungen", 0)

    def get_ausgaben(self):
        return self.state.get("ausgaben", 0)

    def get_service_gutschriften(self):
        return self.state.get("service_gutschriften", 0)

    def get_guthaben(self):
        return self.get_einzahlungen() + self.get_service_gutschriften() - self.get_ausgaben()

    def get_gespielte_spiele(self):
        return self.state.get("gespielte_spiele", 0)

    def get_freispiel_betrag(self):
        return self.state.get("freispiel_betrag", 0)

    def add_freispiel(self, betrag):
        """Legacy free-play: credit via service_gutschriften, not cash."""
        self.state["freispiel_betrag"] = self.get_freispiel_betrag() + betrag
        self._save_state()
        # One free game worth of credit — use configured price externally if needed;
        # keep 200 cent default for backward compatibility with support bot.
        self.add_service_gutschrift(200)
        self.logger.info(f"Freispiel +{betrag}, service credit +200")

    def set_einzahlungen(self, value):
        self.state["einzahlungen"] = value
        self._save_state()

    def set_ausgaben(self, value):
        self.state["ausgaben"] = value
        self._save_state()

    def set_service_gutschriften(self, value):
        self.state["service_gutschriften"] = max(0, int(value))
        self._save_state()

    def set_gespielte_spiele(self, value):
        self.state["gespielte_spiele"] = value
        self._save_state()

    def add_einzahlung(self, betrag):
        self.set_einzahlungen(self.get_einzahlungen() + betrag)
        return self.get_einzahlungen()

    def add_ausgaben(self, betrag):
        self.set_ausgaben(self.get_ausgaben() + betrag)
        return self.get_ausgaben()

    def add_service_gutschrift(self, cent):
        cent = int(cent)
        self.set_service_gutschriften(self.get_service_gutschriften() + cent)
        self.logger.info(f"Service credit +{cent} cent (total {self.get_service_gutschriften()})")
        return self.get_service_gutschriften()

    def increment_spiele(self):
        self.set_gespielte_spiele(self.get_gespielte_spiele() + 1)
        return self.get_gespielte_spiele()

    def reset_counters(self):
        self.state["einzahlungen"] = 0
        self.state["ausgaben"] = 0
        self.state["service_gutschriften"] = 0
        self.state["gespielte_spiele"] = 0
        self.state["freispiel_betrag"] = 0
        self._save_state()
        self.logger.info("Accounting counters reset")

    def get_state(self):
        return self.state.copy()
