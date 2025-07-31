# WebSocket Game-Daten Anzeige

Eine moderne Website zum Empfangen und Anzeigen von Live-Game-Daten über WebSocket-Verbindungen.

## Features

- ✅ Moderne, responsive Benutzeroberfläche
- ✅ WebSocket-Verbindung zu Game-Servern
- ✅ Live-Datenempfang alle 100ms
- ✅ Automatische Reconnect-Funktion
- ✅ Echtzeit-Verbindungsstatus
- ✅ Formatierte und Raw JSON-Anzeige
- ✅ Robuste Fehlerbehandlung
- ✅ Mobile-freundliches Design

## Verwendung

1. Öffnen Sie `index.html` in Ihrem Browser
2. Geben Sie die WebSocket-URL Ihres Game-Servers ein (z.B. `ws://localhost:8765`)
3. Klicken Sie auf "Verbinden" oder drücken Sie Enter
4. Optional: Aktivieren Sie "Auto-Reconnect" für automatische Wiederverbindung

## Beispiel-URLs zum Testen

- **Ihr Moise-Brain Server:**
  - `ws://localhost:8765` (Standard)

- **WebSocket Echo-Test:**
  - `wss://echo.websocket.org`

- **Lokale WebSocket-Server:**
  - `ws://localhost:8080`
  - `ws://localhost:3000`

## Dateien

- `index.html` - Haupt-HTML-Datei
- `styles.css` - CSS-Styling
- `script.js` - JavaScript-Funktionalität

## Technische Details

- **Vanilla JavaScript** - Keine externen Abhängigkeiten
- **WebSocket API** - Echtzeit-Datenübertragung
- **CSS Grid & Flexbox** - Responsive Layout
- **Auto-Reconnect** - Exponentieller Backoff
- **Error Handling** - Robuste Fehlerbehandlung
- **Live Updates** - Empfängt Daten alle 100ms

## Browser-Kompatibilität

- Chrome 60+
- Firefox 55+
- Safari 12+
- Edge 79+

## Lokaler Server starten

```bash
# Python 3
python -m http.server 8000

# Python 2
python -m SimpleHTTPServer 8000

# Node.js
npx http-server

# PHP
php -S localhost:8000
```

Dann öffnen Sie `http://localhost:8000` in Ihrem Browser. 