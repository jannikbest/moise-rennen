# Moise Support Bot

Ein Telegram Bot für das Moise Rennen System mit rollenbasierter Zugriffskontrolle.

## Features

### Rollenbasierte Zugriffskontrolle

Der Bot unterstützt zwei Nutzergruppen:

#### 👨‍💼 Support-Mitglieder
- **Zugriff:** Alle IDs in `ALLOWED_CHAT_IDS`
- **Befehle:**
  - `/start` - Bot starten
  - `/status` - Systemstatus abfragen
  - `/freispiel` - Freispiel starten
  - `/support` - Support-Befehle anzeigen
  - `/help` - Hilfe anzeigen
- **Funktionen:**
  - Vollzugriff auf alle Systemfunktionen
  - Freispiel-Start möglich
  - Erweiterte Status-Informationen
  - Automatische Benachrichtigungen bei Problemen

#### 👤 Reguläre User
- **Zugriff:** Alle anderen autorisierten User
- **Befehle:**
  - `/start` - Bot starten
  - `/status` - Systemstatus abfragen
  - `/help` - Hilfe anzeigen
- **Funktionen:**
  - Grundlegende Status-Abfragen
  - Benachrichtigungen über wichtige Systemänderungen

## Installation

1. **Abhängigkeiten installieren:**
```bash
pip install -r requirements.txt
```

2. **Umgebungsvariablen konfigurieren:**
Erstelle eine `.env` Datei:
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
ALLOWED_CHAT_IDS=123456789,987654321,555666777
MOISE_BRAIN_HOST=localhost
MOISE_BRAIN_PORT=8765
LOG_LEVEL=INFO
```

### Konfiguration der Rollen

- **Support-Mitglieder:** Alle Chat-IDs in `ALLOWED_CHAT_IDS` werden automatisch als Support-Mitglieder eingestuft
- **Reguläre User:** Zukünftig können weitere User hinzugefügt werden, die nicht in `ALLOWED_CHAT_IDS` stehen

## Verwendung

### Bot starten:
```bash
python bot.py
```

### Befehle:

#### Für alle User:
- `/start` - Bot starten und Willkommensnachricht
- `/help` - Hilfe und verfügbare Befehle anzeigen
- `/status` - Aktuellen Systemstatus abfragen

#### Nur für Support-Mitglieder:
- `/freispiel` - Freispiel starten
- `/support` - Support-spezifische Befehle anzeigen

## WebSocket Integration

Der Bot verbindet sich automatisch mit dem Moise Brain Server über WebSocket und:
- Überwacht den Systemstatus in Echtzeit
- Benachrichtigt bei Fehlern
- Zeigt detaillierte Status-Informationen

## Logging

Logs werden in `moise_support.log` geschrieben und enthalten:
- Bot-Aktivitäten
- WebSocket-Verbindungsstatus
- User-Interaktionen mit Rollen-Informationen
- Fehler und Warnungen

## Sicherheit

- Rollenbasierte Zugriffskontrolle
- Validierung aller Chat-IDs
- Sichere WebSocket-Verbindung
- Fehlerbehandlung für alle Operationen 