#!/usr/bin/env python3
"""
Münzzähler-Modul für Moise-Brain
"""
import time
import logging
from collections import deque


class CoinCounter:
    """Klasse für den Münzzähler mit GPIO-Interrupt"""
    
    def __init__(self, gpio_pin, interrupt_callback=None):
        """
        Münzzähler initialisieren
        
        Args:
            gpio_pin (int): GPIO-Pin für den Interrupt
            interrupt_callback (function): Optionaler Callback für Interrupt
        """
        self.logger = logging.getLogger(__name__)
        self.gpio_pin = gpio_pin
        self.interrupt_callback = interrupt_callback
        
        # Pulse-Array für Interrupts
        self.pulse_times = deque()
        self.last_pulse_time = 0
        
        # Münz-Erkennung (Pulse pro Münze)
        self.coin_pulses = {
            2: 1,   # 2 Euro = 1 Pulse
            1: 1,   # 1 Euro = 1 Pulse  
            50: 2,  # 50 Cent = 2 Pulse
            20: 3,  # 20 Cent = 3 Pulse
            10: 4,  # 10 Cent = 4 Pulse
            5: 5,   # 5 Cent = 5 Pulse
            2: 6,   # 2 Cent = 6 Pulse
            1: 7    # 1 Cent = 7 Pulse
        }
        
        # GPIO-Interrupt konfigurieren
        self._setup_gpio_interrupt()
        
        self.logger.info(f"Münzzähler initialisiert auf GPIO {gpio_pin}")
    
    def _setup_gpio_interrupt(self):
        """GPIO-Interrupt einrichten"""
        try:
            import RPi.GPIO as GPIO
            
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(self.gpio_pin, GPIO.FALLING, 
                                callback=self._interrupt_handler, bouncetime=50)
            
            self.logger.info(f"GPIO-Interrupt auf Pin {self.gpio_pin} konfiguriert")
            
        except ImportError:
            self.logger.warning("RPi.GPIO nicht verfügbar - Simuliere GPIO")
        except Exception as e:
            self.logger.error(f"Fehler beim GPIO-Setup: {e}")
    
    def _interrupt_handler(self, channel):
        """Interrupt-Handler für GPIO-Pulse"""
        current_time = time.time()
        self.pulse_times.append(current_time)
        self.last_pulse_time = current_time
        
        if self.interrupt_callback:
            self.interrupt_callback(channel, current_time)
        
        self.logger.debug(f"Pulse erkannt auf GPIO {channel} um {current_time}")
    
    def cycle_update(self):
        """Zyklische Aktualisierung - Münzerkennung"""
        current_time = time.time()
        
        # Prüfe ob 300ms seit letztem Pulse vergangen sind
        if self.pulse_times and (current_time - self.last_pulse_time) >= 0.3:
            # Münze erkennen basierend auf Anzahl Pulse
            pulse_count = len(self.pulse_times)
            
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