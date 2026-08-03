class ClaimView {
    static ERRORS = {
        wrong_pin: 'Wrong PIN',
        invalid: 'Invalid input',
        rate_limited: 'Too many attempts — wait a moment',
        expired: 'Time is up',
        already_claimed: 'Already saved',
        no_claim: 'No claim open'
    };

    constructor(app) {
        this.app = app;
        this.step = 'name';
        this.name = '';
        this.pin = '';
        this.error = '';
        this._busy = false;
        this._lastTypingAt = 0;
        this._visible = false;

        this.box = document.getElementById('claimBox');
        this.inviteEl = document.getElementById('claimInvite');
        this.countdownEl = document.getElementById('claimCountdown');
        this.valueEl = document.getElementById('claimValue');
        this.errorEl = document.getElementById('claimError');
        this.keysEl = document.getElementById('claimKeys');
        this.actionsEl = document.getElementById('claimActions');
        this.doneEl = document.getElementById('claimDone');

        this._onKeyDown = (e) => this.handleKeyDown(e);
        document.addEventListener('keydown', this._onKeyDown, true);
    }

    update(data) {
        const claim = data && data.claim;
        if (!claim || (!claim.open && !claim.claimed)) {
            this.hide();
            return;
        }

        if (claim.claimed) {
            this.showDone((data.lastResult && data.lastResult.message) || 'Saved!');
            return;
        }

        if (!this._visible) {
            this.reset();
            this._visible = true;
        }
        this.box.classList.remove('hidden');
        if (this.doneEl) this.doneEl.classList.add('hidden');
        if (this.inviteEl) this.inviteEl.classList.remove('hidden');
        if (this.countdownEl) {
            this.countdownEl.textContent = String(claim.secondsLeft || 0);
            this.countdownEl.classList.toggle('urgent', (claim.secondsLeft || 0) <= 5);
        }
        this.render();
    }

    showDone(message) {
        this._visible = true;
        this.box.classList.remove('hidden');
        if (this.inviteEl) this.inviteEl.classList.add('hidden');
        if (this.keysEl) this.keysEl.innerHTML = '';
        if (this.actionsEl) this.actionsEl.innerHTML = '';
        if (this.valueEl) this.valueEl.textContent = '';
        if (this.errorEl) this.errorEl.classList.add('hidden');
        if (this.countdownEl) this.countdownEl.textContent = '';
        if (this.doneEl) {
            this.doneEl.textContent = message;
            this.doneEl.classList.remove('hidden');
        }
    }

    hide() {
        if (!this._visible) return;
        this._visible = false;
        this.box.classList.add('hidden');
        this.reset();
    }

    reset() {
        this.step = 'name';
        this.name = '';
        this.pin = '';
        this.error = '';
        this._busy = false;
    }

    handleKeyDown(e) {
        if (!this._visible || !this.box || this.box.classList.contains('hidden')) return;
        if (this.doneEl && !this.doneEl.classList.contains('hidden')) return;

        if (this.step === 'name') {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.goPin();
                return;
            }
            if (e.key === 'Backspace') {
                e.preventDefault();
                this.backName();
                return;
            }
            if (e.key === ' ') {
                e.preventDefault();
                this.typeName(' ');
                return;
            }
            if (e.key.length === 1 && /[A-Za-z0-9ÄÖÜäöüß_.\- ]/.test(e.key)) {
                e.preventDefault();
                this.typeName(e.key);
            }
            return;
        }

        if (this.step === 'pin') {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.doClaim();
                return;
            }
            if (e.key === 'Backspace') {
                e.preventDefault();
                this.backPin();
                return;
            }
            if (/^[0-9]$/.test(e.key)) {
                e.preventDefault();
                this.typePin(e.key);
            }
        }
    }

    bumpTyping() {
        const now = Date.now();
        if (now - this._lastTypingAt < 1000) return;
        this._lastTypingAt = now;
        this.app.request('claim_typing', {}).catch(() => {});
    }

    render() {
        if (!this.errorEl || !this.keysEl || !this.actionsEl || !this.valueEl) return;
        this.errorEl.textContent = this.error || '';
        this.errorEl.classList.toggle('hidden', !this.error);
        this.keysEl.innerHTML = '';
        this.actionsEl.innerHTML = '';

        if (this.step === 'name') {
            this.valueEl.textContent = this.name || '…';
            this._renderKeyboard();
            this._btn(this.actionsEl, 'Next', () => this.goPin(), 'primary', !this.name.trim());
            return;
        }

        this.valueEl.textContent = '•'.repeat(this.pin.length) + '·'.repeat(Math.max(0, 4 - this.pin.length));
        this._renderKeypad();
        this._btn(this.actionsEl, 'Back', () => {
            this.step = 'name';
            this.pin = '';
            this.error = '';
            this.render();
        });
        this._btn(this.actionsEl, 'Save', () => this.doClaim(), 'primary', this.pin.length !== 4);
    }

    _renderKeyboard() {
        ['QWERTYUIOP', 'ASDFGHJKL', 'ZXCVBNM'].forEach((row) => {
            const rowEl = document.createElement('div');
            rowEl.className = 'key-row';
            row.split('').forEach((ch) => {
                rowEl.appendChild(this._key(ch, () => this.typeName(ch)));
            });
            this.keysEl.appendChild(rowEl);
        });
        const special = document.createElement('div');
        special.className = 'key-row';
        special.appendChild(this._key('␣', () => this.typeName(' '), 'wide'));
        special.appendChild(this._key('⌫', () => this.backName(), 'wide'));
        this.keysEl.appendChild(special);
    }

    _renderKeypad() {
        const keys = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '', '0', '⌫'];
        const rowEl = document.createElement('div');
        rowEl.className = 'keypad';
        keys.forEach((ch) => {
            if (!ch) {
                const spacer = document.createElement('div');
                spacer.className = 'key spacer';
                rowEl.appendChild(spacer);
                return;
            }
            if (ch === '⌫') {
                rowEl.appendChild(this._key(ch, () => this.backPin()));
            } else {
                rowEl.appendChild(this._key(ch, () => this.typePin(ch)));
            }
        });
        this.keysEl.appendChild(rowEl);
    }

    typeName(ch) {
        this.bumpTyping();
        if (this.name.length >= 12) return;
        this.name += ch;
        this.error = '';
        this.render();
    }

    backName() {
        this.bumpTyping();
        this.name = this.name.slice(0, -1);
        this.render();
    }

    goPin() {
        if (!this.name.trim()) return;
        this.bumpTyping();
        this.step = 'pin';
        this.pin = '';
        this.error = '';
        this.render();
    }

    typePin(ch) {
        this.bumpTyping();
        if (this.pin.length >= 4) return;
        this.pin += ch;
        this.error = '';
        this.render();
        if (this.pin.length === 4) {
            setTimeout(() => this.doClaim(), 120);
        }
    }

    backPin() {
        this.bumpTyping();
        this.pin = this.pin.slice(0, -1);
        this.render();
    }

    async doClaim() {
        if (this.pin.length !== 4 || this._busy) return;
        this._busy = true;
        try {
            const res = await this.app.request('claim', {
                name: this.name.trim(),
                pin: this.pin
            });
            if (res && res.ok) {
                this.showDone((res.data && res.data.message) || 'Saved!');
                return;
            }
            const err = (res && res.error) || 'invalid';
            this.error = ClaimView.ERRORS[err] || err;
            this.pin = '';
            this.render();
        } catch (e) {
            this.error = 'No connection';
            this.render();
        } finally {
            this._busy = false;
        }
    }

    _key(label, fn, extra) {
        const b = document.createElement('button');
        b.type = 'button';
        b.tabIndex = -1;
        b.className = 'key' + (extra ? ` ${extra}` : '');
        b.textContent = label;
        b.addEventListener('pointerdown', (e) => {
            e.preventDefault();
            fn();
        });
        return b;
    }

    _btn(parent, label, fn, cls, disabled) {
        const b = document.createElement('button');
        b.type = 'button';
        b.className = 'claim-btn' + (cls ? ` ${cls}` : '');
        b.textContent = label;
        b.disabled = !!disabled;
        b.addEventListener('click', fn);
        parent.appendChild(b);
        return b;
    }
}
