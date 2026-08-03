class WebSocketClient {
    constructor(onMessage, onStatus) {
        this.websocket = null;
        this.isConnected = false;
        this.onMessage = onMessage || (() => {});
        this.onStatus = onStatus || (() => {});
        this.reconnectAttempts = 0;
        this._url = null;
        this._pending = new Map();
        this._reqSeq = 1;
    }

    connect(serverUrl) {
        let wsUrl = serverUrl || MOISE_CONFIG.websocket.url;
        if (wsUrl.startsWith('http://')) wsUrl = wsUrl.replace('http://', 'ws://');
        else if (wsUrl.startsWith('https://')) wsUrl = wsUrl.replace('https://', 'wss://');
        else if (!wsUrl.startsWith('ws://') && !wsUrl.startsWith('wss://')) wsUrl = `ws://${wsUrl}`;

        this._url = wsUrl;

        try {
            this.websocket = new WebSocket(wsUrl);
        } catch (e) {
            this.isConnected = false;
            this.onStatus(false);
            this.scheduleReconnect();
            return;
        }

        this.websocket.onopen = () => {
            this.isConnected = true;
            this.reconnectAttempts = 0;
            this.onStatus(true);
        };

        this.websocket.onclose = () => {
            this.isConnected = false;
            this.onStatus(false);
            this.scheduleReconnect();
        };

        this.websocket.onerror = () => {
            this.isConnected = false;
            this.onStatus(false);
        };

        this.websocket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data && data.request_id && this._pending.has(data.request_id)) {
                    const { resolve } = this._pending.get(data.request_id);
                    this._pending.delete(data.request_id);
                    resolve(data);
                    return;
                }
                this.onMessage(data);
            } catch (e) {
                console.error('JSON parse error', e);
            }
        };
    }

    scheduleReconnect() {
        const max = MOISE_CONFIG.websocket.maxReconnectAttempts;
        if (max >= 0 && this.reconnectAttempts >= max) return;
        this.reconnectAttempts += 1;
        setTimeout(() => this.connect(this._url), MOISE_CONFIG.websocket.reconnectInterval);
    }

    send(obj) {
        if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
            return Promise.reject(new Error('not connected'));
        }
        this.websocket.send(JSON.stringify(obj));
        return Promise.resolve();
    }

    request(action, payload) {
        const request_id = `r${this._reqSeq++}`;
        const body = Object.assign({ action, request_id }, payload || {});
        return new Promise((resolve, reject) => {
            const timer = setTimeout(() => {
                this._pending.delete(request_id);
                reject(new Error('timeout'));
            }, 8000);
            this._pending.set(request_id, {
                resolve: (data) => {
                    clearTimeout(timer);
                    resolve(data);
                }
            });
            this.send(body).catch((e) => {
                clearTimeout(timer);
                this._pending.delete(request_id);
                reject(e);
            });
        });
    }

    disconnect() {
        if (this.websocket) this.websocket.close();
    }
}
