#!/usr/bin/env python3
"""
Maus-Klasse für Moise-Brain
"""
from enum import Enum
import logging


class MausState(Enum):
    """Zustände der Maus"""
    READY = "ready"
    RACING = "racing"


class Maus:
    """Klasse für eine Maus mit ID 1-4"""
    
    def __init__(self, maus_id):
        """
        Maus initialisieren
        
        Args:
            maus_id (int): ID der Maus (1-4)
        """
        if not 1 <= maus_id <= 4:
            raise ValueError("Maus-ID muss zwischen 1 und 4 liegen")
        
        self.maus_id = maus_id
        self.punktzahl = 0
        self.logger = logging.getLogger(__name__)
    
    def set_ready(self):
        """Maus in Ready-State setzen und Punktzahl zurücksetzen"""
        self.punktzahl = 0
        self.has_won = False
        self.logger.info(f"Maus {self.maus_id} ist bereit (Punktzahl: {self.punktzahl})")
    
    def set_winning(self):
        """Maus als Gewinner markieren"""
        self.has_won = True
        self.logger.info(f"Maus {self.maus_id} hat gewonnen!")
    
    def set_lose(self):
        """Maus als Verlierer markieren"""
        self.logger.info(f"Maus {self.maus_id} hat verloren!")
    
    def has_won_game(self):
        """Prüfen ob die Maus gewonnen hat"""
        return hasattr(self, 'has_won') and self.has_won
    
    def add_points(self, points):
        """Punkte zur Maus hinzufügen"""
        self.punktzahl += points
        self.logger.info(f"Maus {self.maus_id} bekommt {points} Punkte (Gesamt: {self.punktzahl})")
    
    
    def get_info(self):
        """Informationen über die Maus zurückgeben"""
        return {
            'id': self.maus_id,
            'punktzahl': self.punktzahl
        } 