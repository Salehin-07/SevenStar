/**
 * SevenStar Limo & Chauffeur — verify.js
 * Email verification page interactions:
 *   - OTP digit-box navigation (forward, backspace, arrows)
 *   - Paste handling for full 6-digit code
 *   - Sync visible boxes → hidden consolidated input
 *   - Enable/disable verify button based on completeness
 *   - Loading state on valid submit
 *   - 10-minute countdown timer with expiry state
 */

(function () {
    'use strict';

    var digits    = Array.from(document.querySelectorAll('.su__otp-digit'));
    var hidden    = document.getElementById('su-otp-hidden');
    var verifyBtn = document.getElementById('su-verify-btn');
    var form      = document.getElementById('su-verify-form');
    var countdown = document.getElementById('su-countdown');

    if (!digits.length) return;

    /* ── Auto-focus first box ───────────────────────────────── */
    digits[0].focus();

    /* ── Sync hidden field & toggle submit button ───────────── */
    function syncHidden() {
        var val = digits.map(function (d) { return d.value; }).join('');
        hidden.value = val;
        verifyBtn.disabled = val.length < 6;
    }

    /* ── Input handling ─────────────────────────────────────── */
    digits.forEach(function (box, idx) {
        box.addEventListener('input', function () {
            var raw = box.value.replace(/\D/g, '');

            /* Handle paste of full 6-digit code into first box */
            if (raw.length > 1) {
                raw.split('').slice(0, 6).forEach(function (ch, i) {
                    if (digits[i]) digits[i].value = ch;
                });
                var last = Math.min(raw.length - 1, 5);
                digits[last].focus();
                syncHidden();
                return;
            }

            box.value = raw;
            if (raw && idx < digits.length - 1) digits[idx + 1].focus();
            syncHidden();
        });

        box.addEventListener('keydown', function (e) {
            /* Backspace — clear current then move back */
            if (e.key === 'Backspace') {
                if (box.value) {
                    box.value = '';
                    syncHidden();
                } else if (idx > 0) {
                    digits[idx - 1].focus();
                    digits[idx - 1].value = '';
                    syncHidden();
                }
            }
            /* Arrow navigation */
            if (e.key === 'ArrowLeft'  && idx > 0) {
                e.preventDefault();
                digits[idx - 1].focus();
            }
            if (e.key === 'ArrowRight' && idx < digits.length - 1) {
                e.preventDefault();
                digits[idx + 1].focus();
            }
        });

        /* Select-all on focus for easy overwrite */
        box.addEventListener('focus', function () { box.select(); });
    });

    /* ── Clear bad state when user starts retyping ──────────── */
    digits.forEach(function (d) {
        d.addEventListener('input', function () {
            digits.forEach(function (x) { x.classList.remove('su__bad'); });
        });
    });

    /* ── Form submit: validate + loading state ──────────────── */
    form.addEventListener('submit', function (e) {
        syncHidden();
        var val = hidden.value;

        if (val.length < 6 || !/^\d{6}$/.test(val)) {
            e.preventDefault();
            digits.forEach(function (d) { d.classList.add('su__bad'); });
            digits[0].focus();
            return;
        }

        verifyBtn.disabled = true;
        verifyBtn.innerHTML =
            '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"' +
            ' style="animation:su-spin 1s linear infinite" aria-hidden="true">' +
            '<path d="M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z" opacity=".25"/>' +
            '<path d="M21 12a9 9 0 0 0-9-9"/></svg>' +
            ' Verifying\u2026';
    });

    /* ── 10-minute countdown ────────────────────────────────── */
    if (!countdown) return;

    var endTime = Date.now() + 10 * 60 * 1000;

    function tick() {
        var remaining = Math.max(0, Math.round((endTime - Date.now()) / 1000));
        var m = Math.floor(remaining / 60);
        var s = remaining % 60;
        countdown.textContent = m + ':' + (s < 10 ? '0' : '') + s;

        if (remaining <= 60) {
            countdown.style.color = 'var(--su-err)';
        }
        if (remaining > 0) {
            setTimeout(tick, 1000);
        } else {
            countdown.textContent = 'Expired';
            verifyBtn.disabled = true;
        }
    }
    tick();

}());
