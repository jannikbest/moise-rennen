#!/usr/bin/env python3
"""
Konfiguration für Moise Support Telegram Bot
"""
import os
from dotenv import load_dotenv

# Lade Umgebungsvariablen aus .env Datei
load_dotenv()

class Config:
    """Konfiguration für den Telegram Bot"""
    
    def __init__(self):
        # Telegram Bot Token (aus Umgebungsvariable oder .env)
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        
        # Erlaubte Chat IDs (wer darf den Bot nutzen)
        self.allowed_chat_ids = self._parse_allowed_chat_ids()
        
        # Support Chat IDs (alle in ALLOWED_CHAT_IDS sind Supporter)
        self.support_chat_ids = self.allowed_chat_ids.copy()
        
        # Moise Brain Server Konfiguration
        self.moise_brain_host = os.getenv('MOISE_BRAIN_HOST', 'localhost')
        self.moise_brain_port = int(os.getenv('MOISE_BRAIN_PORT', '8765'))
        
        # Logging Level
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        
        # Bot Einstellungen
        self.bot_name = "Moise Support Bot"
        self.bot_description = "Support Bot für Moise Rennen System"
        
    def _parse_allowed_chat_ids(self):
        """Parse erlaubte Chat IDs aus Umgebungsvariable"""
        chat_ids_str = os.getenv('ALLOWED_CHAT_IDS', '')
        if not chat_ids_str:
            return []
        
        try:
            # Komma-getrennte Liste von Chat IDs
            return [int(cid.strip()) for cid in chat_ids_str.split(',') if cid.strip()]
        except ValueError:
            print("Warnung: Ungültige Chat IDs in ALLOWED_CHAT_IDS")
            return []
    
    def is_chat_allowed(self, chat_id):
        """Prüfe ob Chat ID erlaubt ist (Support oder User)"""
        return chat_id in self.allowed_chat_ids or self.is_support_user(chat_id)
    
    def is_support_user(self, chat_id):
        """Prüfe ob Chat ID ein Support-User ist"""
        return chat_id in self.support_chat_ids
    
    def is_regular_user(self, chat_id):
        """Prüfe ob Chat ID ein regulärer User ist (nicht Support)"""
        return chat_id in self.allowed_chat_ids and not self.is_support_user(chat_id)
    
    def get_user_role(self, chat_id):
        """Ermittle die Rolle des Users"""
        if self.is_support_user(chat_id):
            return "support"
        elif self.is_chat_allowed(chat_id):
            return "user"
        else:
            return "unauthorized"
    
    def get_all_support_users(self):
        """Gebe alle Support-User zurück"""
        return self.support_chat_ids.copy()
    
    def get_all_regular_users(self):
        """Gebe alle regulären User zurück"""
        return [chat_id for chat_id in self.allowed_chat_ids if not self.is_support_user(chat_id)]
    
    def validate_config(self):
        """Validiere Konfiguration"""
        errors = []
        
        if not self.bot_token:
            errors.append("TELEGRAM_BOT_TOKEN nicht gesetzt")
        
        if not self.allowed_chat_ids:
            errors.append("ALLOWED_CHAT_IDS nicht gesetzt")
        
        return errors 