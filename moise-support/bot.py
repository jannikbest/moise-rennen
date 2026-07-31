#!/usr/bin/env python3
"""
Moise Support Telegram Bot
"""
import logging
import asyncio
import json
import websockets
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.error import TimedOut, NetworkError, RetryAfter
from config import Config
from support import SupportHandler
from user import UserHandler
from user_database import UserDatabase

class MoiseSupportBot:
    """Telegram Bot für Moise Support mit rollenbasierter Zugriffskontrolle"""
    
    def __init__(self):
        self.config = Config()
        self.logger = self._setup_logging()
        
        # Validiere Konfiguration
        errors = self.config.validate_config()
        if errors:
            for error in errors:
                self.logger.error(f"Konfigurationsfehler: {error}")
            raise ValueError("Bot-Konfiguration fehlerhaft")
        
        # WebSocket Verbindung
        self.websocket = None
        self.last_status = None
        self.websocket_task = None
        self.application = None
        
        # Zentrale UserDatabase-Instanz erstellen
        self.user_database = UserDatabase()
        
        # Handler initialisieren
        self.support_handler = SupportHandler(self.config, self.websocket, self.application, self.user_database)
        self.user_handler = UserHandler(self.config, self.websocket, self.application, self.user_database)
        
        self.logger.info("Moise Support Bot initialisiert")
    
    def _setup_logging(self):
        """Logging einrichten"""
        logging.basicConfig(
            level=getattr(logging, self.config.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('moise_support.log'),
                logging.StreamHandler()
            ]
        )
        
        # Unterdrücke httpx HTTP Request Logs
        logging.getLogger("httpx").setLevel(logging.WARNING)
        
        return logging.getLogger(__name__)
    
    def _update_handlers(self):
        """Aktualisiere WebSocket und Application Referenzen in Handlern"""
        self.support_handler.websocket = self.websocket
        self.support_handler.application = self.application
        self.user_handler.websocket = self.websocket
        self.user_handler.application = self.application
        # Aktualisiere auch den letzten Status in den Handlern
        if hasattr(self, 'last_status'):
            self.user_handler.set_last_status(self.last_status)
            self.support_handler.set_last_status(self.last_status)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Router für /start Befehl basierend auf User-Rolle"""
        chat_id = update.effective_chat.id
        
        # Erlaube allen Usern den Zugriff (nicht nur denen in ALLOWED_CHAT_IDS)
        if self.config.is_support_user(chat_id):
            await self.support_handler.start_command(update, context)
        else:
            await self.user_handler.start_command(update, context)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Router für /help Befehl basierend auf User-Rolle"""
        chat_id = update.effective_chat.id
        
        # Erlaube allen Usern den Zugriff
        if self.config.is_support_user(chat_id):
            await self.support_handler.help_command(update, context)
        else:
            await self.user_handler.help_command(update, context)
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Router für /status Befehl basierend auf User-Rolle"""
        chat_id = update.effective_chat.id
        
        # Erlaube allen Usern den Zugriff
        if self.config.is_support_user(chat_id):
            # Support-User bekommen erweiterte Status-Informationen
            if self.last_status:
                status_text = self.support_handler.format_status(self.last_status)
            else:
                status_text = """
📊 Systemstatus:

🟡 Keine Daten verfügbar
🔴 WebSocket nicht verbunden

