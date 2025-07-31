class WebSocketDataClient {
    constructor() {
        this.websocket = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.init();
    }

    init() {
        this.bindEvents();
        this.updateStatus('Nicht verbunden', 'disconnected');
    }

    bindEvents() {
        const connectBtn = document.getElementById('fetchBtn');
        const autoConnectBtn = document.getElementById('autoFetchBtn');
        const serverUrlInput = document.getElementById('serverUrl');

        connectBtn.addEventListener('click', () => this.toggleConnection());
        autoConnectBtn.addEventListener('click', () => this.toggleAutoReconnect());
        serverUrlInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.toggleConnection();
            }
        });
    }

    toggleConnection() {
        if (this.isConnected) {
            this.disconnect();
        } else {
            this.connect();
        }
    }

    connect() {
        const serverUrl = document.getElementById('serverUrl').value.trim();
        
        if (!serverUrl) {
            this.showError('Bitte geben Sie eine WebSocket-URL ein.');
            return;
        }

        // Konvertiere HTTP-URL zu WebSocket-URL falls nötig
        let wsUrl = serverUrl;
        if (serverUrl.startsWith('http://')) {
            wsUrl = serverUrl.replace('http://', 'ws://');
        } else if (serverUrl.startsWith('https://')) {
            wsUrl = serverUrl.replace('https://', 'wss://');
        } else if (!serverUrl.startsWith('ws://') && !serverUrl.startsWith('wss://')) {
            wsUrl = `ws://${serverUrl}`;
        }
        
        console.log('Versuche Verbindung zu:', wsUrl);

        this.updateStatus('Verbinde...', 'connecting');
        this.showLoading();

        try {
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                this.isConnected = true;
                this.reconnectAttempts = 0;
                this.updateStatus('Verbunden', 'connected');
                this.hideError();
                this.updateButtonText();
                console.log('WebSocket-Verbindung hergestellt');
            };

            this.websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.displayData(data);
                } catch (error) {
                    console.error('Fehler beim Parsen der JSON-Daten:', error);
                    this.showError(`JSON-Parse-Fehler: ${error.message}`);
                }
            };

            this.websocket.onclose = (event) => {
                this.isConnected = false;
                this.updateStatus('Verbindung getrennt', 'disconnected');
                this.updateButtonText();
                console.log('WebSocket-Verbindung geschlossen:', event.code, event.reason);
                
                // Detaillierte Fehlermeldung basierend auf Close-Code
                let closeMessage = '';
                switch (event.code) {
                    case 1000:
                        closeMessage = 'Verbindung normal geschlossen';
                        break;
                    case 1001:
                        closeMessage = 'Server verlässt die Verbindung';
                        break;
                    case 1002:
                        closeMessage = 'Protokollfehler';
                        break;
                    case 1003:
                        closeMessage = 'Nicht unterstützter Datentyp';
                        break;
                    case 1006:
                        closeMessage = 'Verbindung abnormal geschlossen (Server nicht erreichbar)';
                        break;
                    case 1011:
                        closeMessage = 'Server-Fehler';
                        break;
                    case 1015:
                        closeMessage = 'TLS-Handshake fehlgeschlagen';
                        break;
                    default:
                        closeMessage = `Unbekannter Fehler (Code: ${event.code})`;
                }
                
                if (this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.scheduleReconnect();
                } else {
                    this.showError(`Verbindung getrennt: ${closeMessage}. Maximale Anzahl von Reconnect-Versuchen erreicht.`);
                }
            };

            this.websocket.onerror = (error) => {
                console.error('WebSocket-Fehler:', error);
                this.updateStatus('Verbindungsfehler', 'error');
                
                // Detailliertere Fehlermeldung
                let errorMessage = 'WebSocket-Verbindungsfehler';
                if (error && error.message) {
                    errorMessage += `: ${error.message}`;
                }
                
                // Prüfe spezifische Fehler
                if (this.websocket && this.websocket.readyState === WebSocket.CONNECTING) {
                    errorMessage = 'Verbindung zum Server fehlgeschlagen. Prüfen Sie:';
                    errorMessage += '\n• Läuft der Server auf ws://localhost:8765?';
                    errorMessage += '\n• Ist der Port 8765 erreichbar?';
                    errorMessage += '\n• Sind Firewall-Einstellungen korrekt?';
                }
                
                this.showError(errorMessage);
            };

        } catch (error) {
            console.error('Fehler beim Erstellen der WebSocket-Verbindung:', error);
            this.updateStatus('Fehler', 'error');
            
            let errorMessage = `Fehler beim Verbinden: ${error.message}`;
            
            // Spezifische Fehlermeldungen
            if (error.message.includes('Invalid URL')) {
                errorMessage = 'Ungültige WebSocket-URL. Verwenden Sie ws:// oder wss://';
            } else if (error.message.includes('Network Error')) {
                errorMessage = 'Netzwerkfehler. Server nicht erreichbar.';
            } else if (error.message.includes('Connection refused')) {
                errorMessage = 'Verbindung verweigert. Server läuft möglicherweise nicht.';
            }
            
            this.showError(errorMessage);
        }
    }

    disconnect() {
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
        this.isConnected = false;
        this.updateStatus('Nicht verbunden', 'disconnected');
        this.updateButtonText();
    }

    scheduleReconnect() {
        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
        this.updateStatus(`Reconnect in ${delay/1000}s... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`, 'connecting');
        
        setTimeout(() => {
            if (!this.isConnected) {
                this.connect();
            }
        }, delay);
    }

    toggleAutoReconnect() {
        const autoConnectBtn = document.getElementById('autoFetchBtn');
        
        if (this.maxReconnectAttempts > 0) {
            this.maxReconnectAttempts = 0; // Deaktiviere Auto-Reconnect
            autoConnectBtn.textContent = 'Auto-Reconnect aktivieren';
            autoConnectBtn.classList.remove('auto-active');
        } else {
            this.maxReconnectAttempts = 5; // Aktiviere Auto-Reconnect
            autoConnectBtn.textContent = 'Auto-Reconnect deaktivieren';
            autoConnectBtn.classList.add('auto-active');
        }
    }

    updateButtonText() {
        const connectBtn = document.getElementById('fetchBtn');
        connectBtn.textContent = this.isConnected ? 'Verbindung trennen' : 'Verbinden';
    }

    displayData(data) {
        const dataDisplay = document.getElementById('dataDisplay');
        const rawJson = document.getElementById('rawJson');

        if (!data) {
            dataDisplay.innerHTML = '<div class="placeholder">Keine Daten verfügbar</div>';
            rawJson.textContent = 'Keine Daten verfügbar';
            return;
        }

        // Raw JSON anzeigen
        rawJson.textContent = JSON.stringify(data, null, 2);

        // Formatierte Daten anzeigen
        dataDisplay.innerHTML = this.formatData(data);
    }

    formatData(data) {
        if (typeof data !== 'object' || data === null) {
            return `<div class="data-item">
                <div class="data-key">Wert</div>
                <div class="data-value">${String(data)}</div>
            </div>`;
        }

        let html = '';
        
        if (Array.isArray(data)) {
            // Array verarbeiten
            data.forEach((item, index) => {
                if (typeof item === 'object' && item !== null) {
                    html += `<div class="data-item">
                        <div class="data-key">Element ${index + 1}</div>
                        <div class="data-value">${this.formatObject(item)}</div>
                    </div>`;
                } else {
                    html += `<div class="data-item">
                        <div class="data-key">Element ${index + 1}</div>
                        <div class="data-value">${String(item)}</div>
                    </div>`;
                }
            });
        } else {
            // Objekt verarbeiten
            html = this.formatObject(data);
        }

        return html;
    }

    formatObject(obj) {
        let html = '';
        for (const [key, value] of Object.entries(obj)) {
            if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
                html += `<div class="data-item">
                    <div class="data-key">${this.capitalizeFirst(key)}</div>
                    <div class="data-value">${this.formatObject(value)}</div>
                </div>`;
            } else if (Array.isArray(value)) {
                html += `<div class="data-item">
                    <div class="data-key">${this.capitalizeFirst(key)}</div>
                    <div class="data-value">[${value.length} Elemente] ${JSON.stringify(value)}</div>
                </div>`;
            } else {
                html += `<div class="data-item">
                    <div class="data-key">${this.capitalizeFirst(key)}</div>
                    <div class="data-value">${String(value)}</div>
                </div>`;
            }
        }
        return html;
    }

    capitalizeFirst(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }

    showLoading() {
        const dataDisplay = document.getElementById('dataDisplay');
        dataDisplay.innerHTML = '<div class="loading">Lade Daten...</div>';
    }

    updateStatus(text, status) {
        const statusText = document.getElementById('statusText');
        const statusDot = document.querySelector('.status-dot');
        
        statusText.textContent = text;
        statusDot.className = 'status-dot';
        
        if (status === 'connected') {
            statusDot.classList.add('connected');
        } else if (status === 'error') {
            statusDot.classList.add('error');
        }
    }

    showError(message) {
        const errorDisplay = document.getElementById('errorDisplay');
        // Ersetze \n durch <br> für Zeilenumbrüche in HTML
        errorDisplay.innerHTML = message.replace(/\n/g, '<br>');
        errorDisplay.classList.remove('hidden');
        
        // Log für Debugging
        console.error('WebSocket Error:', message);
    }

    hideError() {
        const errorDisplay = document.getElementById('errorDisplay');
        errorDisplay.classList.add('hidden');
    }

    toggleAutoFetch() {
        const autoFetchBtn = document.getElementById('autoFetchBtn');
        
        if (this.isAutoFetching) {
            this.stopAutoFetch();
            autoFetchBtn.textContent = 'Auto-Update';
            autoFetchBtn.classList.remove('auto-active');
        } else {
            this.startAutoFetch();
            autoFetchBtn.textContent = 'Auto-Update stoppen';
            autoFetchBtn.classList.add('auto-active');
        }
    }

}

// Initialisierung wenn DOM geladen ist
document.addEventListener('DOMContentLoaded', () => {
    new WebSocketDataClient();
});

// Beispiel für WebSocket-Server URLs
function showWebSocketExamples() {
    console.log('WebSocket-Server URLs:');
    console.log('- ws://localhost:8765 (Ihr Moise-Brain Server)');
    console.log('- wss://echo.websocket.org (Echo-Test)');
    console.log('');
    console.log('Die Website konvertiert automatisch HTTP-URLs zu WebSocket-URLs');
} 