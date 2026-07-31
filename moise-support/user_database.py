#!/usr/bin/env python3
"""
User-Datenbank für Moise Support Bot
"""
import json
import logging
from datetime import datetime
import os

class UserDatabase:
    """Datenbank für User-Verwaltung mit JSON"""
    
    def __init__(self, db_path="users.json"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._load_database()
    
    def _load_database(self):
        """Lade Datenbank aus JSON-Datei"""
        try:
            if os.path.exists(self.db_path):
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                self.logger.info(f"User-Datenbank geladen: {len(self.data)} User")
            else:
                self.data = {}
                self.logger.info("Neue User-Datenbank erstellt")
        except Exception as e:
            self.logger.error(f"Fehler beim Laden der Datenbank: {e}")
            self.data = {}
    
    def _save_database(self):
        """Speichere Datenbank in JSON-Datei"""
        try:
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            self.logger.debug("User-Datenbank gespeichert")
        except Exception as e:
            self.logger.error(f"Fehler beim Speichern der Datenbank: {e}")
    
    def user_exists(self, telegram_id):
        """Prüfe ob User in der Datenbank existiert"""
        return str(telegram_id) in self.data
    
    def add_user(self, telegram_id, name):
        """Füge neuen User zur Datenbank hinzu"""
        try:
            user_id = str(telegram_id)
            current_time = datetime.now().isoformat()
            
            self.data[user_id] = {
                "name": name,
                "created_at": current_time,
                "updated_at": current_time
            }
            
            self._save_database()
            self.logger.info(f"User {telegram_id} ({name}) zur Datenbank hinzugefügt")
            return True
        except Exception as e:
            self.logger.error(f"Fehler beim Hinzufügen des Users: {e}")
            return False
    
    def get_user_name(self, telegram_id):
        """Hole den Namen eines Users"""
        try:
            user_id = str(telegram_id)
            if user_id in self.data:
                return self.data[user_id]["name"]
            return None
        except Exception as e:
            self.logger.error(f"Fehler beim Abrufen des User-Namens: {e}")
            return None
    
    def name_exists(self, name):
        """Prüfe ob ein Name bereits existiert"""
        try:
            name_lower = name.lower().strip()
            for user_data in self.data.values():
                if user_data["name"].lower().strip() == name_lower:
                    return True
            return False
        except Exception as e:
            self.logger.error(f"Fehler beim Prüfen der Namens-Existenz: {e}")
            return False
    
    def get_user_by_name(self, name):
        """Hole User-ID anhand des Namens"""
        try:
            name_lower = name.lower().strip()
            for user_id, user_data in self.data.items():
                if user_data["name"].lower().strip() == name_lower:
                    return int(user_id)
            return None
        except Exception as e:
            self.logger.error(f"Fehler beim Abrufen der User-ID: {e}")
            return None
    
    def get_all_users(self):
        """Hole alle User aus der Datenbank"""
        return self.data
    
    def get_user_count(self):
        """Hole die Anzahl der User"""
        return len(self.data) 