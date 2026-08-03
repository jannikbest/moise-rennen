class StatsView {
    constructor() {
        this.cards = [];
        this.index = 0;
        this._timer = null;
        this._hosts = Array.from(document.querySelectorAll('[data-stats-host]'));
    }

    update(data) {
        const idle = !!(data && data.phase === 'idle');
        this._hosts.forEach((el) => el.classList.toggle('hidden', !idle));

        const cards = (data && data.stats && data.stats.cards) || [];
        const key = JSON.stringify(cards.map((c) => [c.id, (c.lines || []).length, c.kind]));
        if (key !== this._key) {
            this._key = key;
            this.cards = cards;
            this.index = 0;
            this.render();
            this._restartTimer();
        }
    }

    _restartTimer() {
        clearInterval(this._timer);
        if (this.cards.length <= 1) return;
        const ms = MOISE_CONFIG.statsRotateMs || 8000;
        this._timer = setInterval(() => {
            this.index = (this.index + 1) % this.cards.length;
            this.render();
        }, ms);
    }

    render() {
        const card = this.cards[this.index];
        this._hosts.forEach((host) => {
            if (!card) {
                host.innerHTML = '<div class="stat-card"><h2>No stats yet</h2><p>Play a few races!</p></div>';
                return;
            }
            const lines = (card.lines || [])
                .map((l) => `<div class="stat-line">${this._esc(l)}</div>`)
                .join('');
            const chart = card.kind === 'chart' ? this._chartSvg(card.hours || []) : '';
            const listClass = (card.lines || []).length > 5 ? ' dense' : '';
            host.innerHTML =
                `<div class="stat-card${listClass}" data-card="${this._esc(card.id)}">` +
                `<div class="stat-index">${this.index + 1}/${this.cards.length}</div>` +
                `<h2>${this._esc(card.title)}</h2>` +
                chart +
                lines +
                `</div>`;
        });
    }

    _chartSvg(hours) {
        const vals = [];
        for (let h = 0; h < 24; h++) vals.push(Number(hours[h]) || 0);
        const max = Math.max(1, ...vals);
        const w = 320;
        const h = 120;
        const pad = 8;
        const barW = (w - pad * 2) / 24;
        let rects = '';
        vals.forEach((v, i) => {
            const bh = Math.max(v > 0 ? 4 : 1, (v / max) * (h - 28));
            const x = pad + i * barW;
            const y = h - 18 - bh;
            const active = v === max && v > 0;
            rects +=
                `<rect x="${x + 1}" y="${y}" width="${Math.max(2, barW - 2)}" height="${bh}" ` +
                `rx="2" fill="${active ? '#f1c40f' : 'rgba(255,255,255,0.55)'}"/>`;
        });
        // hour labels every 6h
        let labels = '';
        [0, 6, 12, 18].forEach((i) => {
            labels +=
                `<text x="${pad + i * barW + barW / 2}" y="${h - 4}" text-anchor="middle" ` +
                `fill="rgba(255,255,255,0.7)" font-size="10">${String(i).padStart(2, '0')}</text>`;
        });
        return (
            `<svg class="stat-chart" viewBox="0 0 ${w} ${h}" width="100%" height="120" aria-hidden="true">` +
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
