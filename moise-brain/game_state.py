#!/usr/bin/env python3
"""
Game-State-Modul für Moise-Brain
"""
import json
import logging
from pathlib import Path


class GameState:
    """Klasse zum Laden und Speichern des Spielzustands"""
    
    def __init__(self, state_file="game_state.json"):
        """
        Game-State initialisieren
        
        Args:
            state_file (str): Pfad zur JSON-State-Datei
        """
        self.logger = logging.getLogger(__name__)
        self.state_file = state_file
        self.state = self._load_state()
    
    def _load_state(self):
        """JSON-State-Datei laden"""
        try:
            state_path = Path(self.state_file)
            if not state_path.exists():
                self.logger.info(f"State-Datei {self.state_file} nicht gefunden - erstelle Standard")
                return self._get_default_state()
            
            with open(state_path, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            self.logger.info(f"Spielzustand aus {self.state_file} geladen")
            return state
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Fehler beim Parsen der State-Datei: {e}")
            return self._get_default_state()
        except Exception as e:
            self.logger.error(f"Fehler beim Laden des Spielzustands: {e}")
            return self._get_default_state()
    
    def _get_default_state(self):
        """Standard-Spielzustand zurückgeben"""
        return {
            "einzahlungen": 0,
            "ausgaben": 0,
            "gespielte_spiele": 0
        }
    
    def _save_state(self):
        """Spielzustand in Datei speichern"""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
            
            self.logger.debug(f"Spielzustand in {self.state_file} gespeichert")
            
        except Exception as e:
            self.logger.error(f"Fehler beim Speichern des Spielzustands: {e}")
    
    def get_einzahlungen(self):
        """Einzahlungen zurückgeben"""
        return self.state.get("einzahlungen", 0)
    
    def get_ausgaben(self):
        """Ausgaben zurückgeben"""
        return self.state.get("ausgaben", 0)
    
    def get_guthaben(self):
        """Guthaben als Differenz zwischen Einzahlungen und Ausgaben berechnen"""
        return self.get_einzahlungen() - self.get_ausgaben()
    
    def get_gespielte_spiele(self):
        """Anzahl gespielte Spiele zurückgeben"""
        return self.state.get("gespielte_spiele", 0)
    
    def set_einzahlungen(self, einzahlungen):
        """Einzahlungen setzen und speichern"""
        self.state["einzahlungen"] = einzahlungen
        self._save_state()
        self.logger.info(f"Einzahlungen auf {einzahlungen} gesetzt")
    
    def set_ausgaben(self, ausgaben):
        """Ausgaben setzen und speichern"""
        self.state["ausgaben"] = ausgaben
        self._save_state()
        self.logger.info(f"Ausgaben auf {ausgaben} gesetzt")
    
    def set_gespielte_spiele(self, spiele):
        """Anzahl gespielte Spiele setzen und speichern"""
        self.state["gespielte_spiele"] = spiele
        self._save_state()
        self.logger.info(f"Gespielte Spiele auf {spiele} gesetzt")
    
    def add_einzahlung(self, betrag):
        """Einzahlung hinzufügen"""
        neue_einzahlungen = self.get_einzahlungen() + betrag
        self.set_einzahlungen(neue_einzahlungen)
        return neue_einzahlungen
    
    def add_ausgaben(self, betrag):
        """Ausgaben erhöhen"""
        neue_ausgaben = self.get_ausgaben() + betrag
        self.set_ausgaben(neue_ausgaben)
        return neue_ausgaben
    
    def increment_spiele(self):
        """Anzahl gespielte Spiele um 1 erhöhen"""
        neue_spiele = self.get_gespielte_spiele() + 1
        self.set_gespielte_spiele(neue_spiele)
        return neue_spiele
    
    def get_state(self):
        """Kompletten Spielzustand zurückgeben"""
        return self.state.copy()
    
    def reset_state(self):
        """Spielzustand zurücksetzen"""
        self.state = self._get_default_state()
        self._save_state()
        self.logger.info("Spielzustand zurückgesetzt") 