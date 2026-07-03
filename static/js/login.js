/**
 * SevenStar Limo & Chauffeur — login.js
 * Login page interactions:
 *   - Clear field errors on input
 *   - Password visibility toggle
 *   - Client-side submit validation (prevents empty submission)
 *   - Loading state on valid submit
 */

(function () {
    'use strict';

    var form  = document.getElementById('li-form');
    var idEl  = document.getElementById('li-identifier');
    var pwEl  = document.getElementById('li-pw');
    var idErr = document.getElementById('li-id-err');
    var pwErr = document.getElementById('li-pw-err');
    var eyeBtn = document.getElementById('li-pw-eye');

    if (!form) return;

    /* ── Clear errors on input ─────────────────────────────── */
    idEl.addEventListener('input', function () {
        idEl.classList.remove('li__bad');
        idErr.classList.remove('li__show');
    });
    pwEl.addEventListener('input', function () {
        pwEl.classList.remove('li__bad');
        pwErr.classList.remove('li__show');
    });

    /* ── Password visibility toggle ────────────────────────── */
    eyeBtn.addEventListener('click', function () {
        var isHidden = pwEl.type === 'password';
        pwEl.type = isHidden ? 'text' : 'password';
        eyeBtn.setAttribute('aria-label', isHidden ? 'Hide password' : 'Show password');
        eyeBtn.querySelector('svg').innerHTML = isHidden
            ? '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/>'
            : '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>';
    });

    /* ── Submit validation ──────────────────────────────────── */
    form.addEventListener('submit', function (e) {
        var valid = true;

        if (!idEl.value.trim()) {
            idEl.classList.add('li__bad');
            idErr.classList.add('li__show');
            valid = false;
        }
        if (!pwEl.value) {
            pwEl.classList.add('li__bad');
            pwErr.classList.add('li__show');
            valid = false;
        }

        if (!valid) {
            e.preventDefault();
            form.querySelector('.li__bad').focus();
            return;
        }

        /* Valid — show loading state, let Django handle auth */
        var btn = document.getElementById('li-btn');
        btn.disabled = true;
        btn.innerHTML =
            '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"' +
            ' style="animation:li-spin 1s linear infinite" aria-hidden="true">' +
            '<path d="M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z" opacity=".25"/>' +
            '<path d="M21 12a9 9 0 0 0-9-9"/></svg>' +
            ' Signing In\u2026';
    });

}());
