#!/usr/bin/env python3
"""
Moise-Controller - Serielle Schnittstelle für den Controller
"""
import platform
from enum import Enum
from serial_interface import SerialInterface


class ControllerState(Enum):
    """Controller-Zustände"""
    NOTREADY = "notReady"
    PENDING = "pending"
    ISREADY = "isReady"
    UNKNOWN = "unknown"
    ERROR = "error"


class MoiseController:
    """Klasse für die Kommunikation mit dem Moise-Controller"""
    
    def __init__(self, port_number, maeuse=None):
        self.port_number = port_number
        self.serial_interface = None
        self.maeuse = maeuse or []  # Liste der Mäuse, die an diesem Controller hängen
        self.state = ControllerState.NOTREADY  # Controller State
        
        # Logger erstellen
        import logging
        self.logger = logging.getLogger(__name__)
        
        # Port je nach System generieren
        if platform.system() == "Darwin":  # macOS
            # Versuche beide Formate: mit führenden Nullen und ohne
            self.port = f'/dev/tty.usbserial-{port_number:04d}'
            self.port_alt = f'/dev/tty.usbserial-{port_number}'
        else:  # Linux/Raspberry Pi
            self.port = f'/dev/ttyUSB{port_number}'
            self.port_alt = None
    
    def init(self):
        """Serielle Schnittstelle öffnen"""
        # SerialInterface mit einem Dummy-Logger erstellen
        class DummyLogger:
            def info(self, msg): pass
            def debug(self, msg): pass
            def error(self, msg): print(f"ERROR: {msg}")
        
        # Versuche zuerst den primären Port
        self.serial_interface = SerialInterface(DummyLogger(), self.port)
        if self.serial_interface.open_connection():
            return True
        
        # Falls das fehlschlägt und ein alternativer Port existiert, versuche diesen
        if self.port_alt:
            self.serial_interface = SerialInterface(DummyLogger(), self.port_alt)
            if self.serial_interface.open_connection():
                self.port = self.port_alt  # Verwende den erfolgreichen Port
                return True
        
        return False
    
    def input(self):
        """Nicht-blockierendes Lesen von seriellen Daten"""
        if self.serial_interface:
            data = self.serial_interface.read_data()
            if data and self.maeuse:
                # Spezielle Kommandos verarbeiten
                if data == "ready":
                    # Controller als ready markieren
                    self.state = ControllerState.ISREADY
                    # Alle Mäuse in Ready-State setzen
                    results = []
                    for maus in self.maeuse:
                        result = maus.set_ready()
                        results.append(result)
                    return results
                elif data == "no":
                    # Controller als notReady markieren
                    self.state = ControllerState.NOTREADY
                    return []
                elif data.startswith("Error"):
                    # Controller als error markieren
                    self.logger.error(f"Controller {self.port_number}, error message : {data}")
                    self.state = ControllerState.ERROR
                    return []
                elif data == "win1" and len(self.maeuse) >= 1:
                    # Erste Maus als Gewinner markieren
                    result = self.maeuse[0].set_winning()
                    self.state = ControllerState.NOTREADY
                    return [result]
                elif data == "win2" and len(self.maeuse) >= 2:
                    # Zweite Maus als Gewinner markieren
                    result = self.maeuse[1].set_winning()
                    self.state = ControllerState.NOTREADY
                    return [result]
                elif data in ["11", "12", "13"] and len(self.maeuse) >= 1:
                    # Erste Maus bekommt Punkte
                    points = int(data[1])  # Extrahiere die Punktzahl aus dem Kommando
                    result = self.maeuse[0].add_points(points)
                    self.state = ControllerState.NOTREADY
                    return [result]
                elif data in ["21", "22", "23"] and len(self.maeuse) >= 2:
                    # Zweite Maus bekommt Punkte
                    points = int(data[1])  # Extrahiere die Punktzahl aus dem Kommando
                    result = self.maeuse[1].add_points(points)
                    self.state = ControllerState.NOTREADY
                    return [result]
                else:
                    self.state = ControllerState.UNKNOWN
                    self.logger.info(f"Controller {self.port_number}, unknown input message : {data}")
            return data
        return None
    
    def close(self):
        """Serielle Schnittstelle schließen"""
        if self.serial_interface:
            self.serial_interface.close_connection()
    
    def cycleUpdate(self):
        """Controller-Cycle-Update"""
        # Hier können Controller-spezifische Updates gemacht werden
        # Aktuell leer, kann später erweitert werden
        pass
    
    def sendCommand(self, command):
        """Kommando an Controller senden"""
        if self.serial_interface:
            self.serial_interface.send_data(command)
            self.state = ControllerState.UNKNOWN # Setze State auf UNKNOWN nach dem Senden
            return True
        return False
    
    def checkState(self):
        """Controller State prüfen und ggf. "ready?" senden"""
        # Sende "ready?" und setze State auf PENDING
        if self.serial_interface:
            self.serial_interface.send_data("ready?")
            self.state = ControllerState.PENDING 