#!/usr/bin/env python3
"""
WebSocket-Server für Moise-Brain
"""
import asyncio
import json
import logging
import websockets
from websockets.server import serve


class WebSocketServer:
    """WebSocket-Server für Game-Data"""
    
    def __init__(self, game_data, host="localhost", port=8765):
        """
        WebSocket-Server initialisieren
        
        Args:
            game_data (GameData): Referenz auf GameData
            host (str): Host-Adresse
            port (int): Port-Nummer
        """
        self.logger = logging.getLogger(__name__)
        self.game_data = game_data
        self.host = host
        self.port = port
        self.clients = set()
        
        self.logger.info(f"WebSocket-Server initialisiert auf {host}:{port}")
    
    async def register(self, websocket):
        """Client registrieren"""
        self.clients.add(websocket)
        self.logger.info(f"Client verbunden - Gesamt: {len(self.clients)}")
    
    async def unregister(self, websocket):
        """Client deregistrieren"""
        self.clients.remove(websocket)
        self.logger.info(f"Client getrennt - Gesamt: {len(self.clients)}")
    
    async def send_game_data(self, websocket):
        """Game-Data an Client senden"""
        try:
            game_summary = self.game_data.get_game_summary()
            await websocket.send(json.dumps(game_summary, ensure_ascii=False))
        except Exception as e:
            self.logger.error(f"Fehler beim Senden der Game-Data: {e}")
    
    async def broadcast_game_data(self):
        """Game-Data an alle Clients senden"""
        if not self.clients:
            return
        
        game_summary = self.game_data.get_game_summary()
        message = json.dumps(game_summary, ensure_ascii=False)
        
        # Alle Clients parallel benachrichtigen
        await asyncio.gather(
            *[client.send(message) for client in self.clients],
            return_exceptions=True
        )
    
    async def handle_client(self, websocket, path):
        """Client-Verbindung behandeln"""
        await self.register(websocket)
        try:
            # Initial Game-Data senden
            await self.send_game_data(websocket)
            
            # Auf Nachrichten warten
            async for message in websocket:
                try:
                    data = json.loads(message)
                    if data.get("action") == "get_game_data":
                        await self.send_game_data(websocket)
                    elif data.get("action") == "ping":
                        await websocket.send(json.dumps({"response": "pong"}))
                except json.JSONDecodeError:
                    self.logger.warning("Ungültige JSON-Nachricht empfangen")
                except Exception as e:
                    self.logger.error(f"Fehler bei Nachrichtenverarbeitung: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            self.logger.info("Client-Verbindung geschlossen")
        except Exception as e:
            self.logger.error(f"Fehler bei Client-Verbindung: {e}")
        finally:
            await self.unregister(websocket)
    
    async def start_server(self):
        """Server starten"""
        async with serve(self.handle_client, self.host, self.port):
            self.logger.info(f"WebSocket-Server gestartet auf ws://{self.host}:{self.port}")
            
            # Periodische Updates an alle Clients (alle 100ms)
            while True:
                await self.broadcast_game_data()
                await asyncio.sleep(0.1)  # 100ms Pause
    
    def start(self):
        """Server in separatem Thread starten"""
        asyncio.run(self.start_server())
    
    def get_client_count(self):
        """Anzahl verbundener Clients zurückgeben"""
        return len(self.clients) 