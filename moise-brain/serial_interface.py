#!/usr/bin/env python3
"""
Serielle Schnittstelle für Moise-Brain
"""
import serial
import time
import platform


class SerialInterface:
    """Klasse für serielle Kommunikation"""
    
    def __init__(self, logger, port):
        self.ser = None
        self.logger = logger
        self.port = port
    
    def open_connection(self):
        """Serielle Schnittstelle öffnen"""
        try:
            self.logger.info(f"System: {platform.system()}, verwende Port: {self.port}")
            # Optimierte Einstellungen für schnelle Kommunikation:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=115200,
                timeout=0.01,        # Kurzer Timeout für schnelle Reaktion
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                xonxoff=False,       # Keine Software-Flusssteuerung
                rtscts=False,        # Keine Hardware-Flusssteuerung
                dsrdtr=False
            )
            
            self.logger.info(f"Serielle Schnittstelle geöffnet: {self.ser.port} @ {self.ser.baudrate}")
            return True
            
        except serial.SerialException as e:
            self.logger.error(f"Fehler beim Öffnen der seriellen Schnittstelle: {e}")
            return False
    
    def close_connection(self):
        """Serielle Schnittstelle schließen"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.logger.info("Serielle Schnittstelle geschlossen")
    
    def send_command(self, cmd):
        """Kommando über serielle Schnittstelle senden"""
        if self.ser and self.ser.is_open:
            # Kommando senden mit Zeilenumbruch
            full_cmd = f"{cmd}\n"
            self.ser.write(full_cmd.encode())
            
            # Nach dem Senden flush() aufrufen
            self.ser.flush()
            
            self.logger.info(f"Kommando gesendet: {cmd}")
    
    def send_data(self, data):
        """Daten über serielle Schnittstelle senden (Alias für send_command)"""
        self.send_command(data)
    
    def read_data(self):
        """Daten von serieller Schnittstelle lesen"""
        if self.ser and self.ser.in_waiting > 0:
            try:
                # Direkt eine Zeile lesen
                raw_data = self.ser.readline()
                command = raw_data.decode().strip()
                return command if command else None
                    
            except UnicodeDecodeError as e:
                # Kaputte UTF-8 Daten ignorieren
                self.logger.debug(f"UTF-8 Dekodierungsfehler ignoriert: {e}")
            except Exception as e:
                # Andere Dekodierungsfehler auch ignorieren
                self.logger.debug(f"Dekodierungsfehler ignoriert: {e}")
        
        return None 