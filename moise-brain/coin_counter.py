#!/usr/bin/env python3
"""
Münzzähler-Modul für Moise-Brain
"""
import time
import logging
from collections import deque


class CoinCounter:
    """Klasse für den Münzzähler mit GPIO-Interrupt"""
    
    def __init__(self, config, interrupt_callback=None):
        """
        Münzzähler initialisieren
        
        Args:
            config (dict): Münzzähler-Konfiguration
            interrupt_callback (function): Optionaler Callback für Interrupt
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.gpio_pin = config.get("gpio_pin", 18)
        self.interrupt_callback = interrupt_callback
        
        # Pulse-Array für Interrupts
        self.pulse_times = deque()
        self.last_pulse_time = 0
        self.pulse_timeout = config.get("pulse_timeout", 0.3)
        
        # Münz-Erkennung (Pulse pro Münze)
        self.coin_pulses = {
            100: 1,  # 1 Euro = 1 Pulse
            200: [3, 4, 5, 6, 7]  # 2 Euro = 3-7 Pulse (kulant)
        }
        
        # GPIO-Interrupt konfigurieren
        self._setup_gpio_interrupt()
        
        self.logger.info(f"Münzzähler initialisiert auf GPIO {self.gpio_pin}")
    
    def _setup_gpio_interrupt(self):
        """GPIO-Interrupt einrichten"""
        try:
            import RPi.GPIO as GPIO
            
            # GPIO-Modus setzen
            GPIO.setmode(GPIO.BCM)
            
            # Pull-up/down konfigurieren
            pull_up_down = GPIO.PUD_UP
            if self.config.get("pull_up_down") == "PUD_DOWN":
                pull_up_down = GPIO.PUD_DOWN
            
            # GPIO als Input mit Pull-up/down konfigurieren
            GPIO.setup(self.gpio_pin, GPIO.IN, pull_up_down=pull_up_down)
            
            # Edge-Detection konfigurieren
            edge = GPIO.FALLING
            if self.config.get("edge") == "RISING":
                edge = GPIO.RISING
            elif self.config.get("edge") == "BOTH":
                edge = GPIO.BOTH
            
            # Bouncetime aus Konfiguration
            bouncetime = self.config.get("bouncetime", 50)
            
            # Event-Detection hinzufügen
            GPIO.add_event_detect(self.gpio_pin, edge, 
                                callback=self._interrupt_handler, bouncetime=bouncetime)
            
            self.logger.info(f"GPIO-Interrupt auf Pin {self.gpio_pin} konfiguriert")
            self.logger.info(f"  - Pull-up/down: {self.config.get('pull_up_down', 'PUD_UP')}")
            self.logger.info(f"  - Edge: {self.config.get('edge', 'FALLING')}")
            self.logger.info(f"  - Bouncetime: {bouncetime}ms")
            
        except ImportError:
            self.logger.warning("RPi.GPIO nicht verfügbar - Simuliere GPIO")
        except Exception as e:
            self.logger.error(f"Fehler beim GPIO-Setup: {e}")
    
    def _interrupt_handler(self, channel):
        """Interrupt-Handler für GPIO-Pulse"""
        current_time = time.time()
        
        # Mindestzeit zwischen Pulsen prüfen (50ms)
        min_pulse_interval = 0.05
        if self.pulse_times and (current_time - self.last_pulse_time) < min_pulse_interval:
            self.logger.debug(f"Pulse zu schnell ignoriert: {current_time - self.last_pulse_time:.3f}s")
            return
        
        # Pulse hinzufügen
        self.pulse_times.append(current_time)
        self.last_pulse_time = current_time
        
        if self.interrupt_callback:
            self.interrupt_callback(channel, current_time)
        
        self.logger.debug(f"Pulse erkannt auf GPIO {channel} um {current_time}")
    
    def cycle_update(self):
        """Zyklische Aktualisierung - Münzerkennung"""
        current_time = time.time()
        
        # Prüfe ob Timeout seit letztem Pulse vergangen ist
        if self.pulse_times and (current_time - self.last_pulse_time) >= self.pulse_timeout:
            # Münze erkennen basierend auf Anzahl Pulse
            pulse_count = len(self.pulse_times)
            
            # Zeit zwischen erstem und letztem Pulse berechnen
            if len(self.pulse_times) > 1:
                total_time = self.pulse_times[-1] - self.pulse_times[0]
                avg_interval = total_time / (pulse_count - 1) if pulse_count > 1 else 0
                self.logger.info(f"Pulse-Sequenz: {pulse_count} Pulse in {total_time:.3f}s (Ø {avg_interval:.3f}s)")
                
                # Validierung: Pulse sollten in vernünftigen Abständen sein
                if avg_interval < 0.05:  # Weniger als 50ms zwischen Pulsen
                    self.logger.warning(f"Pulse zu schnell: Ø {avg_interval:.3f}s - Ignoriere Sequenz")
                    self.pulse_times.clear()
                    return None
            
            # Münze anhand Pulse-Anzahl identifizieren
            coin_value = self._identify_coin(pulse_count)
            
            if coin_value:
                self.logger.info(f"Münze erkannt: {coin_value} Cent ({pulse_count} Pulse)")
                
                # Pulse-Array leeren
                self.pulse_times.clear()
                
                return coin_value
            else:
                self.logger.warning(f"Unbekannte Münze mit {pulse_count} Pulsen")
                self.pulse_times.clear()
        
        return None
    
    def _identify_coin(self, pulse_count):
        """Münze anhand der Pulse-Anzahl identifizieren"""
        for coin_value, pulses in self.coin_pulses.items():
            if isinstance(pulses, list):
                # Liste von erlaubten Pulse-Anzahlen (kulant)
                if pulse_count in pulses:
                    # Warnung wenn nicht exakt 5 Pulse
                    if pulse_count != 5:
                        self.logger.warning(f"2€ Münze mit {pulse_count} Pulsen erkannt (erwartet: 5)")
                    return coin_value
            else:
                # Einzelner Wert (exakt)
                if pulses == pulse_count:
                    return coin_value
        return None
    
    def get_total_pulses(self):
        """Gesamte Anzahl Pulse zurückgeben"""
        return len(self.pulse_times)
    
    def clear_pulses(self):
        """Pulse-Array leeren"""
        self.pulse_times.clear()
        self.logger.debug("Pulse-Array geleert") 