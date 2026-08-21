class MausAnimation {
    constructor() {
        this.padding = 36;
        this.availableWidth = 0;
        this.maxPoints = (typeof MOISE_CONFIG !== 'undefined' && MOISE_CONFIG.maxPoints) || 15;
        this._lastPoints = Object.create(null);
    }

    setMaxPoints(n) {
        const next = Math.max(1, Number(n) || 15);
        if (next === this.maxPoints) return;
        this.maxPoints = next;
        this._lastPoints = Object.create(null);
    }

    rebuildTracks(lanes) {
        const container = document.getElementById('mausTracks');
        if (!container) return;
        container.innerHTML = '';
        this._lastPoints = Object.create(null);
        const labels = (typeof MOISE_CONFIG !== 'undefined' && MOISE_CONFIG.laneLabels) || {};
        const icon = (typeof MOISE_CONFIG !== 'undefined' && MOISE_CONFIG.mausIcon) || 'maus.png';

        (lanes || []).forEach((lane) => {
            const id = lane.id;
            const row = document.createElement('div');
            row.className = 'lane-row';
            row.dataset.maus = String(id);

            const label = document.createElement('div');
            label.className = 'lane-label';
            label.id = `laneLabel${id}`;
            label.textContent = lane.label || labels[id] || `Mouse ${id}`;

            const track = document.createElement('div');
            track.className = 'maus-track';
            track.dataset.maus = String(id);

            const marks = document.createElement('div');
            marks.className = 'track-marks';
            for (let i = 0; i <= this.maxPoints; i++) {
                const m = document.createElement('div');
                m.className = 'track-mark';
                m.dataset.mark = String(i);
                marks.appendChild(m);
            }

            const indicator = document.createElement('div');
            indicator.className = 'maus-indicator';
            indicator.id = `mausIndicator${id}`;
            indicator.innerHTML =
                `<img class="maus-icon" src="${icon}" alt="" draggable="false">` +
                `<span class="maus-points" id="mausPoints${id}">0</span>`;

            track.appendChild(marks);
            track.appendChild(indicator);
            row.appendChild(label);
            row.appendChild(track);
            container.appendChild(row);
        });
        this.measure();
    }

    measure() {
        const track = document.querySelector('.maus-track');
        if (track) {
            this.availableWidth = Math.max(0, track.offsetWidth - this.padding * 2);
        }
    }

    setMausPosition(mausId, points, { jump = false, force = false } = {}) {
        const indicator = document.getElementById(`mausIndicator${mausId}`);
        const pointsEl = document.getElementById(`mausPoints${mausId}`);
        if (!indicator || !pointsEl) return;
        if (!this.availableWidth) this.measure();
        const clamped = Math.max(0, Math.min(this.maxPoints, Number(points) || 0));
        const key = String(mausId);
        if (!force && !jump && this._lastPoints[key] === clamped) return;
        this._lastPoints[key] = clamped;
        const translateX = (clamped / this.maxPoints) * this.availableWidth;
        indicator.style.transform = `translateY(-50%) translateX(${-translateX}px)`;
        pointsEl.textContent = String(Number(points) || 0);
        this.updateTrackMarks(mausId, clamped);
        if (jump) {
            indicator.classList.remove('maus-jump');
            void indicator.offsetWidth;
            indicator.classList.add('maus-jump');
        }
    }

    updateMausPosition(lanes) {
        (lanes || []).forEach((lane) => {
            this.setMausPosition(lane.id, lane.points);
        });
    }

    /** Freeze losers where they are; snap winner to the finish line with a jump. */
    finishPose(lanes, winnerId) {
        const max = this.maxPoints;
        (lanes || []).forEach((lane) => {
            const won = Number(lane.id) === Number(winnerId);
            this.setMausPosition(lane.id, won ? max : lane.points, { jump: won });
        });
    }

    updateTrackMarks(mausId, points) {
        const track = document.querySelector(`.maus-track[data-maus="${mausId}"]`);
        if (!track) return;
        track.querySelectorAll('.track-mark').forEach((mark) => {
            const n = Number(mark.dataset.mark);
            mark.classList.toggle('active', n === points);
            mark.classList.toggle('passed', n < points);
        });
    }

    resetAllMausPositions() {
        document.querySelectorAll('.maus-indicator').forEach((el) => {
            const id = el.id.replace('mausIndicator', '');
            this.setMausPosition(id, 0, { force: true });
        });
    }

    updatePositionsForResize() {
        this.measure();
        Object.keys(this._lastPoints).forEach((id) => {
            this.setMausPosition(id, this._lastPoints[id], { force: true });
        });
    }
}