Der Bot versucht automatisch eine Verbindung herzustellen...
                """
            await update.message.reply_text(status_text)
            self.logger.info(f"Support Status-Abfrage von Chat {chat_id}")
        else:
            # Reguläre User bekommen vereinfachte Status-Informationen
            self.user_handler.set_last_status(self.last_status)
            await self.user_handler.status_command(update, context)
    
    async def freispiel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Router für /freispiel Befehl - nur für Support"""
        await self.support_handler.freispiel_command(update, context)
    
    async def support_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Router für /support Befehl - nur für Support"""
        await self.support_handler.support_command(update, context)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Router für normale Nachrichten basierend auf User-Rolle"""
        chat_id = update.effective_chat.id
        
        # Erlaube allen Usern den Zugriff
        if self.config.is_support_user(chat_id):
            await self.support_handler.handle_message(update, context)
        else:
            await self.user_handler.handle_message(update, context)
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Router für Callback-Queries (Button-Klicks) basierend auf User-Rolle"""
        query = update.callback_query
        chat_id = query.from_user.id
        
        # Erlaube allen Usern den Zugriff
        if self.config.is_support_user(chat_id):
            await self.support_handler.handle_callback_query(update, context)
        elif query.data.startswith("user_"):
            await self.user_handler.handle_callback_query(update, context)
        else:
            await query.answer("❌ Unbekannter Button-Klick")
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Handler für Bot-Fehler - nur für Support-Mitglieder"""
        error = context.error
        
        # Ignoriere Timeout-Fehler, da sie normal sind
        if isinstance(error, TimedOut):
            self.logger.warning("Telegram API Timeout - normal bei langsamen Verbindungen")
            return
        
        # Ignoriere RetryAfter-Fehler
        if isinstance(error, RetryAfter):
            self.logger.warning(f"Telegram API Rate Limit: {error.retry_after}s")
            return
        
        # Ignoriere Network-Fehler und Message-Änderungsfehler
        if isinstance(error, NetworkError):
            self.logger.warning(f"Telegram API Network Error - temporär: {error}")
            return
        
        # Ignoriere "Message is not modified" Fehler (passiert bei doppelten Button-Klicks)
        if "Message is not modified" in str(error):
            self.logger.debug("Message nicht geändert - wahrscheinlich doppelter Button-Klick")
            return
        
        self.logger.error(f"Bot-Fehler: {error}")
        
        # Sende Fehlermeldung nur an Support-Mitglieder
        error_message = f"❌ Bot-Fehler aufgetreten: {error}"
        await self._notify_support_only_safe(error_message)
    
    async def _notify_support_only_safe(self, message):
        """Sende Nachricht nur an Support-Mitglieder mit Timeout-Behandlung"""
        if not self.application:
            self.logger.warning("Bot Application nicht verfügbar für Benachrichtigungen")
            return
            
        for chat_id in self.config.get_all_support_users():
            try:
                await asyncio.wait_for(
                    self.application.bot.send_message(
                        chat_id=chat_id, 
                        text=message,
                        parse_mode='Markdown'
                    ),
                    timeout=10.0  # 10 Sekunden Timeout
                )
                self.logger.info(f"Benachrichtigung gesendet an Support Chat {chat_id}")
            except asyncio.TimeoutError:
                self.logger.warning(f"Timeout beim Senden an Support Chat {chat_id}")
            except TimedOut:
                self.logger.warning(f"Telegram Timeout beim Senden an Support Chat {chat_id}")
            except RetryAfter as e:
                self.logger.warning(f"Rate Limit beim Senden an Support Chat {chat_id}: {e.retry_after}s")
            except NetworkError:
                self.logger.warning(f"Network Error beim Senden an Support Chat {chat_id}")
            except Exception as e:
                self.logger.error(f"Fehler beim Senden an Support Chat {chat_id}: {e}")
    
    async def connect_websocket(self):
        """WebSocket Verbindung zum Moise Brain herstellen"""
        websocket_url = f"ws://{self.config.moise_brain_host}:{self.config.moise_brain_port}"
        was_connected = False
        
        while True:
            try:
                self.logger.info(f"Verbinde zu WebSocket: {websocket_url}")
                async with websockets.connect(websocket_url) as websocket:
                    self.websocket = websocket
                    self._update_handlers()  # Aktualisiere Handler-Referenzen
                    self.logger.info("WebSocket verbunden")
                    
                    # Nur loggen, keine Benachrichtigung bei Verbindung
                    if not was_connected:
                        was_connected = True
                    
                    async for message in websocket:
                        try:
                            data = json.loads(message)
                            self.last_status = data
                            # Aktualisiere Status in den Handlern
                            self.user_handler.set_last_status(data)
                            self.support_handler.set_last_status(data)
                            self.logger.debug(f"WebSocket Daten empfangen: {data}")
                            
                            # Prüfe auf Fehler und benachrichtige nur Support
                            await self._check_and_notify_errors(data)
                            
                        except json.JSONDecodeError as e:
                            error_msg = f"❌ **JSON Parse Fehler:** {e}"
                            self.logger.error(error_msg)
                            await self._notify_support_only_safe(error_msg)
                        except Exception as e:
                            error_msg = f"❌ **WebSocket Datenfehler:** {e}"
                            self.logger.error(error_msg)
                            await self._notify_support_only_safe(error_msg)
                            
            except Exception as e:
                error_msg = f"🔴 **WebSocket Verbindung verloren:** {e}"
                self.logger.error(error_msg)
                
                # Nur benachrichtigen wenn vorher verbunden war
                if was_connected:
                    await self._notify_support_only_safe(error_msg)
                    was_connected = False
                
                # Warte 10 Sekunden vor erneutem Versuch
                await asyncio.sleep(10)
    
    async def _check_and_notify_errors(self, data):
        """Prüfe Daten auf Fehler und benachrichtige nur Support"""
        if 'game_error' in data and data['game_error'] != 'none':
            error_msg = f"❌ **Systemfehler:** {data['game_error']}"
            await self._notify_support_only_safe(error_msg)
    
    async def _notify_support_only(self, message):
        """Sende Nachricht nur an Support-Mitglieder (Legacy-Methode)"""
        await self._notify_support_only_safe(message)
    
    def run(self):
        """Bot starten"""
        self.logger.info("Starte Telegram Bot...")
        
        # Bot-Anwendung erstellen
        application = Application.builder().token(self.config.bot_token).build()
        self.application = application
        self._update_handlers()  # Aktualisiere Handler-Referenzen
        
        # Handler registrieren
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("status", self.status_command))
        application.add_handler(CommandHandler("freispiel", self.freispiel_command))
        application.add_handler(CommandHandler("support", self.support_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Callback-Query-Handler für Inline-Buttons
        application.add_handler(CallbackQueryHandler(self.handle_callback_query))
        
        # Fehler-Handler
        application.add_error_handler(self.error_handler)
        
        # WebSocket Task starten
        async def run_bot_with_websocket():
            # Starte WebSocket in separatem Task
            websocket_task = asyncio.create_task(self.connect_websocket())
            
            try:
                # Starte Bot mit polling und Timeout-Behandlung
                self.logger.info("Initialisiere Bot...")
                await asyncio.wait_for(application.initialize(), timeout=30.0)
                
                self.logger.info("Starte Bot...")
                await asyncio.wait_for(application.start(), timeout=30.0)
                
                self.logger.info("Starte Polling...")
                await asyncio.wait_for(application.updater.start_polling(), timeout=30.0)
                
                self.logger.info("Bot erfolgreich gestartet!")
                
                # Warte auf Beendigung (wird durch Ctrl+C unterbrochen)
                try:
                    await asyncio.Event().wait()
                except asyncio.CancelledError:
                    self.logger.info("Bot wird beendet...")
                    return
                
            except asyncio.TimeoutError:
                self.logger.error("Timeout beim Starten des Bots - versuche es erneut...")
                # Versuche es nochmal nach kurzer Pause
                await asyncio.sleep(5)
                await self._retry_bot_start(application)
            except TimedOut:
                self.logger.error("Telegram API Timeout beim Starten - versuche es erneut...")
                await asyncio.sleep(5)
                await self._retry_bot_start(application)
            except Exception as e:
                self.logger.error(f"Fehler beim Starten des Bots: {e}")
                # Versuche es nochmal
                await asyncio.sleep(5)
                await self._retry_bot_start(application)
            finally:
                # Cleanup
                websocket_task.cancel()
                try:
                    await application.stop()
                    await application.shutdown()
                except Exception as e:
                    self.logger.warning(f"Fehler beim Beenden des Bots: {e}")
                
                try:
                    await websocket_task
                except asyncio.CancelledError:
                    pass
        
        # Bot starten mit Signal-Handling
        self.logger.info("Bot läuft... Drücke Ctrl+C zum Beenden")
        
        try:
            asyncio.run(run_bot_with_websocket())
        except KeyboardInterrupt:
            self.logger.info("Bot wird beendet...")
        except Exception as e:
            self.logger.error(f"Unerwarteter Fehler beim Bot-Start: {e}")
            raise
    
    async def _retry_bot_start(self, application):
        """Versuche Bot-Start erneut"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.logger.info(f"Versuch {attempt + 1}/{max_retries} Bot zu starten...")
                
                # Erstelle eine neue Application für jeden Versuch
                new_application = Application.builder().token(self.config.bot_token).build()
                self.application = new_application
                self._update_handlers()  # Aktualisiere Handler-Referenzen
                
                # Handler registrieren
                new_application.add_handler(CommandHandler("start", self.start_command))
                new_application.add_handler(CommandHandler("help", self.help_command))
                new_application.add_handler(CommandHandler("status", self.status_command))
                new_application.add_handler(CommandHandler("freispiel", self.freispiel_command))
                new_application.add_handler(CommandHandler("support", self.support_command))
                new_application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
                new_application.add_handler(CallbackQueryHandler(self.handle_callback_query))
                new_application.add_error_handler(self.error_handler)
                
                await asyncio.wait_for(new_application.initialize(), timeout=30.0)
                await asyncio.wait_for(new_application.start(), timeout=30.0)
                await asyncio.wait_for(new_application.updater.start_polling(), timeout=30.0)
                
                self.logger.info("Bot erfolgreich gestartet nach Wiederholung!")
                try:
                    await asyncio.Event().wait()  # Warte auf Beendigung (wird durch Ctrl+C unterbrochen)
                except asyncio.CancelledError:
                    self.logger.info("Bot wird beendet...")
                    return
                
            except (asyncio.TimeoutError, TimedOut) as e:
                self.logger.warning(f"Versuch {attempt + 1} fehlgeschlagen: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(10)  # Längere Pause zwischen Versuchen
                else:
                    self.logger.error("Bot konnte nach mehreren Versuchen nicht gestartet werden")
                    raise
            except Exception as e:
                self.logger.error(f"Unerwarteter Fehler beim Bot-Start: {e}")
                raise

if __name__ == "__main__":
    bot = MoiseSupportBot()
    bot.run() 