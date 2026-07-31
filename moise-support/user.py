#!/usr/bin/env python3
"""
User-Modul für Moise Support Bot
Enthält alle User-spezifischen Funktionen und Befehle
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from base_handler import BaseHandler

class UserHandler(BaseHandler):
    """Handler für User-spezifische Befehle und Funktionen"""
    
    def __init__(self, config, websocket=None, application=None, user_database=None):
        super().__init__(config, websocket, application, user_database)
    
    def is_regular_user(self, chat_id):
        """Prüfe ob User ein regulärer User ist (nicht Support)"""
        return self.config.is_regular_user(chat_id)
    
    def is_authorized_user(self, chat_id):
        """Prüfe ob User autorisiert ist (User oder Support)"""
        return self.config.is_chat_allowed(chat_id)
    
    def _get_main_keyboard(self, chat_id=None):
        """Erstelle User-spezifische Inline-Keyboard"""
        keyboard = []
        
        # Prüfe ob User einen Namen hat UND das Spiel ready ist
        if chat_id and self.user_db.user_exists(chat_id) and self.is_game_ready():
            keyboard.append([
                InlineKeyboardButton("🎮 Am Spiel teilnehmen", callback_data="user_join_game")
            ])
        
        keyboard.extend([
            [
                InlineKeyboardButton("🆘 Ich brauche Hilfe", callback_data="user_help_main")
            ],
            [
                InlineKeyboardButton("✏️ Namen ändern", callback_data="user_change_name")
            ]
        ])
        return InlineKeyboardMarkup(keyboard)
    
    def _get_welcome_keyboard(self):
        """Erstelle Willkommens-Keyboard für neue User"""
        keyboard = [
            [
                InlineKeyboardButton("✅ Ja, hier ist mein Name", callback_data="user_enter_name")
            ],
            [
                InlineKeyboardButton("❌ Nein, das will ich nicht", callback_data="user_no_name")
            ],
            [
                InlineKeyboardButton("🆘 Nein, ich brauche den Moise-Support", callback_data="user_help_main")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def _get_help_keyboard(self):
        """Erstelle Hilfe-Keyboard mit Unteroptionen"""
        keyboard = [
            [
                InlineKeyboardButton("🐭 Die Moise laufen nicht", callback_data="user_help_moise")
            ],
            [
                InlineKeyboardButton("💰 Mein Geld wurde nicht gezählt", callback_data="user_help_money")
            ],
            [
                InlineKeyboardButton("❓ Etwas anderes", callback_data="user_help_other")
            ],
            [
                InlineKeyboardButton("🔙 Zurück", callback_data="user_back")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def _get_bahn_keyboard(self):
        """Erstelle Bahn-Auswahl-Keyboard für User"""
        keyboard = [
            [
                InlineKeyboardButton("🏁 Bahn 1", callback_data="user_bahn_1"),
                InlineKeyboardButton("🏁 Bahn 2", callback_data="user_bahn_2")
            ],
            [
                InlineKeyboardButton("🏁 Bahn 3", callback_data="user_bahn_3"),
                InlineKeyboardButton("🏁 Bahn 4", callback_data="user_bahn_4")
            ],
            [
                InlineKeyboardButton("🏁 Bahn 5", callback_data="user_bahn_5")
            ],
            [
                InlineKeyboardButton("🔙 Zurück", callback_data="user_back")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """User-spezifischer Start-Befehl"""
        chat_id = update.effective_chat.id
        
        # Prüfe ob User neu ist
        if not self.user_db.user_exists(chat_id):
            # Neuer User - zeige Willkommensnachricht
            welcome_text = f"""
Hallo Maus, willkommen beim Moise-Support.

Du kannst hier Hilfe bekommen oder Infos zu deinen gewonnenen Spielen erhalten.

Willst du, dass deine gewonnenen Spiele gespeichert werden? Dann sag uns deinen Namen.
            """
            
            await update.message.reply_text(
                welcome_text,
                reply_markup=self._get_welcome_keyboard()
            )
            self.logger.info(f"Neuer User {chat_id} begrüßt")
        else:
            # Bekannter User - normale Begrüßung
            user_name = self.user_db.get_user_name(chat_id)
            welcome_text = f"""
🤖 Willkommen zurück beim {self.config.bot_name}!

👤 **User-Modus aktiviert**

Hallo {user_name}, du kannst:
• Hilfe anfordern
• Probleme melden

Wähle eine Aktion aus:
            """
            
            await update.message.reply_text(
                welcome_text,
                reply_markup=self._get_main_keyboard(chat_id)
            )
            self.logger.info(f"Bekannter User {chat_id} ({user_name}) begrüßt")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """User-spezifischer Help-Befehl"""
        chat_id = update.effective_chat.id
        help_text = """
