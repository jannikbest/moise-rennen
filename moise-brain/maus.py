#!/usr/bin/env python3
"""Maus / lane model."""
import logging


class Maus:
    def __init__(self, maus_id, name=None):
        if maus_id < 1:
            raise ValueError("Maus-ID must be >= 1")
        self.maus_id = maus_id
        self.name = name
        self.punktzahl = 0
        self.has_won = False
        self.game_ref = None
        self.logger = logging.getLogger(__name__)

    def set_ready(self):
        self.punktzahl = 0
        self.has_won = False

    def set_winning(self):
        self.has_won = True
        self.logger.info(f"Maus {self.maus_id} won")

    def set_lose(self):
        pass

    def has_won_game(self):
        return self.has_won

    def add_points(self, points):
        self.punktzahl += points
        self.logger.info(f"Maus {self.maus_id} +{points} (total {self.punktzahl})")
        if self.game_ref:
            self.game_ref.update_point_time()

    def get_info(self):
        return {"id": self.maus_id, "punktzahl": self.punktzahl, "name": self.name}
