class MoiseApp {
    constructor() {
        this.lastSeq = -1;
        this.lastMessageAt = 0;
        this.lastData = null;
        this.animation = new MausAnimation();
        this.view = new KinoView(this.animation);
        this.claimView = new ClaimView(this);
        this.statsView = new StatsView();
        this.statsDetail = new StatsDetail();
        this.ws = new WebSocketClient(
            (data) => this.onMessage(data),
            (ok) => this.onStatus(ok)
        );
    }

    start() {
        this.ws.connect(MOISE_CONFIG.websocket.url);
        this.view.showOffline('stats');
        this.updateConnBadge(false);
        setInterval(() => this.checkStale(), 500);
    }

    request(action, payload) {
        return this.ws.request(action, payload);
    }

    updateConnBadge(wsOk) {
        const badge = document.getElementById('connBadge');
        const text = document.getElementById('connBadgeText');
        if (!badge || !text) return;

        if (!wsOk) {
            badge.classList.remove('connected', 'searching');
            text.textContent = 'Offline';
            return;
        }

        const data = this.lastData;
        const espOk = !!(data && data.espConnected);
        const name = (data && data.espName) || 'moise-rennen';
        const host = (data && data.espHost) || '';
        badge.classList.toggle('connected', espOk);
        badge.classList.toggle('searching', !espOk);
        if (espOk) {
            text.textContent = host
                ? `Connected · ${name} · ${host}`
                : `Connected · ${name}`;
        } else {
            text.textContent = host
                ? `Searching for controller · ${host}`
                : 'Searching for controller…';
        }
    }

    onStatus(ok) {
        if (!ok) {
            this.lastData = null;
            this.view.showOffline('stats');
            this.lastSeq = -1;
            const statsBtn = document.getElementById('statsBtn');
            if (statsBtn) statsBtn.classList.add('hidden');
        }
        this.updateConnBadge(!!ok);
    }

    onMessage(data) {
        if (!data || typeof data.seq !== 'number') return;
        if (data.seq <= this.lastSeq) return;
        this.lastSeq = data.seq;
        this.lastMessageAt = Date.now();
        this.lastData = data;

        if (data.phase === 'offline') {
            this.view.showOffline('controller');
        } else {
            this.view.update(data);
        }
        this.claimView.update(data);
        this.statsView.update(data);
        this.statsDetail.update(data);
        this.updateConnBadge(true);
    }

    checkStale() {
        if (!this.lastMessageAt) return;
        const age = Date.now() - this.lastMessageAt;
        if (age > (MOISE_CONFIG.staleTimeoutMs || 3000)) {
            this.view.showOffline(this.ws.isConnected ? 'controller' : 'stats');
            this.lastSeq = -1;
            this.lastMessageAt = 0;
            this.lastData = null;
            const statsBtn = document.getElementById('statsBtn');
            if (statsBtn) statsBtn.classList.add('hidden');
            this.updateConnBadge(this.ws.isConnected);
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.moiseApp = new MoiseApp();
    window.moiseApp.start();
});
