class KinoView {
    constructor(animation) {
        this.animation = animation;
        this.lastState = null;
        this.lanesBuilt = false;
        this.laneKey = '';
        this._resizeBound = false;
        this._lastLanes = [];
        this._cueTimer = null;
        this._countingDown = false;
        this._winHold = false;
        this._pendingWin = null;
        this._celebrateTimer = null;
    }

    update(data) {
        if (!data || !data.state) return;

        if (data.maxPoints != null) {
            this.animation.setMaxPoints(data.maxPoints);
        }

        this.ensureLanes(data.lanes || []);
        this._lastLanes = data.lanes || [];

        if (data.state !== this.lastState) {
            const prev = this.lastState;
            this.lastState = data.state;

            if (data.state === 'race') {
                this.cancelWinHold();
                this.showScreen('race');
                this.animation.resetAllMausPositions();
                this.startCountdown();
            } else if (data.state === 'win' && prev === 'race') {
                this.clearCountdown();
                this.startWinCelebration(data);
            } else if (data.state === 'win') {
                this.cancelWinHold();
                this.showScreen('win');
                this.updateWinner(data);
            } else {
                this.clearCountdown();
                this.cancelWinHold();
                this.showScreen(data.state);
            }
        }

        if (data.state === 'race') {
            if (!this._countingDown) {
                this.animation.updateMausPosition(data.lanes || []);
                this.updateClock(data.durationMs);
            } else {
                this.animation.resetAllMausPositions();
                this.updateClock(0);
            }
            this.updateLabels(data.lanes || []);
        } else if (data.state === 'win') {
            this.updateLabels(data.lanes || []);
            if (this._winHold) {
                this._pendingWin = data;
                this.highlightWinnerLane(data);
            } else {
                this.updateWinner(data);
            }
        }
    }

    ensureLanes(lanes) {
        const key = lanes.map((l) => l.id).join(',');
        if (this.lanesBuilt && key === this.laneKey) return;
        if (!lanes.length) return;

        this.animation.rebuildTracks(lanes);
        this.lanesBuilt = true;
        this.laneKey = key;

        if (!this._resizeBound) {
            this._resizeBound = true;
            window.addEventListener('resize', () => this.animation.updatePositionsForResize());
        }
    }

    updateLabels(lanes) {
        const defaults = (typeof MOISE_CONFIG !== 'undefined' && MOISE_CONFIG.laneLabels) || {};
        (lanes || []).forEach((lane) => {
            const el = document.getElementById(`laneLabel${lane.id}`);
            if (!el) return;
            el.textContent = lane.label || defaults[lane.id] || `Mouse ${lane.id}`;
        });
    }

    updateClock(ms) {
        const el = document.getElementById('raceClock');
        if (!el) return;
        const sec = Math.max(0, Number(ms) || 0) / 1000;
        el.textContent = `${sec.toFixed(1)}s`;
    }

    showScreen(state) {
        const known = ['offline', 'config', 'homing', 'ready', 'race', 'win', 'error'];
        const target = known.includes(state) ? state : 'offline';
        known.forEach((name) => {
            const el = document.getElementById(`screen-${name}`);
            if (el) el.classList.toggle('hidden', name !== target);
        });
    }

    showOffline() {
        this.clearCountdown();
        this.cancelWinHold();
        this.lastState = 'offline';
        this.showScreen('offline');
    }

    startCountdown() {
        this.clearCountdown();
        this._countingDown = true;
        const cue = document.getElementById('raceCue');
        const text = document.getElementById('raceCueText');
        if (!cue || !text) {
            this._countingDown = false;
            return;
        }

        const steps = [
            { label: 'Get ready', cls: 'ready', ms: 900 },
            { label: '3', cls: 'count', ms: 800 },
            { label: '2', cls: 'count', ms: 800 },
            { label: '1', cls: 'count', ms: 800 },
            { label: '🏁', cls: 'go', ms: 900 }
        ];

        cue.classList.remove('hidden');
        this.animation.resetAllMausPositions();
        this.updateClock(0);
        let i = 0;

        const tick = () => {
            if (i >= steps.length) {
                this.clearCountdown();
                return;
            }
            const step = steps[i++];
            text.className = `race-cue-text ${step.cls}`;
            text.textContent = step.label;
            void text.offsetWidth;
            text.classList.add('pop');
            this._cueTimer = setTimeout(tick, step.ms);
        };
        tick();
    }

