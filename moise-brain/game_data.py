#!/usr/bin/env python3
"""
Game-Data-Modul für Moise-Brain
"""
import logging
from enum import Enum


class GameError(Enum):
    NONE = "none"
    COMMUNICATION_ERROR = "communication_error"
    HARDWARE_ERROR = "hardware_error"
    TIMEOUT_ERROR = "timeout_error"


class GameData:
    def __init__(self, game_state):
        self.logger = logging.getLogger(__name__)
        self.game_state_ref = game_state
        
        self.maus_punktzahlen = {}
        self.gewonnene_maus = None
        self.game_error = GameError.NONE
        self.error_message = ""
        self.current_game_state = None
        
        self.logger.info("Game-Data initialisiert")
    
    def get_guthaben(self):
        return self.game_state_ref.get_guthaben()
    
    def get_einzahlungen(self):
        return self.game_state_ref.get_einzahlungen()
    
    def get_ausgaben(self):
        return self.game_state_ref.get_ausgaben()
    
    def get_gespielte_spiele(self):
        return self.game_state_ref.get_gespielte_spiele()
    
    def set_maus_punktzahl(self, maus_id, punktzahl):
        self.maus_punktzahlen[maus_id] = punktzahl
    
    def get_maus_punktzahl(self, maus_id):
        return self.maus_punktzahlen.get(maus_id, 0)
    
    def get_all_maus_punktzahlen(self):
        return self.maus_punktzahlen.copy()
    
    def set_gewonnene_maus(self, maus_id):
        self.gewonnene_maus = maus_id
    
    def get_gewonnene_maus(self):
        return self.gewonnene_maus
    
    def set_game_error(self, error, error_message=""):
        self.game_error = error
        self.error_message = error_message
        
        if error != GameError.NONE:
            if error_message:
                self.logger.error(f"Spiel-Fehler: {error_message}")
            else:
                self.logger.error(f"Spiel-Fehler: {error.value}")
    
    def get_game_error(self):
        return self.game_error
    
    def get_error_message(self):
        return self.error_message
    
    def has_error(self):
        return self.game_error != GameError.NONE
    
    def set_game_state(self, state):
        self.current_game_state = state
    
    def get_game_state(self):
        return self.current_game_state
    
    def reset_game_data(self):
        self.maus_punktzahlen.clear()
        self.gewonnene_maus = None
        self.game_error = GameError.NONE
        self.error_message = ""
        self.current_game_state = None
    
    def get_game_summary(self):
        return {
            'guthaben': self.get_guthaben(),
            'gespielte_spiele': self.get_gespielte_spiele(),
            'game_state': self.get_game_state(),
            'maus_punktzahlen': self.get_all_maus_punktzahlen(),
            'gewonnene_maus': self.get_gewonnene_maus(),
            'game_error': self.get_game_error().value,
            'error_message': self.get_error_message()
        }
    
    def add_ausgaben(self, betrag):
        return self.game_state_ref.add_ausgaben(betrag)
    
    def increment_spiele(self):
        return self.game_state_ref.increment_spiele() 