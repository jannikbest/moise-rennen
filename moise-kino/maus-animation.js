class MausAnimation {
    constructor() {
        this.padding = 20;
        this.availableWidth = 0;
        this.maxPoints = 15;
    }

    rebuildTracks(lanes) {
        const container = document.getElementById('mausTracks');
        if (!container) return;
        container.innerHTML = '';
        (lanes || []).forEach((lane) => {
            const id = lane.id;
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
            indicator.innerHTML = `<span class="maus-emoji">🐭</span><span class="maus-points" id="mausPoints${id}">0</span>`;

            track.appendChild(marks);
            track.appendChild(indicator);
            container.appendChild(track);
        });
        this.measure();
    }

    rebuildNameBar(lanes) {
        const bar = document.getElementById('mausNamesBottom');
        if (!bar) return;
        bar.innerHTML = '';
        (lanes || []).forEach((lane) => {
            const el = document.createElement('div');
            el.className = 'maus-name-bottom hidden';
            el.id = `maus${lane.id}-name-container`;
            el.innerHTML = `<div class="field-label">Maus ${lane.name || lane.id}</div><div id="maus${lane.id}NameValue" class="field-value">-</div>`;
            bar.appendChild(el);
        });
    }

    measure() {
        const track = document.querySelector('.maus-track');
        if (track) {
            this.availableWidth = Math.max(0, track.offsetWidth - this.padding * 2);
        }
    }

    setMausPosition(mausId, points) {
        const indicator = document.getElementById(`mausIndicator${mausId}`);
        const pointsEl = document.getElementById(`mausPoints${mausId}`);
        if (!indicator || !pointsEl) return;
        if (!this.availableWidth) this.measure();
        const clamped = Math.max(0, Math.min(this.maxPoints, Number(points) || 0));
        const translateX = (clamped / this.maxPoints) * this.availableWidth;
        indicator.style.transform = `translateY(-50%) translateX(${translateX}px)`;
        pointsEl.textContent = String(clamped);
        this.updateTrackMarks(mausId, clamped);
    }

    updateMausPosition(punktzahlen) {
        Object.keys(punktzahlen || {}).forEach((id) => {
            this.setMausPosition(id, punktzahlen[id]);
        });
    }

    updateTrackMarks(mausId, points) {
        const track = document.querySelector(`.maus-track[data-maus="${mausId}"]`);
        if (!track) return;
        track.querySelectorAll('.track-mark').forEach((mark) => {
            const n = Number(mark.dataset.mark);
            mark.classList.toggle('active', n === points);
        });
    }

    resetAllMausPositions() {
        document.querySelectorAll('.maus-indicator').forEach((el) => {
            const id = el.id.replace('mausIndicator', '');
            this.setMausPosition(id, 0);
        });
    }

    updatePositionsForResize() {
        this.measure();
        document.querySelectorAll('.maus-points').forEach((el) => {
            const id = el.id.replace('mausPoints', '');
            this.setMausPosition(id, Number(el.textContent) || 0);
        });
    }
}
