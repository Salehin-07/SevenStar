/**
 * SevenStar Limo & Chauffeur — signup.js
 * Signup page interactions:
 *   - Clear field errors on input
 *   - Password strength meter
 *   - Password visibility toggles (password + confirm)
 *   - Client-side validation on submit
 *   - Loading state on valid submit
 */

(function () {
    'use strict';

    var form    = document.getElementById('su-form');
    var btn     = document.getElementById('su-btn');
    var firstEl = document.getElementById('su-first');
    var lastEl  = document.getElementById('su-last');
    var emailEl = document.getElementById('su-email');
    var phoneEl = document.getElementById('su-phone');
    var pwEl    = document.getElementById('su-pw');
    var pw2El   = document.getElementById('su-pw2');
    var termsEl = document.getElementById('su-terms');

    if (!form) return;

    /* ── Helpers ───────────────────────────────────────────── */
    function setErr(inp, errId) {
        inp.classList.add('su__bad');
        inp.classList.remove('su__good');
        var el = document.getElementById(errId);
        if (el) el.classList.add('su__show');
    }
    function clearErr(inp, errId) {
        inp.classList.remove('su__bad');
        var el = document.getElementById(errId);
        if (el) el.classList.remove('su__show');
    }
    function setGood(inp) {
        inp.classList.remove('su__bad');
        inp.classList.add('su__good');
    }

    /* Clear errors on input */
    [
        [firstEl, 'su-first-err'],
        [lastEl,  'su-last-err'],
        [emailEl, 'su-email-err'],
        [phoneEl, 'su-phone-err'],
        [pwEl,    'su-pw-err'],
        [pw2El,   'su-pw2-err'],
    ].forEach(function (pair) {
        pair[0].addEventListener('input', function () { clearErr(pair[0], pair[1]); });
    });

    /* ── Password strength meter ────────────────────────────── */
    var strengthWrap = document.getElementById('su-strength');
    var strengthFill = document.getElementById('su-strength-fill');
    var strengthLbl  = document.getElementById('su-strength-lbl');

    function calcStrength(pw) {
        var score = 0;
        if (pw.length >= 8)          score++;
        if (pw.length >= 12)         score++;
        if (/[A-Z]/.test(pw))        score++;
        if (/[0-9]/.test(pw))        score++;
        if (/[^A-Za-z0-9]/.test(pw)) score++;
        return score;
    }

    pwEl.addEventListener('input', function () {
        var pw = pwEl.value;
        if (!pw) {
            strengthWrap.classList.remove('su__show');
            return;
        }
        strengthWrap.classList.add('su__show');

        var s = calcStrength(pw);
        var pct, color, lbl;
        if      (s <= 1) { pct = '25%';  color = '#c0392b'; lbl = 'Weak'; }
        else if (s <= 2) { pct = '50%';  color = '#e67e22'; lbl = 'Fair'; }
        else if (s <= 3) { pct = '75%';  color = '#f1c40f'; lbl = 'Good'; }
        else             { pct = '100%'; color = '#2a6e48'; lbl = 'Strong'; }

        strengthFill.style.width      = pct;
        strengthFill.style.background = color;
        strengthLbl.textContent       = lbl;
        strengthLbl.style.color       = color;
    });

    /* ── Password visibility toggles ──────────────────────── */
    function makeToggle(btnId, inputEl) {
        var toggleBtn = document.getElementById(btnId);
        if (!toggleBtn) return;
        toggleBtn.addEventListener('click', function () {
            var isHidden = inputEl.type === 'password';
            inputEl.type = isHidden ? 'text' : 'password';
            toggleBtn.setAttribute('aria-label', isHidden ? 'Hide password' : 'Show password');
            toggleBtn.querySelector('svg').innerHTML = isHidden
                ? '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/>'
                : '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>';
        });
    }
    makeToggle('su-pw-eye',  pwEl);
    makeToggle('su-pw2-eye', pw2El);

    /* ── Submit validation ──────────────────────────────────── */
    var emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    var phoneRe = /^[\d\s\+\-\(\)]{6,15}$/;

    form.addEventListener('submit', function (e) {
        var valid = true;

        if (!firstEl.value.trim()) { setErr(firstEl, 'su-first-err'); valid = false; }
        else setGood(firstEl);

        if (!lastEl.value.trim()) { setErr(lastEl, 'su-last-err'); valid = false; }
        else setGood(lastEl);

        if (!emailEl.value.trim() || !emailRe.test(emailEl.value.trim())) {
            setErr(emailEl, 'su-email-err'); valid = false;
        } else setGood(emailEl);

        if (!phoneEl.value.trim() || !phoneRe.test(phoneEl.value.trim())) {
            setErr(phoneEl, 'su-phone-err'); valid = false;
        } else setGood(phoneEl);

        if (!pwEl.value || pwEl.value.length < 8) {
            setErr(pwEl, 'su-pw-err'); valid = false;
        } else setGood(pwEl);

        if (!pw2El.value || pw2El.value !== pwEl.value) {
            setErr(pw2El, 'su-pw2-err'); valid = false;
        } else setGood(pw2El);

        if (!termsEl.checked) {
            termsEl.focus();
            valid = false;
        }

        if (!valid) {
            e.preventDefault();
            var firstBad = form.querySelector('.su__bad');
            if (firstBad) firstBad.scrollIntoView({ behavior: 'smooth', block: 'center' });
            return;
        }

        /* Valid — loading state, let Django handle registration */
        btn.disabled = true;
        btn.innerHTML =
            '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"' +
            ' style="animation:su-spin 1s linear infinite" aria-hidden="true">' +
            '<path d="M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z" opacity=".25"/>' +
            '<path d="M21 12a9 9 0 0 0-9-9"/></svg>' +
            ' Creating Account\u2026';
    });

}());
