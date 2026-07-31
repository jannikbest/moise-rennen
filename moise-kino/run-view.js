class RunView {
    constructor(animation) {
        this.animation = animation;
        this.lastGameState = null;
        this.currentMausNamen = {};
        this.lanesBuilt = false;
    }

    ensureLanes(data) {
        const lanes = data.lanes && data.lanes.length ? data.lanes : this._fallbackLanes(data);
        if (!this.lanesBuilt && lanes.length) {
            this.animation.rebuildTracks(lanes);
            this.animation.rebuildNameBar(lanes);
            this.lanesBuilt = true;
            window.addEventListener('resize', () => this.animation.updatePositionsForResize());
        }
    }

    _fallbackLanes(data) {
        const pts = data.maus_punktzahlen || {};
        const ids = Object.keys(pts).map(Number).sort((a, b) => a - b);
        if (!ids.length) {
            return [1, 2, 3, 4, 5].map((id) => ({ id, name: String(id) }));
        }
        return ids.map((id) => ({ id, name: String(id) }));
    }

    update(data) {
        this.ensureLanes(data);

        const guthaben = document.getElementById('guthabenValue');
        const spiele = document.getElementById('spieleValue');
        const price = document.getElementById('priceValue');
        if (guthaben) guthaben.textContent = DataFormatter.formatCurrency(data.guthaben);
        if (spiele) spiele.textContent = data.gespielte_spiele != null ? data.gespielte_spiele : '-';
        if (price) price.textContent = DataFormatter.formatCurrency(data.game_price_cent || 100);

        if (data.maus_punktzahlen) {
            this.animation.updateMausPosition(data.maus_punktzahlen);
        }

        if (data.maus_namen) {
            this.currentMausNamen = data.maus_namen;
            Object.keys(data.maus_namen).forEach((id) => {
                const box = document.getElementById(`maus${id}-name-container`);
                const val = document.getElementById(`maus${id}NameValue`);
                if (box && val && data.maus_namen[id]) {
                    box.classList.remove('hidden');
                    val.textContent = data.maus_namen[id];
                }
            });
        }

        if (data.game_state && data.game_state !== this.lastGameState) {
            this.lastGameState = data.game_state;
            this._setStatus(data.game_state);
        }

        if (data.gewonnen && data.game_state === 'finished') {
            this._updateWinner(data.gewonnen);
        }
    }

    _setStatus(status) {
        const el = document.getElementById('moiseStatusValue');
        const s = String(status).toLowerCase();
        if (s === 'ready') {
            if (el) el.textContent = 'Moise bereit';
            this._show('ready');
        } else if (s === 'racing') {
            if (el) el.textContent = 'Moise unterwegs';
            this._show('racing');
            this.animation.resetAllMausPositions();
        } else if (s === 'finished') {
            if (el) el.textContent = 'Maus im Ziel!';
            this._show('finished');
        } else if (s === 'wait_for_ready' || s === 'wait_for_controller_response') {
            if (el) el.textContent = 'Moise laufen zurück';
            this._show('ready');
        } else if (s === 'error' || s === 'paused') {
            if (el) el.textContent = status;
            this._show('ready');
        } else {
            if (el) el.textContent = status;
            this._show('racing');
        }
    }

    _show(which) {
        ['ready', 'racing', 'finished'].forEach((name) => {
            const el = document.getElementById(`${name}-view`);
            if (el) el.classList.toggle('hidden', name !== which);
        });
    }

    _updateWinner(gewonnen) {
        const maus = document.getElementById('winnerMaus');
        const time = document.getElementById('winnerTime');
        const playerBox = document.getElementById('winnerPlayer');
        const playerName = document.getElementById('winnerPlayerName');
        if (maus) maus.textContent = gewonnen.id || '-';
        if (time) time.textContent = gewonnen.Zeit ? `${gewonnen.Zeit} ms` : '-';
        if (playerBox && playerName) {
            const idMatch = String(gewonnen.id || '').match(/(\d+)/);
            const id = idMatch ? idMatch[1] : null;
            const name = id && this.currentMausNamen ? this.currentMausNamen[id] : null;
            if (name) {
                playerName.textContent = name;
                playerBox.classList.remove('hidden');
            } else {
                playerBox.classList.add('hidden');
            }
        }
    }
}
