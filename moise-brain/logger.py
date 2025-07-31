#!/usr/bin/env python3
"""
Logger-Modul für Moise-Brain
"""
import logging
from datetime import datetime


def setup_logging():
    """Logging mit Zeitstempel ins File einrichten"""
    # Log-Datei mit Zeitstempel im log-Ordner
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"log/moise_brain_{timestamp}.log"
    
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