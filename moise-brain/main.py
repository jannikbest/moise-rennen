#!/usr/bin/env python3
"""
Moise-Brain - Hauptprogramm
"""
import time
import sys
import select
import platform
import threading
import asyncio
from logger import setup_logging
from config import Config
from serial_interface import SerialInterface
from game_logic import GameLogic
from moise_controller import MoiseController
from maus import Maus
from game import Game
from coin_counter import CoinCounter
from game_state import GameState
from game_data import GameData, GameError
from websocket_server import WebSocketServer


def input_available():
    """Prüft ohne zu blockieren, ob Benutzereingaben verfügbar sind"""
    return select.select([sys.stdin], [], [], 0.0)[0]


def start_websocket_server(websocket_server):
    """WebSocket-Server in separatem Thread starten"""
    try:
        websocket_server.start()
    except Exception as e:
        print(f"WebSocket-Server Fehler: {e}")


def main():
    """Hauptprogramm"""
    logger = setup_logging()
    logger.info("Moise-Brain gestartet")
    
    # Konfiguration laden
    config = Config()
    if not config.validate_config():
        logger.error("Konfiguration ist ungültig!")
        return
    
    # Game-State laden
    game_state = GameState()
    logger.info(f"Spielzustand geladen - Guthaben: {game_state.get_guthaben()} Cent")
    
    # Game-Data erstellen
    game_data = GameData(game_state)
    
    # WebSocket-Server erstellen (nur wenn aktiviert)
    websocket_server = None
    websocket_thread = None
    if config.is_websocket_enabled():
        host = config.get_websocket_host()
        port = config.get_websocket_port()
        websocket_server = WebSocketServer(game_data, host, port)
        
        # WebSocket-Server in separatem Thread starten
        websocket_thread = threading.Thread(target=start_websocket_server, args=(websocket_server,), daemon=True)
        websocket_thread.start()
        logger.info(f"WebSocket-Server gestartet auf {host}:{port}")
    else:
        logger.info("WebSocket-Server deaktiviert")
    
    # Münzzähler erstellen (nur wenn konfiguriert)
    coin_counter = None
    coin_gpio = config.get_coin_counter_gpio()
    if coin_gpio:
        try:
            coin_counter = CoinCounter(coin_gpio)
            logger.info(f"Münzzähler auf GPIO {coin_gpio} aktiviert")
        except Exception as e:
            error_msg = f"Fehler beim Münzzähler-Setup: {e}"
            logger.error(error_msg)
            game_data.set_game_error(GameError.HARDWARE_ERROR, error_msg)
    else:
        logger.info("Kein Münzzähler konfiguriert")
    
    # Mäuse erstellen
    maus1 = Maus(1)
    maus2 = Maus(2)
    maus3 = Maus(3)
    maus4 = Maus(4)
    
    # Game-System erstellen
    game = Game(logger, game_data)
    
    # Controller mit Mäusen erstellen
    controller1 = MoiseController(1, [maus1, maus2])  # Controller 1 mit Maus 1 und 2
    controller2 = MoiseController(6, [maus3, maus4])  # Controller 6 mit Maus 3 und 4
    
    # Controller zum Game hinzufügen
    game.add_controller(controller1)
    game.add_controller(controller2)
    
    # Controller öffnen
    controller1_ok = False
    controller2_ok = False
    
    try:
        controller1_ok = controller1.init()
        if not controller1_ok:
            error_msg = "Konnte Controller 1 nicht öffnen"
            logger.error(error_msg)
            game_data.set_game_error(GameError.HARDWARE_ERROR, error_msg)
    except Exception as e:
        error_msg = f"Fehler beim Controller 1 Setup: {e}"
        logger.error(error_msg)
        game_data.set_game_error(GameError.HARDWARE_ERROR, error_msg)
    
    try:
        controller2_ok = controller2.init()
        if not controller2_ok:
            error_msg = "Konnte Controller 2 nicht öffnen"
            logger.error(error_msg)
            game_data.set_game_error(GameError.HARDWARE_ERROR, error_msg)
    except Exception as e:
        error_msg = f"Fehler beim Controller 2 Setup: {e}"
        logger.error(error_msg)
        game_data.set_game_error(GameError.HARDWARE_ERROR, error_msg)
    
    if controller1_ok and controller2_ok:
        logger.info("Beide Controller erfolgreich geöffnet")
        logger.info(f"Controller 1: {controller1.port}")
        logger.info(f"Controller 2: {controller2.port}")
        game_data.set_game_error(GameError.NONE)
    else:
        logger.warning("Nicht alle Controller konnten geöffnet werden")
    
    # Hauptschleife
    logger.info("Starte Hauptschleife (Ctrl+C zum Beenden)")
    try:
        while True:
            # 1. Controller mit input() aufrufen
            try:
                if controller1_ok:
                    controller1.input()
                if controller2_ok:
                    controller2.input()
            except Exception as e:
                error_msg = f"Fehler bei Controller input(): {e}"
                logger.error(error_msg)
                game_data.set_game_error(GameError.COMMUNICATION_ERROR, error_msg)
            
            # 2. Game mit cycleUpdate() aufrufen
            try:
                game.cycleUpdate()
                
                # GameData mit aktuellen Spielinformationen aktualisieren
                current_state = game.get_current_state().value
                game_data.set_game_state(current_state)
                
                # Maus-Punktzahlen aktualisieren
                for maus in game.maeuse:
                    game_data.set_maus_punktzahl(maus.maus_id, maus.punktzahl)
                
                # Gewinner-Maus setzen
                for maus in game.maeuse:
                    if maus.has_won_game():
                        game_data.set_gewonnene_maus(maus.maus_id)
                        break
                else:
                    # Kein Gewinner gefunden
                    game_data.set_gewonnene_maus(None)
                    
            except Exception as e:
                error_msg = f"Fehler bei Game cycleUpdate(): {e}"
                logger.error(error_msg)
                game_data.set_game_error(GameError.HARDWARE_ERROR, error_msg)
            
            # 3. Controller mit cycleUpdate() aufrufen
            try:
                if controller1_ok:
                    controller1.cycleUpdate()
                if controller2_ok:
                    controller2.cycleUpdate()
            except Exception as e:
                error_msg = f"Fehler bei Controller cycleUpdate(): {e}"
                logger.error(error_msg)
                game_data.set_game_error(GameError.COMMUNICATION_ERROR, error_msg)
            
            # 4. Münzzähler mit cycleUpdate() aufrufen (nur wenn vorhanden)
            if coin_counter:
                try:
                    coin_value = coin_counter.cycle_update()
                    if coin_value:
                        # Einzahlung hinzufügen
                        neue_einzahlungen = game_state.add_einzahlung(coin_value)
                        neues_guthaben = game_state.get_guthaben()
                        logger.info(f"Münze eingeworfen: {coin_value} Cent - Einzahlungen: {neue_einzahlungen} Cent - Guthaben: {neues_guthaben} Cent")
                except Exception as e:
                    error_msg = f"Fehler bei Münzzähler: {e}"
                    logger.error(error_msg)
                    game_data.set_game_error(GameError.HARDWARE_ERROR, error_msg)
            
            # Kurz warten um CPU zu schonen
            time.sleep(0.01)
        
    except KeyboardInterrupt:
        logger.info("Programm durch Ctrl+C beendet")
    except Exception as e:
        error_msg = f"Kritischer Fehler in Hauptschleife: {e}"
        logger.error(error_msg)
        game_data.set_game_error(GameError.HARDWARE_ERROR, error_msg)
    finally:
        try:
            if controller1_ok:
                controller1.close()
            if controller2_ok:
                controller2.close()
        except Exception as e:
            logger.error(f"Fehler beim Schließen der Controller: {e}")
        logger.info("Programm beendet")


if __name__ == "__main__":
    main() 