📋 **User-Befehle:**

/start - Bot starten
/help - Diese Hilfe anzeigen

Du kannst Hilfe anfordern, wenn du Probleme hast.
        """
        
        await update.message.reply_text(
            help_text,
            reply_markup=self._get_main_keyboard(chat_id)
        )
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """User-spezifischer Status-Befehl - nicht verfügbar für User"""
        chat_id = update.effective_chat.id
        await update.message.reply_text(
            "❌ **Status-Abfrage nicht verfügbar**\n\n"
            "Als User kannst du den Systemstatus nicht abfragen. "
            "Nutze die Hilfe-Funktion, wenn du Probleme hast.",
            reply_markup=self._get_main_keyboard(chat_id)
        )
        self.logger.info(f"User Status-Abfrage verweigert von Chat {chat_id}")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler für User-Nachrichten"""
        message_text = update.message.text.lower()
        chat_id = update.effective_chat.id
        self.logger.info(f"User-Nachricht von Chat {chat_id}: {message_text}")
        
        # Prüfe ob User in Namens-Eingabe-Modus ist
        if hasattr(context, 'user_data') and context.user_data.get('waiting_for_name'):
            await super()._handle_name_input(update, context)
            return
        
        # Prüfe auf Hilfe-Anfragen
        if any(keyword in message_text for keyword in ["hilfe", "help", "problem", "fehler", "nicht"]):
            await self._show_help_options(update, context)
        else:
            await update.message.reply_text(
                "Sry Maus, das hab ich nicht verstanden 😅\n\n"
                "Ich kann folgendes für dich tun:\n"
                "• Hilfe anfordern 🆘\n"
                "• Namen ändern ✏️\n\n"
                "Nutze die Buttons oder schreibe 'Hilfe' für Unterstützung! 💕",
                reply_markup=self._get_main_keyboard(chat_id)
            )
    

    
    async def _show_help_options(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Zeige Hilfe-Optionen an"""
        help_text = """
🆘 **Wie kann ich dir helfen?**

Bitte wähle eine Option aus:
        """
        
        await update.message.reply_text(
            help_text,
            reply_markup=self._get_help_keyboard()
        )
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler für User-Callback-Queries (Button-Klicks)"""
        query = update.callback_query
        await query.answer()  # Bestätige den Button-Klick
        
        if query.data == "user_enter_name":
            await super()._handle_enter_name_button(query, context)
        elif query.data == "user_no_name":
            await super()._handle_no_name_button(query, context)
        elif query.data == "user_help_main":
            await self._handle_help_main_button(query, context)
        elif query.data == "user_change_name":
            await super()._handle_change_name_button(query, context)
        elif query.data == "user_join_game":
            await super()._handle_join_game_button(query, context)
        elif query.data.startswith("user_bahn_"):
            await super()._handle_bahn_selection(query, context)
        elif query.data == "user_help_moise":
            await self._handle_help_moise_button(query, context)
        elif query.data == "user_help_money":
            await self._handle_help_money_button(query, context)
        elif query.data == "user_help_other":
            await self._handle_help_other_button(query, context)
        elif query.data == "user_back":
            await self._handle_back_button(query, context)
    
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
    
    async def _handle_help_main_button(self, query, context):
        """Handler für Haupt-Hilfe-Button"""
        help_text = """
🆘 **Wie kann ich dir helfen?**

Bitte wähle eine Option aus:
        """
        
        await query.edit_message_text(
            help_text,
            reply_markup=self._get_help_keyboard()
        )
    
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
        
        # Extrahiere Bahn-Nummer aus callback_data (user_bahn_1 -> 1)
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
    
    async def _handle_help_moise_button(self, query, context):
        """Handler für Moise-Problem-Button"""
        user_id = query.from_user.id
        user_name = query.from_user.first_name or "Unbekannter User"
        
        # Bestätigung an User
        await query.edit_message_text(
            "🐭 **Problem mit den Moise gemeldet!**\n\n"
            "Dein Problem wurde an den Support weitergeleitet. "
            "Du wirst bald eine Antwort erhalten.",
            reply_markup=self._get_main_keyboard(user_id)
        )
        
        # Benachrichtigung an Support
        support_message = f"""
🆘 **User-Hilfeanfrage**

👤 **User:** {user_name} (ID: {user_id})
🐭 **Problem:** Die Moise laufen nicht

Bitte kümmere dich um diese Anfrage.
        """
        
        await self._notify_support(support_message)
        self.logger.info(f"Hilfeanfrage für Moise-Problem von User {user_id}")
    
    async def _handle_help_money_button(self, query, context):
        """Handler für Geld-Problem-Button"""
        user_id = query.from_user.id
        user_name = query.from_user.first_name or "Unbekannter User"
        
        # Bestätigung an User
        await query.edit_message_text(
            "💰 **Geld-Problem gemeldet!**\n\n"
            "Dein Problem wurde an den Support weitergeleitet. "
            "Du wirst bald eine Antwort erhalten.",
            reply_markup=self._get_main_keyboard(user_id)
        )
        
        # Benachrichtigung an Support
        support_message = f"""
🆘 **User-Hilfeanfrage**

👤 **User:** {user_name} (ID: {user_id})
💰 **Problem:** Geld wurde nicht gezählt

Bitte kümmere dich um diese Anfrage.
        """
        
        await self._notify_support(support_message)
        self.logger.info(f"Hilfeanfrage für Geld-Problem von User {user_id}")
    
    async def _handle_help_other_button(self, query, context):
        """Handler für Anderes-Problem-Button"""
        user_id = query.from_user.id
        user_name = query.from_user.first_name or "Unbekannter User"
        
        # Bestätigung an User
        await query.edit_message_text(
            "❓ **Anderes Problem gemeldet!**\n\n"
            "Dein Problem wurde an den Support weitergeleitet. "
            "Du wirst bald eine Antwort erhalten.",
            reply_markup=self._get_main_keyboard(user_id)
        )
        
        # Benachrichtigung an Support
        support_message = f"""
🆘 **User-Hilfeanfrage**

👤 **User:** {user_name} (ID: {user_id})
❓ **Problem:** Etwas anderes

Bitte kümmere dich um diese Anfrage.
        """
        
        await self._notify_support(support_message)
        self.logger.info(f"Hilfeanfrage für anderes Problem von User {user_id}")
    
    async def _handle_back_button(self, query, context):
        """Handler für Zurück-Button"""
        user_id = query.from_user.id
        await query.edit_message_text(
            "👤 **User-Modus aktiviert**\n\n"
            "Wähle eine Aktion aus:",
            reply_markup=self._get_main_keyboard(user_id)
        )
    
    async def _notify_support(self, message):
        """Benachrichtige Support-Mitglieder über User-Hilfeanfragen"""
        if not self.application:
            self.logger.warning("Bot Application nicht verfügbar für Support-Benachrichtigungen")
            return
            
        for chat_id in self.config.get_all_support_users():
            try:
                await self.application.bot.send_message(
                    chat_id=chat_id, 
                    text=message,
                    parse_mode='Markdown'
                )
                self.logger.info(f"User-Hilfeanfrage gesendet an Support Chat {chat_id}")
            except Exception as e:
                self.logger.error(f"Fehler beim Senden der Hilfeanfrage an Support Chat {chat_id}: {e}")
    
    def format_status(self, data):
        """User-spezifische Status-Formatierung mit vereinfachten Informationen"""
        try:
            status_text = "📊 **Moise System Status**\n\n"
            
            # Spiel aktiv (wichtigste Information für User)
            if 'is_game_active' in data:
                game_status = "🟢 Aktiv" if data['is_game_active'] else "🔴 Inaktiv"
                status_text += f"🎯 **Spiel Status:** {game_status}\n"
            
            # Game Error (wichtig für User)
            if 'game_error' in data and data['game_error'] != 'none':
                status_text += f"❌ **Fehler:** {data['game_error']}\n"
            
            # Gewonnene Maus (interessant für User)
            if 'gewonnene_maus' in data:
                status_text += f"🏆 **Gewonnene Maus:** {data['gewonnene_maus']}\n"
            
            # Gespielte Spiele (interessant für User)
            if 'gespielte_spiele' in data:
                status_text += f"🎮 **Gespielte Spiele:** {data['gespielte_spiele']}\n"
            
            # Maus Punktzahlen (vereinfacht für User)
            if 'maus_punktzahlen' in data and isinstance(data['maus_punktzahlen'], dict):
                status_text += "\n🐭 **Aktuelle Punktzahlen:**\n"
                for maus_id, points in data['maus_punktzahlen'].items():
                    status_text += f"  Maus {maus_id}: {points} Punkte\n"
            
            # Keine finanziellen Details für reguläre User
            status_text += "\n💡 **Hinweis:** Für detaillierte Informationen wende dich an den Support."
            
            return status_text
            
        except Exception as e:
            self.logger.error(f"Fehler beim Formatieren des User-Status: {e}")
            return f"❌ Fehler beim Formatieren des Status: {e}"
    
    def set_last_status(self, status):
        """Setze den letzten Status für User-Status-Abfragen"""
        self.last_status = status
    
 