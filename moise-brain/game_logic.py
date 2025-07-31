#!/usr/bin/env python3
"""
Spiel-Logik für Moise-Brain
"""
import time
from enum import Enum


class State(Enum):
    """Zustände der Statemachine"""
    STARTUP = "startup"
    WAITING_FOR_READY = "waiting_for_ready"
    WAIT_5_SEC = "wait_5_sec"
    READY = "ready"
    RACING = "racing"
    ERROR = "error"


class GameLogic:
    """Klasse für die Spiel-Logik und Statemachine"""
    
    def __init__(self, logger, serial_interface):
        self.current_state = State.STARTUP
        self.wait_timer = 0
        self.ready_attempts = 0
        self.logger = logger
        self.serial_interface = serial_interface
    
    def on_command(self, command):
        """Kommando von Controller verarbeiten"""
        # Prüfen ob Kommando lesbar ist (nur ASCII, keine Steuerzeichen)
        try:
            # Prüfen ob alle Zeichen druckbar sind
            if not all(c.isprintable() or c.isspace() for c in command):
                self.logger.debug(f"Unlesbares Kommando ignoriert: {repr(command)}")
                return
            
            # Leere Kommandos ignorieren
            if not command.strip():
                return
                
        except Exception:
            self.logger.debug(f"Kaputtes Kommando ignoriert: {repr(command)}")
            return
        
        self.logger.info(f"Kommando empfangen: {command}")
        
        if self.current_state == State.WAITING_FOR_READY:
            if command == "ready":
                self.logger.info("Controller ist bereit! -> State: READY")
                self.ready_attempts = 0
                self.current_state = State.READY
            elif command == "no":
                if self.ready_attempts >= 2:
                    self.logger.warning("Controller nach 2 Versuchen nicht bereit, sende Reset")
                    self.serial_interface.send_command("reset")
                    self.ready_attempts = 0
                    self.current_state = State.WAITING_FOR_READY
                else:
                    self.logger.info(f"Controller noch nicht bereit (Versuch {self.ready_attempts}) -> State: WAIT_5_SEC")
                    self.current_state = State.WAIT_5_SEC
                    self.wait_timer = time.time() + 5.0
            elif command == "error":
                self.logger.warning("Controller meldet Fehler, sende Reset")
                self.serial_interface.send_command("reset")
                self.ready_attempts = 0
                self.current_state = State.WAITING_FOR_READY
            else:
                self.current_state = State.WAIT_5_SEC
                self.wait_timer = time.time() + 5.0
        elif self.current_state == State.RACING:
            if command == "win1":
                pass
            elif command == "win2":
                pass
            elif command == "11":
                pass
            elif command == "12":
                pass
            elif command == "13":
                pass
            elif command == "24":
                pass
            elif command == "22":
                pass
            elif command == "23":
                pass
    
    def update(self):
        """Update-Funktion mit Statemachine"""
        if self.current_state == State.STARTUP:
            self.ready_attempts = 1
            self.logger.info("Startup: Frage Controller ob ready... -> State: WAITING_FOR_READY")
            self.serial_interface.send_command("ready?")
            self.current_state = State.WAITING_FOR_READY
            
        elif self.current_state == State.WAIT_5_SEC:
            # 5 Sekunden warten bevor nochmal fragen
            if time.time() >= self.wait_timer:
                self.ready_attempts += 1
                self.logger.info(f"5 Sekunden vorbei, frage nochmal nach ready (Versuch {self.ready_attempts}) -> State: WAITING_FOR_READY")
                self.serial_interface.send_command("ready?")
                self.current_state = State.WAITING_FOR_READY
                
        elif self.current_state == State.READY:
            # Nicht-blockierende Eingabe prüfen
            print("Bereit! Gib 'go' ein und drücke Enter zum Starten.")
            
            # Direkten input() benutzen (nicht in Hauptschleife, nur zur Demo)
            user_input = input("> ")
            if user_input.strip().lower() == "go":
                self.logger.info("Starte Rennen! -> State: RACING")
                self.serial_interface.send_command("go")
                self.current_state = State.RACING
                
        elif self.current_state == State.RACING:
            # Racing state
            pass
    
    def get_current_state(self):
        """Aktuellen State zurückgeben"""
        return self.current_state 