    clearCountdown() {
        clearTimeout(this._cueTimer);
        this._cueTimer = null;
        this._countingDown = false;
        const cue = document.getElementById('raceCue');
        if (cue) cue.classList.add('hidden');
    }

    startWinCelebration(data) {
        this.cancelWinHold();
        this._winHold = true;
        this._pendingWin = data;
        this.showScreen('race');
        const winnerId = this.winnerIdOf(data);
        this.animation.finishPose(data.lanes || this._lastLanes || [], winnerId);
        this.highlightWinnerLane(data);

        this._celebrateTimer = setTimeout(() => {
            this._winHold = false;
            this.clearWinnerHighlight();
            this.showScreen('win');
            if (this._pendingWin) this.updateWinner(this._pendingWin);
            this._pendingWin = null;
            this._celebrateTimer = null;
        }, 5000);
    }

    cancelWinHold() {
        clearTimeout(this._celebrateTimer);
        this._celebrateTimer = null;
        this._winHold = false;
        this._pendingWin = null;
        this.clearWinnerHighlight();
    }

    winnerIdOf(data) {
        const result = data && data.lastResult;
        return (result && result.winnerLane) || (data && data.winner) || 0;
    }

    highlightWinnerLane(data) {
        const winnerId = this.winnerIdOf(data);
        document.querySelectorAll('.lane-row').forEach((row) => {
            const won = String(row.dataset.maus) === String(winnerId);
            row.classList.toggle('lane-winner', won);
            let badge = row.querySelector('.lane-win-badge');
            if (won) {
                if (!badge) {
                    badge = document.createElement('div');
                    badge.className = 'lane-win-badge';
                    badge.innerHTML =
                        '<img class="lane-win-star" src="icon-star.png" alt="" draggable="false">' +
                        '<img class="lane-win-cup" src="icon-trophy.png" alt="" draggable="false">';
                    row.appendChild(badge);
                }
            } else if (badge) {
                badge.remove();
            }
        });
    }

    clearWinnerHighlight() {
        document.querySelectorAll('.lane-row.lane-winner').forEach((row) => {
            row.classList.remove('lane-winner');
            const badge = row.querySelector('.lane-win-badge');
            if (badge) badge.remove();
        });
    }

    updateWinner(data) {
        const screen = document.getElementById('screen-win');
        const el = document.getElementById('winnerLabel');
        const timeEl = document.getElementById('winnerTime');
        const result = data.lastResult || null;
        const durationMs = (result && result.durationMs) || data.durationMs;
        const winnerId = (result && result.winnerLane) || data.winner;

        if (screen) {
            if (winnerId) screen.dataset.winner = String(winnerId);
            else delete screen.dataset.winner;
        }

        if (timeEl) {
            const sec = Math.max(0, Number(durationMs) || 0) / 1000;
            timeEl.textContent = durationMs ? `${sec.toFixed(1)} seconds` : '';
        }

        if (!el) return;
        if (!winnerId && !(result && result.winner)) {
            el.textContent = 'No winner';
            return;
        }

        if (result && result.winner) {
            el.textContent = result.winner;
            return;
        }

        const defaults = (typeof MOISE_CONFIG !== 'undefined' && MOISE_CONFIG.laneLabels) || {};
        const lane = (data.lanes || []).find((l) => Number(l.id) === Number(winnerId));
        el.textContent = (lane && lane.label) || defaults[winnerId] || `Mouse ${winnerId}`;
    }
}
