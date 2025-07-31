#!/usr/bin/env python3
"""
Config-Modul für Moise-Brain
"""
import json
import logging
from pathlib import Path


class Config:
    """Klasse zum Laden und Verwalten der Konfiguration"""
    
    def __init__(self, config_file="config.json"):
        """
        Konfiguration laden
        
        Args:
            config_file (str): Pfad zur JSON-Konfigurationsdatei
        """
        self.logger = logging.getLogger(__name__)
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self):
        """JSON-Konfigurationsdatei laden"""
        try:
            config_path = Path(self.config_file)
            if not config_path.exists():
                self.logger.error(f"Konfigurationsdatei {self.config_file} nicht gefunden!")
                return self._get_default_config()
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            self.logger.info(f"Konfiguration aus {self.config_file} geladen")
            return config
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Fehler beim Parsen der JSON-Konfiguration: {e}")
            return self._get_default_config()
        except Exception as e:
            self.logger.error(f"Fehler beim Laden der Konfiguration: {e}")
            return self._get_default_config()
    
    def _get_default_config(self):
        """Standard-Konfiguration zurückgeben"""
        self.logger.warning("Verwende Standard-Konfiguration")
        return {
            "mice": {
                "count": 4,
                "max_id": 4
            },
            "controllers": [
                {
                    "id": 1,
                    "name": "Controller 1",
                    "serial_port": "/dev/ttyUSB0",
                    "baud_rate": 9600,
                    "timeout": 1.0
                }
            ],
            "coin_counter": {
                "gpio_pin": 18
            }
        }
    
    def get_mice_config(self):
        """Mäuse-Konfiguration zurückgeben"""
        return self.config.get("mice", {})
    
    def get_controllers_config(self):
        """Controller-Konfiguration zurückgeben"""
        return self.config.get("controllers", [])
    
    def get_coin_counter_config(self):
        """Münzzähler-Konfiguration zurückgeben"""
        return self.config.get("coin_counter", {})
    
    def get_mice_count(self):
        """Anzahl der Mäuse zurückgeben"""
        return self.get_mice_config().get("count", 4)
    
    def get_max_mice_id(self):
        """Maximale Maus-ID zurückgeben"""
        return self.get_mice_config().get("max_id", 4)
    
    def get_controllers(self):
        """Liste aller Controller zurückgeben"""
        return self.get_controllers_config()
    
    def get_controller_by_id(self, controller_id):
        """Controller anhand ID finden"""
        for controller in self.get_controllers():
            if controller.get("id") == controller_id:
                return controller
        return None
    
    def get_coin_counter_gpio(self):
        """GPIO-Pin für Münzzähler zurückgeben"""
        coin_config = self.get_coin_counter_config()
        if not coin_config:
            return None
        return coin_config.get("gpio_pin")
    
    def get_websocket_config(self):
        """WebSocket-Konfiguration zurückgeben"""
        return self.config.get("websocket", {})
    
    def is_websocket_enabled(self):
        """Prüfen ob WebSocket aktiviert ist"""
        return self.get_websocket_config().get("enabled", False)
    
    def get_websocket_host(self):
        """WebSocket-Host zurückgeben"""
        return self.get_websocket_config().get("host", "localhost")
    
    def get_websocket_port(self):
        """WebSocket-Port zurückgeben"""
        return self.get_websocket_config().get("port", 8765)
    
    def validate_config(self):
        """Konfiguration validieren"""
        errors = []
        
        # Mäuse-Konfiguration prüfen
        mice_config = self.get_mice_config()
        if mice_config.get("count", 0) <= 0:
            errors.append("Anzahl der Mäuse muss größer als 0 sein")
        
        if mice_config.get("max_id", 0) < mice_config.get("count", 0):
            errors.append("Maximale Maus-ID muss größer oder gleich der Anzahl der Mäuse sein")
        
        # Controller-Konfiguration prüfen
        controllers = self.get_controllers()
        if not controllers:
            errors.append("Mindestens ein Controller muss konfiguriert sein")
        
        for controller in controllers:
            if not controller.get("serial_port"):
                errors.append(f"Controller {controller.get('id', 'unbekannt')} hat keinen seriellen Port")
        
        # Münzzähler-Konfiguration prüfen (nur wenn konfiguriert)
        coin_gpio = self.get_coin_counter_gpio()
        if coin_gpio is not None and (not isinstance(coin_gpio, int) or coin_gpio < 1):
            errors.append("GPIO-Pin für Münzzähler muss eine positive Zahl sein")
        
        if errors:
            for error in errors:
                self.logger.error(f"Konfigurationsfehler: {error}")
            return False
        
        self.logger.info("Konfiguration ist gültig")
        return True 