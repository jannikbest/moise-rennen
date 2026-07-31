class MoiseApp {
    constructor() {
        this.token = sessionStorage.getItem('moise_token') || null;
        this.view = 'run';
        this.pendingMode = null;
        this.lastData = null;
        this.lastActivity = Date.now();
        this.animation = new MausAnimation();
        this.runView = new RunView(this.animation);
        this.configView = new ConfigView(this);
        this.debugView = new DebugView(this);
        this.ws = new WebSocketClient(
            (data) => this.onMessage(data),
            (ok) => this.onStatus(ok)
        );
    }

    start() {
        this.bindTopbar();
        this.bindPasswordModal();
        this.configView.bind();
        this.debugView.bind();
        this.ws.connect(MOISE_CONFIG.websocket.url);
        this.showView('run');
        this.trackActivity();
        setInterval(() => this.checkIdle(), 5000);
    }

    trackActivity() {
        ['click', 'keydown', 'touchstart', 'mousemove'].forEach((evt) => {
            document.addEventListener(evt, () => {
                this.lastActivity = Date.now();
            }, { passive: true });
        });
    }

    checkIdle() {
        if (this.view === 'run') return;
        const idle = Date.now() - this.lastActivity;
        if (idle > (MOISE_CONFIG.ui.idleReturnMs || 300000)) {
            this.switchMode('run');
        }
    }

    bindTopbar() {
        document.querySelectorAll('.mode-btn').forEach((btn) => {
            btn.addEventListener('click', () => {
                const mode = btn.dataset.mode;
                this.switchMode(mode);
            });
        });
    }

    bindPasswordModal() {
        document.getElementById('passwordCancel').addEventListener('click', () => {
            document.getElementById('passwordModal').classList.add('hidden');
            this.pendingMode = null;
        });
        document.getElementById('passwordSubmit').addEventListener('click', () => this.submitPassword());
        document.getElementById('passwordInput').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') this.submitPassword();
        });
    }

    async submitPassword() {
        const password = document.getElementById('passwordInput').value;
        try {
            const res = await this.ws.request('login', { password });
            if (res && res.ok && res.data && res.data.token) {
                this.token = res.data.token;
                sessionStorage.setItem('moise_token', this.token);
                document.getElementById('passwordModal').classList.add('hidden');
                document.getElementById('passwordError').classList.add('hidden');
                document.getElementById('passwordInput').value = '';
                if (this.pendingMode) {
                    const mode = this.pendingMode;
                    this.pendingMode = null;
                    await this.enterProtected(mode);
                }
            } else {
                document.getElementById('passwordError').classList.remove('hidden');
            }
        } catch (e) {
            document.getElementById('passwordError').classList.remove('hidden');
        }
    }

    async switchMode(mode) {
        if (mode === 'run') {
            await this.request('set_mode', { mode: 'run' }).catch(() => {});
            this.showView('run');
            return;
        }
        if (!this.token) {
            this.pendingMode = mode;
            document.getElementById('passwordModal').classList.remove('hidden');
            document.getElementById('passwordInput').focus();
            return;
        }
        await this.enterProtected(mode);
    }

    async enterProtected(mode) {
        const res = await this.request('set_mode', { mode }).catch(() => null);
        if (res && res.ok === false && res.error === 'unauthorized') {
            this.token = null;
            sessionStorage.removeItem('moise_token');
            this.pendingMode = mode;
            document.getElementById('passwordModal').classList.remove('hidden');
            return;
        }
        this.showView(mode);
    }

    showView(mode) {
        const prev = this.view;
        this.view = mode;
        document.querySelectorAll('.mode-btn').forEach((btn) => {
            btn.classList.toggle('active', btn.dataset.mode === mode);
        });
        document.getElementById('view-run').classList.toggle('hidden', mode !== 'run');
        document.getElementById('view-config').classList.toggle('hidden', mode !== 'config');
        document.getElementById('view-debug').classList.toggle('hidden', mode !== 'debug');

        if (prev === 'debug' && mode !== 'debug') this.debugView.onHide();
        if (mode === 'config') this.configView.onShow();
        if (mode === 'debug') this.debugView.onShow();
    }

    request(action, payload) {
        return this.ws.request(action, payload, this.token);
    }

    onStatus(ok) {
        const el = document.getElementById('connectionStatus');
        if (el) el.classList.toggle('connected', !!ok);
        if (!ok) {
            const status = document.getElementById('moiseStatusValue');
            if (status) status.textContent = 'Keine Verbindung';
        }
    }

    onMessage(data) {
        if (data && data.type === 'serial_log' && data.entry) {
            this.debugView.onSerialEntry(data.entry);
            return;
        }
        this.lastData = data;
        this.updateErrorBanner(data);
        const modeLabel = document.getElementById('systemModeLabel');
        if (modeLabel && data.system_mode) modeLabel.textContent = data.system_mode;

        if (this.view === 'run') this.runView.update(data);
        if (this.view === 'config') this.configView.update(data);
        if (this.view === 'debug') this.debugView.update(data);
        // Always keep run animation data warm
        if (this.view !== 'run') this.runView.update(data);
    }

    updateErrorBanner(data) {
        const banner = document.getElementById('errorBanner');
        const errors = (data && data.errors) || [];
        if (!errors.length) {
            banner.classList.add('hidden');
            banner.textContent = '';
            return;
        }
        banner.classList.remove('hidden');
        banner.textContent = errors.map((e) => e.message).join(' | ');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.moiseApp = new MoiseApp();
    window.moiseApp.start();
});
