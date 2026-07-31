class ConfigView {
    constructor(app) {
        this.app = app;
        this.configCache = null;
        this.discovery = [];
    }

    bind() {
        document.getElementById('btnDiscover').addEventListener('click', () => this.discover());
        document.getElementById('btnSaveConfig').addEventListener('click', () => this.saveConfig());
        document.getElementById('btnSetPrice').addEventListener('click', () => this.setPrice());
        document.getElementById('btnCreditCustom').addEventListener('click', () => {
            const euro = Number(document.getElementById('creditCustom').value);
            if (euro > 0) this.addCredit(Math.round(euro * 100));
        });
        document.querySelectorAll('[data-credit]').forEach((btn) => {
            btn.addEventListener('click', () => this.addCredit(Number(btn.dataset.credit)));
        });
        document.getElementById('btnResetCounters').addEventListener('click', () => {
            if (confirm('Wirklich alle Zähler zurücksetzen?')) this.resetCounters();
        });
    }

    async onShow() {
        await this.loadConfig();
        this.renderControllers(this.app.lastData);
        this.renderCash(this.app.lastData);
    }

    update(data) {
        this.renderControllers(data);
        this.renderCash(data);
    }

    async loadConfig() {
        const res = await this.app.request('get_config');
        if (res && res.ok) {
            this.configCache = res.data;
            this.renderLaneMapping();
            const price = (res.data.game && res.data.game.price_cent) || 100;
            document.getElementById('priceInput').value = (price / 100).toFixed(2);
        }
    }

    renderCash(data) {
        if (!data) return;
        const el = document.getElementById('cashStats');
        const price = data.game_price_cent || 100;
        const gamesLeft = price > 0 ? Math.floor((data.guthaben || 0) / price) : 0;
        el.innerHTML = `
            <div>Einzahlungen: <strong>${DataFormatter.formatCurrency(data.einzahlungen)}</strong></div>
            <div>Service: <strong>${DataFormatter.formatCurrency(data.service_gutschriften)}</strong></div>
            <div>Ausgaben: <strong>${DataFormatter.formatCurrency(data.ausgaben)}</strong></div>
            <div>Guthaben: <strong>${DataFormatter.formatCurrency(data.guthaben)}</strong></div>
            <div>Spiele: <strong>${data.gespielte_spiele || 0}</strong></div>
            <div>Preis: <strong>${DataFormatter.formatCurrency(price)}</strong></div>
        `;
        document.getElementById('gamesEstimate').textContent = `Noch ca. ${gamesLeft} Spiele mit aktuellem Guthaben`;
        document.getElementById('priceInput').value = (price / 100).toFixed(2);
    }

    renderControllers(data) {
        const list = document.getElementById('controllerList');
        const controllers = (data && data.controllers) || [];
        if (!controllers.length) {
            list.innerHTML = '<p class="muted">Keine gebundenen Controller</p>';
            return;
        }
        list.innerHTML = controllers.map((c) => `
            <div class="controller-card">
                <div><strong>#${c.id}</strong> ${c.name || ''} — <code>${c.port || 'kein Port'}</code></div>
                <div class="muted">State: ${c.state} | Mode: ${c.firmware_mode || '-'} | Lanes: ${JSON.stringify(c.lanes)}</div>
                <div class="panel-actions">
                    <button type="button" data-identify="${c.id}">Identify</button>
                </div>
            </div>
        `).join('');
        list.querySelectorAll('[data-identify]').forEach((btn) => {
            btn.addEventListener('click', () => {
                this.app.request('identify_controller', { controller_id: Number(btn.dataset.identify) });
            });
        });
    }

    renderLaneMapping() {
        const el = document.getElementById('laneMapping');
        if (!this.configCache) {
            el.innerHTML = '<p class="muted">Keine Config</p>';
            return;
        }
        const controllers = this.configCache.controllers || [];
        el.innerHTML = controllers.map((c, idx) => {
            const lanes = c.lanes || {};
            const rows = Object.keys(lanes).map((local) => `
                <div class="form-row">
                    <span>Ctrl ${c.id} lokal ${local} →</span>
                    <input type="number" data-cmap="${idx}:${local}" value="${lanes[local]}" min="1">
                </div>
            `).join('');
            return `<div class="controller-card"><strong>${c.name || c.id}</strong>${rows}</div>`;
        }).join('');
    }

    async discover() {
        const res = await this.app.request('discover_controllers');
        const el = document.getElementById('discoveryList');
        if (!res || !res.ok) {
            el.innerHTML = `<p class="error-text">${(res && res.error) || 'Discover fehlgeschlagen'}</p>`;
            return;
        }
        this.discovery = res.data || [];
        el.innerHTML = '<h3>Gefunden</h3>' + this.discovery.map((d, i) => `
            <div class="discovery-card" data-idx="${i}">
                <code>${d.port}</code> — id=${d.id} lanes=${d.lanes != null ? d.lanes : '?'}
                <div class="form-row">
                    <input type="number" class="set-id" placeholder="ID setzen" min="0">
                    <button type="button" class="btn-set-id">ID schreiben</button>
                    <input type="number" class="set-lanes" placeholder="Lanes 1|2" min="1" max="2">
                    <button type="button" class="btn-set-lanes">Lanes schreiben</button>
                </div>
            </div>
        `).join('');

        el.querySelectorAll('.discovery-card').forEach((card) => {
            const idx = Number(card.dataset.idx);
            const port = this.discovery[idx].port;
            card.querySelector('.btn-set-id').addEventListener('click', async () => {
                const id = Number(card.querySelector('.set-id').value);
                await this.app.request('set_controller_id', { port, id });
                this.discover();
            });
            card.querySelector('.btn-set-lanes').addEventListener('click', async () => {
                const lanes = Number(card.querySelector('.set-lanes').value);
                await this.app.request('set_controller_lanes', { port, lanes });
                this.discover();
            });
        });
    }

    async saveConfig() {
        if (!this.configCache) await this.loadConfig();
        if (!this.configCache) return;
        document.querySelectorAll('[data-cmap]').forEach((input) => {
            const [idx, local] = input.dataset.cmap.split(':');
            this.configCache.controllers[Number(idx)].lanes[local] = Number(input.value);
        });
        const res = await this.app.request('set_config', { config: this.configCache });
        if (res && res.ok) alert('Config gespeichert. Brain ggf. neu starten für volles Remapping.');
        else alert((res && res.error) || 'Speichern fehlgeschlagen');
    }

    async addCredit(cent) {
        const res = await this.app.request('add_credit', { cent });
        if (!(res && res.ok)) alert((res && res.error) || 'Fehlgeschlagen');
    }

    async setPrice() {
        const euro = Number(document.getElementById('priceInput').value);
        const cent = Math.round(euro * 100);
        const res = await this.app.request('set_price', { cent });
        if (!(res && res.ok)) alert((res && res.error) || 'Fehlgeschlagen');
    }

    async resetCounters() {
        const res = await this.app.request('reset_counters');
        if (!(res && res.ok)) alert((res && res.error) || 'Fehlgeschlagen');
    }
}
