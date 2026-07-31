#!/usr/bin/env python3
"""
Support-Modul für Moise Support Bot
Enthält alle Support-spezifischen Funktionen und Befehle
"""
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from user_database import UserDatabase

class SupportHandler:
    """Handler für Support-spezifische Befehle und Funktionen"""
    
    def __init__(self, config, websocket=None, application=None, user_database=None):
        self.config = config
        self.websocket = websocket
        self.application = application
        self.logger = logging.getLogger(__name__)
        self.user_db = user_database
    
    def is_support_user(self, chat_id):
        """Prüfe ob User Support-Zugriff hat"""
        return self.config.is_support_user(chat_id)
    
    def is_game_ready(self):
        """Prüfe ob das Spiel im 'ready' Zustand ist"""
        if not hasattr(self, 'last_status') or not self.last_status:
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
    
    def _get_support_keyboard(self, chat_id=None):
        """Erstelle Support-spezifische Inline-Keyboard"""
        keyboard = []
        
        # Support-spezifische Buttons
        keyboard.extend([
            [
                InlineKeyboardButton("📊 Status anzeigen", callback_data="support_status"),
                InlineKeyboardButton("🎮 Freispiel schenken", callback_data="support_freispiel")
            ]
        ])
        
        # User-Funktionen (nur wenn Support einen Namen hat)
        if chat_id and self.user_db.user_exists(chat_id) and self.is_game_ready():
            keyboard.append([
                InlineKeyboardButton("🎮 Am Spiel teilnehmen", callback_data="support_join_game")
            ])
        
        keyboard.append([
            InlineKeyboardButton("✏️ Namen ändern", callback_data="support_change_name")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    def _get_welcome_keyboard(self):
        """Erstelle Willkommens-Keyboard für neue Support-User"""
        keyboard = [
            [
                InlineKeyboardButton("✅ Ja, hier ist mein Name", callback_data="support_enter_name")
            ],
            [
                InlineKeyboardButton("❌ Nein, das will ich nicht", callback_data="support_no_name")
            ],
            [
                InlineKeyboardButton("🆘 Nein, ich brauche den Moise-Support", callback_data="support_help_main")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Support-spezifischer Start-Befehl"""
        chat_id = update.effective_chat.id
        
        # Prüfe ob Support-User neu ist
        if not self.user_db.user_exists(chat_id):
            # Neuer Support-User - zeige Willkommensnachricht
            welcome_text = f"""
Hallo Maus, willkommen beim Moise-Support.

Du kannst hier Hilfe bekommen oder Infos zu deinen gewonnenen Spielen erhalten.

Willst du, dass deine gewonnenen Spiele gespeichert werden? Dann sag uns deinen Namen.
            """
            
            await update.message.reply_text(
                welcome_text,
                reply_markup=self._get_welcome_keyboard()
            )
            self.logger.info(f"Neuer Support-User {chat_id} begrüßt")
        else:
            # Bekannter Support-User - normale Begrüßung
            user_name = self.user_db.get_user_name(chat_id)
            welcome_text = f"""
🤖 Willkommen zurück beim {self.config.bot_name}!

👨‍💼 **Support-Modus aktiviert**

Hallo {user_name}, du hast vollen Zugriff auf alle Funktionen:
• Systemstatus überwachen
• Freispiel starten
• Benachrichtigungen verwalten

Wähle eine Aktion aus:
            """
            
            await update.message.reply_text(
                welcome_text,
                reply_markup=self._get_support_keyboard(chat_id)
            )
            self.logger.info(f"Bekannter Support-User {chat_id} ({user_name}) begrüßt")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Support-spezifischer Help-Befehl"""
        help_text = """
📋 **Support-Befehle:**

/start - Bot starten
/status - Systemstatus abfragen
/freispiel - Freispiel starten
/help - Diese Hilfe anzeigen

Der Bot informiert dich automatisch über:
• Systemfehler
• Münzzähler-Probleme
• Controller-Verbindungsprobleme
• Spielstatus-Änderungen
        """
        
        await update.message.reply_text(
            help_text,
            reply_markup=self._get_support_keyboard(chat_id)
        )
    
    async def freispiel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler für /freispiel Befehl - nur für Support"""
        await self._execute_freispiel(update, context)
    
    async def _execute_freispiel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Führe Freispiel-Action aus"""
        if not self.websocket:
            await update.message.reply_text("❌ **Fehler:** Keine WebSocket Verbindung verfügbar")
            return
        
        try:
            # Sende freispiel Action an WebSocket
            freispiel_message = json.dumps({"action": "freispiel"})
            await self.websocket.send(freispiel_message)
            
            await update.message.reply_text("🎮 **Freispiel gestartet!**")
            self.logger.info(f"Freispiel-Action gesendet von Support Chat {update.effective_chat.id}")
            
        except Exception as e:
            error_msg = f"❌ **Fehler beim Senden der Freispiel-Action:** {e}"
            await update.message.reply_text(error_msg)
            self.logger.error(error_msg)
    
    async def support_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler für /support Befehl - nur für Support"""
        support_text = """
🔧 **Support-Befehle:**

/status - Detaillierter Systemstatus
/freispiel - Freispiel starten
/support - Diese Hilfe anzeigen

**Support-Funktionen:**
• Vollzugriff auf alle Systemfunktionen
• Freispiel-Start möglich
• Erweiterte Status-Informationen
• Automatische Benachrichtigungen bei Problemen
        """
        
        await update.message.reply_text(
            support_text,
            reply_markup=self._get_support_keyboard(chat_id)
        )
        self.logger.info(f"Support-Befehl von Chat {update.effective_chat.id}")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler für Support-Nachrichten"""
        message_text = update.message.text.lower()
        chat_id = update.effective_chat.id
        self.logger.info(f"Support-Nachricht von Chat {chat_id}: {message_text}")
        
        # Prüfe ob Support-User in Namens-Eingabe-Modus ist
        if hasattr(context, 'user_data') and context.user_data.get('waiting_for_name'):
            await self._handle_name_input(update, context)
            return
        
        # Prüfe auf Hilfe-Anfragen
        if any(keyword in message_text for keyword in ["hilfe", "help", "problem", "fehler", "nicht"]):
            await self._show_help_options(update, context)
        else:
            await update.message.reply_text(
                "Sry Maus, das hab ich nicht verstanden 😅\n\n"
                "Ich kann folgendes für dich tun:\n"
                "• Status anzeigen 📊\n"
                "• Freispiel schenken 🎮\n"
                "• Namen ändern ✏️\n\n"
                "Nutze die Buttons oder schreibe 'Hilfe' für Unterstützung! 💕",
                reply_markup=self._get_support_keyboard(chat_id)
            )
    
    async def _handle_name_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler für Namens-Eingabe bei Support-Usern"""
        chat_id = update.effective_chat.id
        name = update.message.text.strip()
        is_changing_name = context.user_data.get('is_changing_name', False)
        
        if len(name) < 2:
            await update.message.reply_text(
                "Hmm, das ist ein bisschen zu kurz 🧐\n\n"
                "Bitte gib einen Namen mit mindestens 2 Zeichen ein ✨"
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
                    "• Status anzeigen 📊\n"
                    "• Freispiel schenken 🎮\n"
                    "• Namen ändern ✏️\n\n"
                    "Nutze die Buttons oder schreibe 'Hilfe' für Unterstützung! 💕",
                    reply_markup=self._get_support_keyboard(chat_id)
                )
                self.logger.info(f"Support-User {chat_id} hat Namen zu '{name}' geändert")
            else:
                await update.message.reply_text(
                    f"Yay, vielen Dank {name}! 🎉\n\n"
                    "Dein Name wurde gespeichert. Du kannst jetzt alle Support-Funktionen nutzen! 💪",
                    reply_markup=self._get_support_keyboard(chat_id)
                )
                self.logger.info(f"Support-User {chat_id} mit Namen '{name}' in Datenbank gespeichert")
        else:
            await update.message.reply_text(
                "Ups, da ist etwas schiefgegangen 😅\n\n"
                "Es gab ein Problem beim Speichern deines Namens. "
                "Du kannst trotzdem alle Support-Funktionen nutzen! 💪",
                reply_markup=self._get_support_keyboard(chat_id)
            )
        
        # Entferne Namens-Eingabe-Modus
        context.user_data.pop('waiting_for_name', None)
        context.user_data.pop('is_changing_name', None)
    
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
    
    def _get_help_keyboard(self):
        """Erstelle Hilfe-Keyboard mit Unteroptionen"""
        keyboard = [
            [
                InlineKeyboardButton("🐭 Die Moise laufen nicht", callback_data="support_help_moise")
            ],
            [
                InlineKeyboardButton("💰 Mein Geld wurde nicht gezählt", callback_data="support_help_money")
            ],
            [
                InlineKeyboardButton("❓ Etwas anderes", callback_data="support_help_other")
            ],
            [
                InlineKeyboardButton("🔙 Zurück", callback_data="support_back")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def _get_bahn_keyboard(self):
        """Erstelle Bahn-Auswahl-Keyboard für Support"""
        keyboard = [
            [
                InlineKeyboardButton("🏁 Bahn 1", callback_data="support_bahn_1"),
                InlineKeyboardButton("🏁 Bahn 2", callback_data="support_bahn_2")
            ],
            [
                InlineKeyboardButton("🏁 Bahn 3", callback_data="support_bahn_3"),
                InlineKeyboardButton("🏁 Bahn 4", callback_data="support_bahn_4")
            ],
            [
                InlineKeyboardButton("🏁 Bahn 5", callback_data="support_bahn_5")
            ],
            [
                InlineKeyboardButton("🔙 Zurück", callback_data="support_back")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler für Support-Callback-Queries (Button-Klicks)"""
        query = update.callback_query
        await query.answer()  # Bestätige den Button-Klick
        
        if query.data == "support_enter_name":
            await self._handle_enter_name_button(query, context)
        elif query.data == "support_no_name":
            await self._handle_no_name_button(query, context)
        elif query.data == "support_change_name":
            await self._handle_change_name_button(query, context)
        elif query.data == "support_status":
            await self._handle_status_button(query, context)
        elif query.data == "support_freispiel":
            await self._handle_freispiel_button(query, context)
        elif query.data == "support_join_game":
            await self._handle_join_game_button(query, context)
        elif query.data.startswith("support_bahn_"):
            await self._handle_bahn_selection(query, context)
        elif query.data == "support_help_main":
            await self._handle_help_main_button(query, context)
        elif query.data == "support_help_moise":
            await self._handle_help_moise_button(query, context)
        elif query.data == "support_help_money":
            await self._handle_help_money_button(query, context)
        elif query.data == "support_help_other":
            await self._handle_help_other_button(query, context)
        elif query.data == "support_back":
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
        await query.edit_message_text(
            "❌ **Kein Problem Maus!**\n\n"
            "Wenn du es dir anders überlegt hast, melde dich gern nochmal.",
            reply_markup=self._get_support_keyboard(query.from_user.id)
        )
        self.logger.info(f"Support-User {query.from_user.id} hat Namens-Speicherung abgelehnt")
    
    async def _handle_change_name_button(self, query, context):
        """Handler für Namen-Änderungs-Button"""
        await query.edit_message_text(
            "✏️ **Namen ändern**\n\n"
            "Bitte schreibe jetzt deinen neuen Namen:",
        )
        
        # Setze Namens-Änderungs-Modus
        context.user_data['waiting_for_name'] = True
        context.user_data['is_changing_name'] = True
    
    async def _handle_status_button(self, query, context):
        """Handler für Status-Button"""
        # Hier würden wir den aktuellen Status abrufen und anzeigen
        # Da wir keinen direkten Zugriff auf last_status haben, zeigen wir eine Nachricht
        await query.edit_message_text(
            "📊 **Status wird abgerufen...**\n\n"
            "Nutze /status für den aktuellen Systemstatus.",
            reply_markup=self._get_support_keyboard()
        )
    
    async def _handle_freispiel_button(self, query, context):
        """Handler für Freispiel-Button"""
        if not self.websocket:
            await query.edit_message_text(
                "❌ **Fehler:** Keine WebSocket Verbindung verfügbar",
                reply_markup=self._get_support_keyboard(query.from_user.id)
            )
            return
        
        try:
            # Sende freispiel Action an WebSocket
            freispiel_message = json.dumps({"action": "freispiel"})
            await self.websocket.send(freispiel_message)
            
            await query.edit_message_text(
                "🎮 **Freispiel gestartet!**",
                reply_markup=self._get_support_keyboard(query.from_user.id)
            )
            self.logger.info(f"Freispiel-Action gesendet von Support Button Chat {query.from_user.id}")
            
        except Exception as e:
            error_msg = f"❌ **Fehler beim Senden der Freispiel-Action:** {e}"
            await query.edit_message_text(
                error_msg,
                reply_markup=self._get_support_keyboard(query.from_user.id)
            )
            self.logger.error(error_msg)
    
    async def _handle_join_game_button(self, query, context):
        """Handler für Spiel-Teilnahme-Button (Support)"""
        chat_id = query.from_user.id
        
        # Prüfe ob Support einen Namen hat
        if not self.user_db.user_exists(chat_id):
            await query.edit_message_text(
                "❌ **Du brauchst einen Namen!**\n\n"
                "Du musst zuerst deinen Namen eingeben, bevor du am Spiel teilnehmen kannst. "
                "Bitte ändere zuerst deinen Namen.",
                reply_markup=self._get_support_keyboard(chat_id)
            )
            return
        
        # Prüfe ob das Spiel ready ist
        if not self.is_game_ready():
            await query.edit_message_text(
                "⏳ **Spiel noch nicht bereit!**\n\n"
                "Das Spiel ist momentan nicht im 'ready' Zustand. "
                "Bitte warte, bis das Spiel bereit ist.",
                reply_markup=self._get_support_keyboard(chat_id)
            )
            return
        
        user_name = self.user_db.get_user_name(chat_id)
        
        await query.edit_message_text(
            f"🎮 **Spiel-Teilnahme für {user_name} (Support)**\n\n"
            "Auf welcher Bahn möchtest du spielen?\n"
            "Wähle eine Bahn aus:",
            reply_markup=self._get_bahn_keyboard()
        )
    
    async def _handle_bahn_selection(self, query, context):
        """Handler für Bahn-Auswahl (Support)"""
        chat_id = query.from_user.id
        user_name = self.user_db.get_user_name(chat_id)
        
        # Extrahiere Bahn-Nummer aus callback_data (support_bahn_1 -> 1)
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
                self.logger.info(f"Support Spiel-Teilnahme gesendet: {user_name} auf Bahn {bahn_num}")
                
                await query.edit_message_text(
                    f"✅ **Spiel-Teilnahme erfolgreich!**\n\n"
                    f"Du spielst jetzt als **{user_name}** auf **Bahn {bahn_num}**.\n"
                    f"Viel Glück! 🍀",
                    reply_markup=self._get_support_keyboard(chat_id)
                )
            except Exception as e:
                self.logger.error(f"Fehler beim Senden der Support Spiel-Teilnahme: {e}")
                await query.edit_message_text(
                    "❌ **Fehler beim Spiel-Beitritt**\n\n"
                    "Es gab ein Problem mit der Verbindung. "
                    "Bitte versuche es später nochmal.",
                    reply_markup=self._get_support_keyboard(chat_id)
                )
        else:
            await query.edit_message_text(
                "❌ **Keine Verbindung**\n\n"
                "Der Bot ist nicht mit dem Spiel verbunden. "
                "Bitte versuche es später nochmal.",
                reply_markup=self._get_support_keyboard(chat_id)
            )
    
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
    
    async def _handle_help_moise_button(self, query, context):
        """Handler für Moise-Problem-Button"""
        user_id = query.from_user.id
        user_name = query.from_user.first_name or "Unbekannter User"
        
        # Bestätigung an Support-User
        await query.edit_message_text(
            "🐭 **Problem mit den Moise gemeldet!**\n\n"
            "Das Problem wurde dokumentiert. Du kannst es jetzt bearbeiten.",
            reply_markup=self._get_support_keyboard(user_id)
        )
        
        # Logge das Problem
        self.logger.info(f"Moise-Problem dokumentiert von Support-User {user_id} ({user_name})")
    
    async def _handle_help_money_button(self, query, context):
        """Handler für Geld-Problem-Button"""
        user_id = query.from_user.id
        user_name = query.from_user.first_name or "Unbekannter User"
        
        # Bestätigung an Support-User
        await query.edit_message_text(
            "💰 **Geld-Problem dokumentiert!**\n\n"
            "Das Problem wurde dokumentiert. Du kannst es jetzt bearbeiten.",
            reply_markup=self._get_support_keyboard(user_id)
        )
        
        # Logge das Problem
        self.logger.info(f"Geld-Problem dokumentiert von Support-User {user_id} ({user_name})")
    
    async def _handle_help_other_button(self, query, context):
        """Handler für Anderes-Problem-Button"""
        user_id = query.from_user.id
        user_name = query.from_user.first_name or "Unbekannter User"
        
        # Bestätigung an Support-User
        await query.edit_message_text(
            "❓ **Anderes Problem dokumentiert!**\n\n"
            "Das Problem wurde dokumentiert. Du kannst es jetzt bearbeiten.",
            reply_markup=self._get_support_keyboard(user_id)
        )
        
        # Logge das Problem
        self.logger.info(f"Anderes Problem dokumentiert von Support-User {user_id} ({user_name})")
    
    async def _handle_back_button(self, query, context):
        """Handler für Zurück-Button"""
        user_id = query.from_user.id
        await query.edit_message_text(
            "👨‍💼 **Support-Modus aktiviert**\n\n"
            "Wähle eine Aktion aus:",
            reply_markup=self._get_support_keyboard(user_id)
        )
    
    def format_status(self, data):
        """Support-spezifische Status-Formatierung mit erweiterten Informationen"""
        try:
            status_text = "📊 **Moise System Status (Support-Ansicht)**\n\n"
            
            # Guthaben
            if 'guthaben' in data:
                euros = data['guthaben'] / 100
                status_text += f"💰 **Guthaben:** {euros:.2f}€\n"
            
            # Einzahlungen
            if 'einzahlungen' in data:
                euros = data['einzahlungen'] / 100
                status_text += f"📥 **Einzahlungen:** {euros:.2f}€\n"
            
            # Ausgaben
            if 'ausgaben' in data:
                euros = data['ausgaben'] / 100
                status_text += f"📤 **Ausgaben:** {euros:.2f}€\n"
            
            # Gespielte Spiele
            if 'gespielte_spiele' in data:
                status_text += f"🎮 **Gespielte Spiele:** {data['gespielte_spiele']}\n"
            
            # Gewonnene Maus
            if 'gewonnene_maus' in data:
                status_text += f"🏆 **Gewonnene Maus:** {data['gewonnene_maus']}\n"
            
            # Spiel aktiv
            if 'is_game_active' in data:
                game_status = "🟢 Aktiv" if data['is_game_active'] else "🔴 Inaktiv"
                status_text += f"🎯 **Spiel Status:** {game_status}\n"
            
            # Game Error
            if 'game_error' in data and data['game_error'] != 'none':
                status_text += f"❌ **Fehler:** {data['game_error']}\n"
            
            # Maus Punktzahlen
            if 'maus_punktzahlen' in data and isinstance(data['maus_punktzahlen'], dict):
                status_text += "\n🐭 **Maus Punktzahlen:**\n"
                for maus_id, points in data['maus_punktzahlen'].items():
                    status_text += f"  Maus {maus_id}: {points} Punkte\n"
            
            # Support-spezifische Zusatzinformationen
            status_text += "\n🔧 **Support-Info:**\n"
            status_text += f"• WebSocket Status: {'🟢 Verbunden' if self.websocket else '🔴 Getrennt'}\n"
            status_text += f"• Support-Mitglieder: {len(self.config.get_all_support_users())}\n"
            
            return status_text
            
        except Exception as e:
            self.logger.error(f"Fehler beim Formatieren des Support-Status: {e}")
            return f"❌ Fehler beim Formatieren des Status: {e}"
    
    def set_last_status(self, status):
        """Setze den letzten Status für Support-Status-Abfragen"""
        self.last_status = status 