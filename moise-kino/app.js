class MoiseApp {
    constructor() {
        this.lastSeq = -1;
        this.lastMessageAt = 0;
        this.animation = new MausAnimation();
        this.view = new KinoView(this.animation);
        this.claimView = new ClaimView(this);
        this.statsView = new StatsView();
        this.statsDetail = new StatsDetail();
        this.ws = new WebSocketClient(
            (data) => this.onMessage(data),
            (ok) => this.onStatus(ok)
        );
        this._testMode = !!MOISE_CONFIG.testMode;
    }

    start() {
        this.ws.connect(MOISE_CONFIG.websocket.url);
        this.view.showOffline();
        this.bindSimStart();
        setInterval(() => this.checkStale(), 500);
    }

    bindSimStart() {
        const btn = document.getElementById('simStartBtn');
        if (!btn) return;
        btn.addEventListener('click', async () => {
            btn.disabled = true;
            try {
                await this.request('sim_start', {});
            } catch (e) {
                console.error('sim_start', e);
            }
            setTimeout(() => { btn.disabled = false; }, 1500);
        });
        btn.title = 'Start a simulated race';
        btn.textContent = '▶ Start race';
    }

    updateSimButton(data) {
        const btn = document.getElementById('simStartBtn');
        if (!btn) return;
        const enabled = this._testMode || !!(data && data.testMode);
        this._testMode = enabled;
        const idle = !!data && data.phase === 'idle';
        btn.classList.toggle('hidden', !(enabled && idle));
    }

    request(action, payload) {
        return this.ws.request(action, payload);
    }

    onStatus(ok) {
        const dot = document.getElementById('connDot');
        if (dot) dot.classList.toggle('connected', !!ok);
        if (!ok) {
            this.view.showOffline();
            this.lastSeq = -1;
            const btn = document.getElementById('simStartBtn');
            if (btn) btn.classList.add('hidden');
            const statsBtn = document.getElementById('statsBtn');
            if (statsBtn) statsBtn.classList.add('hidden');
        }
    }

    onMessage(data) {
        if (!data || typeof data.seq !== 'number') return;
        if (data.seq <= this.lastSeq) return;
        this.lastSeq = data.seq;
        this.lastMessageAt = Date.now();

        if (data.phase === 'offline') {
            this.view.showOffline();
        } else {
            this.view.update(data);
        }
        this.claimView.update(data);
        this.statsView.update(data);
        this.statsDetail.update(data);
        this.updateSimButton(data);
    }

    checkStale() {
        if (!this.lastMessageAt) return;
        const age = Date.now() - this.lastMessageAt;
        if (age > (MOISE_CONFIG.staleTimeoutMs || 3000)) {
            this.view.showOffline();
            this.lastSeq = -1;
            this.lastMessageAt = 0;
            const btn = document.getElementById('simStartBtn');
            if (btn) btn.classList.add('hidden');
            const statsBtn = document.getElementById('statsBtn');
            if (statsBtn) statsBtn.classList.add('hidden');
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.moiseApp = new MoiseApp();
    window.moiseApp.start();
});
