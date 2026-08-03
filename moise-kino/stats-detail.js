class StatsDetail {
    constructor() {
        this.open = false;
        this._idleTimer = null;
        this._stats = null;

        this.btn = document.getElementById('statsBtn');
        this.overlay = document.getElementById('statsDetail');
        this.body = document.getElementById('statsDetailBody');
        this.closeBtn = document.getElementById('statsDetailClose');

        if (this.btn) {
            this.btn.addEventListener('click', () => this.toggle());
        }
        if (this.closeBtn) {
            this.closeBtn.addEventListener('click', () => this.hide());
        }
        if (this.overlay) {
            this.overlay.addEventListener('click', (e) => {
                if (e.target === this.overlay) this.hide();
            });
            this.overlay.addEventListener('pointerdown', () => this.bumpIdle());
        }
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.open) this.hide();
        });
    }

    update(data) {
        const idle = !!(data && data.phase === 'idle');
        if (this.btn) this.btn.classList.toggle('hidden', !idle);
        if (data && data.stats) this._stats = data.stats;
        if (!idle && this.open) this.hide();
        if (this.open) this.render();
    }

    toggle() {
        if (this.open) this.hide();
        else this.show();
    }

    show() {
        this.open = true;
        if (this.overlay) this.overlay.classList.remove('hidden');
        this.render();
        this.bumpIdle();
    }

    hide() {
        this.open = false;
        if (this.overlay) this.overlay.classList.add('hidden');
        clearTimeout(this._idleTimer);
    }

    bumpIdle() {
        clearTimeout(this._idleTimer);
        const ms = (typeof MOISE_CONFIG !== 'undefined' && MOISE_CONFIG.statsDetailIdleMs) || 60000;
        this._idleTimer = setTimeout(() => this.hide(), ms);
    }

    render() {
        if (!this.body) return;
        const sections = (this._stats && this._stats.detail) || [];
        if (!sections.length) {
            this.body.innerHTML = '<p class="stats-detail-empty">No stats yet — play a few races!</p>';
            return;
        }
        this.body.innerHTML = sections.map((sec) => this._section(sec)).join('');
    }

    _section(sec) {
        const title = this._esc(sec.title || '');
        if (sec.kind === 'chart') {
            return (
                `<section class="stats-detail-section">` +
                `<h3>${title}</h3>` +
                this._chartSvg(sec.hours || []) +
                `</section>`
            );
        }
        const rows = (sec.rows || [])
            .map((r) => {
                const rank = r.rank != null ? `<span class="sd-rank">${r.rank}.</span>` : '';
                return (
                    `<div class="sd-row">` +
                    `${rank}<span class="sd-name">${this._esc(r.name || '')}</span>` +
                    `<span class="sd-value">${this._esc(r.value || '')}</span>` +
                    `</div>`
                );
            })
            .join('');
        return `<section class="stats-detail-section"><h3>${title}</h3>${rows}</section>`;
    }

    _chartSvg(hours) {
        const vals = [];
        for (let h = 0; h < 24; h++) vals.push(Number(hours[h]) || 0);
        const max = Math.max(1, ...vals);
        const w = 640;
        const h = 160;
        const pad = 10;
        const barW = (w - pad * 2) / 24;
        let rects = '';
        vals.forEach((v, i) => {
            const bh = Math.max(v > 0 ? 4 : 1, (v / max) * (h - 36));
            const x = pad + i * barW;
            const y = h - 24 - bh;
            const active = v === max && v > 0;
            rects +=
                `<rect x="${x + 1}" y="${y}" width="${Math.max(2, barW - 2)}" height="${bh}" ` +
                `rx="2" fill="${active ? '#f1c40f' : 'rgba(255,255,255,0.55)'}"/>`;
        });
        let labels = '';
        [0, 6, 12, 18].forEach((i) => {
            labels +=
                `<text x="${pad + i * barW + barW / 2}" y="${h - 6}" text-anchor="middle" ` +
                `fill="rgba(255,255,255,0.7)" font-size="12">${String(i).padStart(2, '0')}</text>`;
        });
        return (
            `<svg class="stat-chart" viewBox="0 0 ${w} ${h}" width="100%" height="160" aria-hidden="true">` +
            rects +
            labels +
            `</svg>`
        );
    }

    _esc(s) {
        return String(s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }
}
