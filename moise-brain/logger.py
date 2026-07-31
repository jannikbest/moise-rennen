#!/usr/bin/env python3
"""
Logger-Modul für Moise-Brain
"""
import logging
import os
from datetime import datetime


def setup_logging():
    """Logging mit Zeitstempel ins File einrichten"""
    # Log-Datei mit Zeitstempel im log-Ordner
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"log/moise_brain_{timestamp}.log"
    
    # Log-Ordner erstellen, falls er nicht existiert
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Logging konfigurieren
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()  # Auch auf Konsole
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging gestartet - Datei: {log_file}")
    return logger 