#!/usr/bin/env python3
"""
Basis-Handler für Moise Support Bot
Enthält gemeinsame Funktionalität für User und Support
"""
import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

class BaseHandler:
    """Basis-Handler für gemeinsame Funktionalität"""
    
    def __init__(self, config, websocket=None, application=None, user_database=None):
        self.config = config
        self.websocket = websocket
        self.application = application
        self.logger = logging.getLogger(__name__)
        self.user_db = user_database
        self.last_status = None
    
    def is_game_ready(self):
        """Prüfe ob das Spiel im 'ready' Zustand ist"""
        if not self.last_status:
            return False
        
        try:
            # Prüfe verschiedene mögliche Game-State Felder
            game_state = self.last_status.get('game_state', '').lower()
            if game_state == 'ready':
                return True
            
            # Alternative Prüfungen für verschiedene State-Formate
            if 'is_game_active' in self.last_status and self.last_status['is_game_active']:
                return True
            
            # Prüfe auf spezifische Ready-Indikatoren
            if 'status' in self.last_status and self.last_status['status'].lower() == 'ready':
                return True
            
            return False
        except Exception as e:
            self.logger.error(f"Fehler beim Prüfen des Game-States: {e}")
            return False
    
    def _get_bahn_keyboard(self):
        """Erstelle Bahn-Auswahl-Keyboard - muss von abgeleiteten Klassen überschrieben werden"""
        raise NotImplementedError
    
    def _sanitize_name(self, name):
        """Bereinige den Namen von unerwünschten Zeichen"""
        # Entferne Newlines und Whitespace
        sanitized = name.replace('\n', ' ').replace('\r', ' ').strip()
        
        # Entferne JSON-spezifische Zeichen
        sanitized = sanitized.replace('{', '').replace('}', '').replace('[', '').replace(']', '')
        sanitized = sanitized.replace('"', '').replace("'", '').replace('\\', '')
        
        # Entferne mehrfache Leerzeichen
        sanitized = ' '.join(sanitized.split())
        
        return sanitized
    
    async def _handle_name_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler für Namens-Eingabe"""
        chat_id = update.effective_chat.id
        raw_name = update.message.text
        name = self._sanitize_name(raw_name)
        is_changing_name = context.user_data.get('is_changing_name', False)
        
        if len(name) < 2:
            await update.message.reply_text(
                "Hmm, das ist ein bisschen zu kurz 🧐\n\n"
                "Bitte gib einen Namen mit mindestens 2 Zeichen ein ✨"
            )
            return
        
        # Prüfe ob Name nach Bereinigung zu kurz ist
        if len(name) < 2:
            await update.message.reply_text(
                "Hmm, nach der Bereinigung ist der Name zu kurz 🧐\n\n"
                "Bitte gib einen gültigen Namen ein (ohne Sonderzeichen)."
            )
            return
        
        # Prüfe ob Name bereits existiert (außer bei eigenen Namen)
        existing_user_id = self.user_db.get_user_by_name(name)
        if existing_user_id and existing_user_id != chat_id:
            await update.message.reply_text(
                f"Oh nein wie schade 😔\n\n"
                f"Das ist ein schöner Name, doch leider hat sich den schon eine andere Maus geschnappt 🐭\n\n"
                f"Es wäre lieb wenn du dir einen anderen suchst 💕"
            )
            return
        
        # Speichere User in Datenbank
        if self.user_db.add_user(chat_id, name):
            if is_changing_name:
                await update.message.reply_text(
                    f"Cool {name} ist ein schöner Moise-Name! 🐭✨\n\n"
                    "Ich kann folgendes für dich tun:\n"
                    "• Hilfe anfordern 🆘\n"
                    "• Namen ändern ✏️\n\n"
                    "Nutze die Buttons oder schreibe 'Hilfe' für Unterstützung! 💕",
                    reply_markup=self._get_main_keyboard(chat_id)
                )
                self.logger.info(f"User {chat_id} hat Namen zu '{name}' geändert")
            else:
                await update.message.reply_text(
                    f"Yay, vielen Dank {name}! 🎉\n\n"
                    "Dein Name wurde gespeichert. Du kannst jetzt Hilfe anfordern, wenn du Probleme hast! 💪",
                    reply_markup=self._get_main_keyboard(chat_id)
                )
                self.logger.info(f"User {chat_id} mit Namen '{name}' in Datenbank gespeichert")
        else:
            await update.message.reply_text(
                "Ups, da ist etwas schiefgegangen 😅\n\n"
                "Es gab ein Problem beim Speichern deines Namens. "
                "Du kannst trotzdem Hilfe anfordern wenn du Probleme hast! 💪",
                reply_markup=self._get_main_keyboard(chat_id)
            )
        
        # Entferne Namens-Eingabe-Modus
        context.user_data.pop('waiting_for_name', None)
        context.user_data.pop('is_changing_name', None)
    
    async def _handle_enter_name_button(self, query, context):
        """Handler für Namens-Eingabe-Button"""
        await query.edit_message_text(
            "✅ **Perfekt!**\n\n"
            "Bitte schreibe jetzt deinen Namen:",
        )
        
        # Setze Namens-Eingabe-Modus
        context.user_data['waiting_for_name'] = True
    
    async def _handle_no_name_button(self, query, context):
        """Handler für Kein-Name-Button"""
        user_id = query.from_user.id
        await query.edit_message_text(
            "❌ **Kein Problem Maus!**\n\n"
            "Wenn du es dir anders überlegt hast, melde dich gern nochmal.",
            reply_markup=self._get_main_keyboard(user_id)
        )
        self.logger.info(f"User {user_id} hat Namens-Speicherung abgelehnt")
    
    async def _handle_change_name_button(self, query, context):
        """Handler für Namen-Änderungs-Button"""
        await query.edit_message_text(
            "✏️ **Namen ändern**\n\n"
            "Bitte schreibe jetzt deinen neuen Namen:",
        )
        
        # Setze Namens-Änderungs-Modus
        context.user_data['waiting_for_name'] = True
        context.user_data['is_changing_name'] = True
    
    async def _handle_join_game_button(self, query, context):
        """Handler für Spiel-Teilnahme-Button"""
        chat_id = query.from_user.id
        
        # Prüfe ob User einen Namen hat
        if not self.user_db.user_exists(chat_id):
            await query.edit_message_text(
                "❌ **Du brauchst einen Namen!**\n\n"
                "Du musst zuerst deinen Namen eingeben, bevor du am Spiel teilnehmen kannst. "
                "Bitte ändere zuerst deinen Namen.",
                reply_markup=self._get_main_keyboard(chat_id)
            )
            return
        
        # Prüfe ob das Spiel ready ist
        if not self.is_game_ready():
            await query.edit_message_text(
                "⏳ **Spiel noch nicht bereit!**\n\n"
                "Das Spiel ist momentan nicht im 'ready' Zustand. "
                "Bitte warte, bis das Spiel bereit ist, oder kontaktiere den Support.",
                reply_markup=self._get_main_keyboard(chat_id)
            )
            return
        
        user_name = self.user_db.get_user_name(chat_id)
        
        await query.edit_message_text(
            f"🎮 **Spiel-Teilnahme für {user_name}**\n\n"
            "Auf welcher Bahn möchtest du spielen?\n"
            "Wähle eine Bahn aus:",
            reply_markup=self._get_bahn_keyboard()
        )
    
    async def _handle_bahn_selection(self, query, context):
        """Handler für Bahn-Auswahl"""
        chat_id = query.from_user.id
        user_name = self.user_db.get_user_name(chat_id)
        
        # Extrahiere Bahn-Nummer aus callback_data (bahn_1 -> 1)
        bahn_num = int(query.data.split('_')[-1])
        
        # Erstelle WebSocket-Nachricht
        websocket_message = {
            "action": "set_maus_name",
            "maus_id": bahn_num,
            "name": user_name
        }
        
        # Sende über WebSocket
        if self.websocket and self.websocket.open:
            try:
                await self.websocket.send(json.dumps(websocket_message))
                self.logger.info(f"Spiel-Teilnahme gesendet: {user_name} auf Bahn {bahn_num}")
                
                await query.edit_message_text(
                    f"✅ **Spiel-Teilnahme erfolgreich!**\n\n"
                    f"Du spielst jetzt als **{user_name}** auf **Bahn {bahn_num}**.\n"
                    f"Viel Glück! 🍀",
                    reply_markup=self._get_main_keyboard(chat_id)
                )
            except Exception as e:
                self.logger.error(f"Fehler beim Senden der Spiel-Teilnahme: {e}")
                await query.edit_message_text(
                    "❌ **Fehler beim Spiel-Beitritt**\n\n"
                    "Es gab ein Problem mit der Verbindung. "
                    "Bitte versuche es später nochmal.",
                    reply_markup=self._get_main_keyboard(chat_id)
                )
        else:
            await query.edit_message_text(
                "❌ **Keine Verbindung**\n\n"
                "Der Bot ist nicht mit dem Spiel verbunden. "
                "Bitte versuche es später nochmal.",
                reply_markup=self._get_main_keyboard(chat_id)
            )
    
    def set_last_status(self, status):
        """Setze den letzten Status"""
        self.last_status = status
    
    # Abstrakte Methoden - müssen von abgeleiteten Klassen implementiert werden
    def _get_main_keyboard(self, chat_id=None):
        """Erstelle Haupt-Keyboard - muss von abgeleiteten Klassen implementiert werden"""
        raise NotImplementedError
    
    def _get_help_keyboard(self):
        """Erstelle Hilfe-Keyboard - muss von abgeleiteten Klassen implementiert werden"""
        raise NotImplementedError
    
    def _get_bahn_keyboard(self):
        """Erstelle Bahn-Auswahl-Keyboard - muss von abgeleiteten Klassen implementiert werden"""
        raise NotImplementedError
    
    async def _handle_help_main_button(self, query, context):
        """Handler für Haupt-Hilfe-Button - muss von abgeleiteten Klassen implementiert werden"""
        raise NotImplementedError
    
    async def _handle_back_button(self, query, context):
        """Handler für Zurück-Button - muss von abgeleiteten Klassen implementiert werden"""
        raise NotImplementedError 