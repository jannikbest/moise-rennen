#!/usr/bin/env python3
"""
Game-Klasse für Moise-Brain mit State Machine
"""
import logging
import time
from enum import Enum


class GameState(Enum):
    """Spiel-Zustände"""
    STARTUP = "startup"
    WAIT_FOR_READY = "wait_for_ready"
    WAIT_FOR_CONTROLLER_RESPONSE = "wait_for_controller_response"
    READY = "ready"
    RACING = "racing"
    FINISHED = "finished"
    ERROR = "error"


class Game:
    """Klasse für das Spiel-Management mit State Machine"""
    
    def __init__(self, logger, game_data=None):
        """
        Game initialisieren
        
        Args:
            logger: Logger-Instanz
        """
        self.logger = logger
        self.current_state = GameState.STARTUP
        self.controllers = []
        self.maeuse = []
        self.wait_start_time = None  # Zeitstempel für WAIT_FOR_READY
        self.finished_start_time = None  # Zeitstempel für FINISHED
        self.controller_response_start_time = None  # Zeitstempel für WAIT_FOR_CONTROLLER_RESPONSE
        self.game_data = game_data
        
        self.logger.info("Game mit State Machine initialisiert")
        self.logger.info(f"Aktueller Zustand: {self.current_state.value}")
    
    def add_controller(self, controller):
        """Controller zum Spiel hinzufügen"""
        self.controllers.append(controller)
        # Mäuse des Controllers zur Gesamtliste hinzufügen
        self.maeuse.extend(controller.maeuse)
        self.logger.info(f"Controller {controller.port_number} mit {len(controller.maeuse)} Mäusen hinzugefügt")
    
    def set_state(self, new_state):
        """Zustand ändern"""
        old_state = self.current_state
        self.current_state = new_state
        self.logger.info(f"Game-Zustand geändert: {old_state.value} -> {new_state.value}")
    
    def get_current_state(self):
        """Aktuellen Zustand zurückgeben"""
        return self.current_state
    
    def cycleUpdate(self):
        """Update-Zyklus basierend auf aktuellem Zustand"""
        if self.current_state == GameState.STARTUP:
            self._handle_startup()
        elif self.current_state == GameState.WAIT_FOR_READY:
            self._handle_wait_for_ready()
        elif self.current_state == GameState.WAIT_FOR_CONTROLLER_RESPONSE:
            self._handle_wait_for_controller_response()
        elif self.current_state == GameState.READY:
            self._handle_ready()
        elif self.current_state == GameState.RACING:
            self._handle_racing()
        elif self.current_state == GameState.FINISHED:
            self._handle_finished()
        elif self.current_state == GameState.ERROR:
            self._handle_error()
    
    def _handle_startup(self):
        """Startup-Zustand behandeln"""
        # Wechsel zu WAIT_FOR_READY
        self.set_state(GameState.WAIT_FOR_READY)
    
    def _handle_wait_for_ready(self):
        """Wait for Ready-Zustand behandeln"""
        # Zeitstempel setzen wenn erstmalig in diesem State
        if self.wait_start_time is None:
            self.wait_start_time = time.time()
            self.logger.info("Starte Warten auf Controller Ready-Status")
            # Sende "home" nur an Controller die nicht ready sind
            for controller in self.controllers:
                if controller.state.value != "isReady":
                    controller.sendCommand("home")
        
        # Prüfe ob alle Controller ready sind
        all_ready = True
        for controller in self.controllers:
            if controller.state.value != "isReady":
                all_ready = False
        
        if all_ready:
            # Alle Controller sind ready
            self.logger.info("Alle Controller sind ready - wechsle zu READY")
            self.set_state(GameState.READY)
            self.wait_start_time = None
        else:
            # Prüfe Timeout (10 Sekunden)
            if time.time() - self.wait_start_time > 10:
                self.logger.info("10 Sekunden Timeout - wechsle zu WAIT_FOR_CONTROLLER_RESPONSE")
                self.set_state(GameState.WAIT_FOR_CONTROLLER_RESPONSE)
                self.wait_start_time = None
    
    def _handle_ready(self):
        """Ready-Zustand behandeln"""
        # Sende "go" an beide Controller und wechsle zu RACING
        for controller in self.controllers:
            controller.sendCommand("go")
        
        self.logger.info("Sende 'go' an alle Controller - wechsle zu RACING")
        self.set_state(GameState.RACING)
    
    def _handle_racing(self):
        """Racing-Zustand behandeln"""
        # Prüfe ob eine Maus gewonnen hat
        winner = None
        for maus in self.maeuse:
            if maus.has_won_game():
                winner = maus
                break
        
        if winner:
            # Gewinner gefunden - sende "lose" nur an Controller ohne Gewinner-Maus
            for controller in self.controllers:
                # Prüfe ob der Controller die Gewinner-Maus hat
                has_winner = winner in controller.maeuse
                if not has_winner:
                    controller.sendCommand("lose")
            
            # Spiel beendet - Anzahl Spiele erhöhen
            if self.game_data:
                self.game_data.increment_spiele()
            self.set_state(GameState.FINISHED)
    
    def _handle_finished(self):
        """Finished-Zustand behandeln"""
        # Zeitstempel setzen wenn erstmalig in diesem State
        if self.finished_start_time is None:
            self.finished_start_time = time.time()
            self.logger.info("Starte Warten auf FINISHED-Status")
        
        # Prüfe Timeout (3 Sekunden)
        if time.time() - self.finished_start_time > 3:
            self.logger.info("Timeout: FINISHED-Status erreicht - wechsle zu WAIT_FOR_READY")
            self.set_state(GameState.WAIT_FOR_READY)
            self.finished_start_time = None
    
    def _handle_error(self):
        """Error-Zustand behandeln"""
        # Error-Logik hier implementieren
        pass
    
    def reset_game(self):
        """Spiel zurücksetzen - alle Mäuse auf ready"""
        results = []
        for maus in self.maeuse:
            result = maus.set_ready()
            results.append(result)
        
        for result in results:
            self.logger.info(result)
    
    def get_maus_info(self):
        """Informationen über alle Mäuse zurückgeben"""
        info = []
        for maus in self.maeuse:
            maus_info = maus.get_info()
            maus_info['has_won'] = maus.has_won_game()
            info.append(maus_info)
        return info
    
    def get_game_info(self):
        """Informationen über das Spiel zurückgeben"""
        return {
            'state': self.current_state.value,
            'controllers_count': len(self.controllers),
            'mice_count': len(self.maeuse),
            'mice_info': self.get_maus_info()
        } 

    def _handle_wait_for_controller_response(self):
        """Wait for Controller Response-Zustand behandeln"""
        # Zeitstempel setzen wenn erstmalig in diesem State
        if self.controller_response_start_time is None:
            self.controller_response_start_time = time.time()
            self.logger.info("Starte Warten auf Controller Response")
            
            # Rufe checkState für nicht-ready Controller auf
            for controller in self.controllers:
                if controller.state.value != "isReady":
                    controller.checkState()
        
        # Prüfe ob alle Controller ready sind
        all_ready = True
        for controller in self.controllers:
            if controller.state.value != "isReady":
                all_ready = False
        
        if all_ready:
            # Alle Controller sind ready
            self.logger.info("Alle Controller sind ready nach Response - wechsle zu READY")
            self.set_state(GameState.READY)
            self.controller_response_start_time = None
        else:
            # Prüfe Timeout (2 Sekunden)
            if time.time() - self.controller_response_start_time > 2:
                self.logger.error("Controller Response Timeout - wechsle zu ERROR")
                self.set_state(GameState.ERROR)
                self.controller_response_start_time = None 