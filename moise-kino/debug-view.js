class DebugView {
    constructor(app) {
        this.app = app;
        this.subscribed = false;
        this.showNoise = true;
    }

    bind() {
        document.getElementById('btnIoStreamOn').addEventListener('click', () => {
            this.app.request('debug_io_stream', { enabled: true });
        });
        document.getElementById('btnIoStreamOff').addEventListener('click', () => {
            this.app.request('debug_io_stream', { enabled: false });
        });
        document.getElementById('showNoise').addEventListener('change', (e) => {
            this.showNoise = e.target.checked;
        });
        document.getElementById('btnSerialSend').addEventListener('click', () => this.sendSerial());
        document.getElementById('serialCommand').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') this.sendSerial();
        });
    }

    async onShow() {
        this.renderLanes(this.app.lastData);
        this.renderErrors(this.app.lastData);
        this.fillControllerSelect(this.app.lastData);
        if (!this.subscribed) {
            const res = await this.app.request('serial_log_subscribe');
            this.subscribed = true;
            if (res && res.ok && Array.isArray(res.data)) {
                res.data.forEach((entry) => this.appendSerial(entry));
            }
        }
    }

    async onHide() {
        if (this.subscribed) {
            await this.app.request('serial_log_unsubscribe');
            this.subscribed = false;
        }
    }

    update(data) {
        this.renderLanes(data);
        this.renderErrors(data);
        this.renderSerialStats(data);
        this.fillControllerSelect(data);
        if (data.io_states) this.appendIoEvents(data.io_states);
    }

    onSerialEntry(entry) {
        this.appendSerial(entry);
    }

    fillControllerSelect(data) {
        const sel = document.getElementById('serialController');
        const controllers = (data && data.controllers) || [];
        const current = sel.value;
        sel.innerHTML = controllers.map((c) =>
            `<option value="${c.id}">#${c.id} ${c.port || ''}</option>`
        ).join('');
        if (current) sel.value = current;
    }

    renderLanes(data) {
        const el = document.getElementById('debugLanes');
        const controllers = (data && data.controllers) || [];
        if (!controllers.length) {
            el.innerHTML = '<p class="muted">Keine Controller</p>';
            return;
        }
        el.innerHTML = controllers.map((c) => {
            const laneIds = Object.keys(c.lanes || {}).sort();
            return laneIds.map((local) => {
                const globalId = c.lanes[local];
                const prefix = `${c.id}:${local}:`;
                const io = data.io_states || {};
                const lights = ['home', 'win', 's1', 's2', 's3'].map((name) => {
                    const key = `${c.id}:${local}:${name}`;
                    // firmware keys are "local:name" inside controller; brain prefixes controller id
                    const alt = Object.keys(io).find((k) => k === key || k.endsWith(`:${local}:${name}`) || k === `${local}:${name}`);
                    const on = alt != null ? io[alt] : (io[`${local}:${name}`] || 0);
                    // Prefer controller-scoped keys from brain: `${id}:${local}:${name}` built in main as `${id}:${k}` where k is `local:name`
                    const scoped = io[`${c.id}:${local}:${name}`];
                    const val = scoped != null ? scoped : on;
                    return `<span class="io-light ${val ? 'on' : ''}">${name}</span>`;
                }).join('');
                return `
                    <div class="debug-lane" data-cid="${c.id}" data-lane="${local}">
                        <strong>Ctrl ${c.id} / Lane ${local}</strong> → Maus ${globalId}
                        <div class="io-lights">${lights}</div>
                        <div class="motor-btns">
                            <button type="button" data-motor="fwd">Vor</button>
                            <button type="button" data-motor="rev">Zurück</button>
                            <button type="button" data-motor="stop">Stop</button>
                        </div>
                        <div class="led-btns">
                            <button type="button" data-led="on">LED an</button>
                            <button type="button" data-led="off">LED aus</button>
                            <button type="button" data-led="255,0,0">Rot</button>
                            <button type="button" data-led="0,255,0">Grün</button>
                        </div>
                    </div>
                `;
            }).join('');
        }).join('');

        el.querySelectorAll('.debug-lane').forEach((laneEl) => {
            const cid = Number(laneEl.dataset.cid);
            const lane = Number(laneEl.dataset.lane);
            laneEl.querySelectorAll('[data-motor]').forEach((btn) => {
                const dir = btn.dataset.motor;
                if (dir === 'stop') {
                    btn.addEventListener('click', () => {
                        this.app.request('debug_motor', { controller_id: cid, lane, direction: 'stop' });
                    });
                } else {
                    const start = () => this.app.request('debug_motor', {
                        controller_id: cid, lane, direction: dir, ms: 400
                    });
                    btn.addEventListener('mousedown', start);
                    btn.addEventListener('touchstart', (e) => { e.preventDefault(); start(); });
                    btn.addEventListener('mouseup', () => {
                        this.app.request('debug_motor', { controller_id: cid, lane, direction: 'stop' });
                    });
                    btn.addEventListener('mouseleave', () => {
                        this.app.request('debug_motor', { controller_id: cid, lane, direction: 'stop' });
                    });
                    btn.addEventListener('touchend', () => {
                        this.app.request('debug_motor', { controller_id: cid, lane, direction: 'stop' });
                    });
                }
            });
            laneEl.querySelectorAll('[data-led]').forEach((btn) => {
                btn.addEventListener('click', () => {
                    this.app.request('debug_led', {
                        controller_id: cid,
                        lane,
                        color: btn.dataset.led
                    });
                });
            });
        });
    }

    renderSerialStats(data) {
        const el = document.getElementById('serialStats');
        const controllers = (data && data.controllers) || [];
        el.innerHTML = controllers.map((c) => {
            const s = c.serial_stats || {};
            return `#${c.id}: valid=${s.valid || 0} discard=${s.discarded || 0} decode=${s.decode_errors || 0} reboots=${s.reboots || 0} last=${s.seconds_since_valid != null ? s.seconds_since_valid + 's' : '-'}`;
        }).join('<br>');
    }

    renderErrors(data) {
        const el = document.getElementById('errorList');
        const errors = (data && data.errors) || [];
        if (!errors.length) {
            el.textContent = 'Keine aktiven Fehler';
            return;
        }
        el.innerHTML = errors.map((e) =>
            `<div>[${e.severity}] ${e.code} @ ${e.source}: ${e.message}</div>`
        ).join('');
    }

    appendSerial(entry) {
        const noiseTypes = ['noise_no_hash', 'bootlog', 'decode_error', 'discarded_pre_rdy'];
        if (!this.showNoise && noiseTypes.indexOf(entry.classification) >= 0) return;
        const el = document.getElementById('serialLog');
        const ts = new Date((entry.ts || 0) * 1000).toLocaleTimeString();
        const cls = entry.classification || entry.direction || '';
        const line = document.createElement('div');
        line.className = cls;
        line.textContent = `${ts} ${entry.direction || ''} [${cls}] ${entry.port || ''} ${entry.text || ''}`;
        el.appendChild(line);
        while (el.childNodes.length > 400) el.removeChild(el.firstChild);
        el.scrollTop = el.scrollHeight;
    }

    appendIoEvents(ioStates) {
        // lightweight: banner already has live lights; optional log skip to avoid spam
    }

    async sendSerial() {
        const cid = Number(document.getElementById('serialController').value);
        const command = document.getElementById('serialCommand').value.trim();
        if (!command) return;
        await this.app.request('serial_send', { controller_id: cid, command });
        document.getElementById('serialCommand').value = '';
    }
}
