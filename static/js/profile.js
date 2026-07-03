/**
 * SevenStar Limo & Chauffeur — profile.js
 * Profile page interactions:
 *   - IntersectionObserver reveal animations
 *   - Sidebar tab switching
 *   - Password eye toggles (all 3 password fields)
 *   - Password strength meter (new password field)
 *   - Personal details form client-side validation
 *   - Change password form client-side validation
 *   - Open correct tab when Django redirects with ?tab= in URL
 */

(function () {
    'use strict';

    /* ── Reveal animations ──────────────────────────────────── */
    var revealEls = document.querySelectorAll('.pr__reveal');
    if ('IntersectionObserver' in window) {
        var obs = new IntersectionObserver(function (entries) {
            entries.forEach(function (e) {
                if (e.isIntersecting) {
                    e.target.classList.add('pr__in');
                    obs.unobserve(e.target);
                }
            });
        }, { threshold: 0.08 });
        revealEls.forEach(function (el) { obs.observe(el); });
    } else {
        revealEls.forEach(function (el) { el.classList.add('pr__in'); });
    }

    /* ── Sidebar tab switching ──────────────────────────────── */
    var tabBtns  = document.querySelectorAll('.pr__sidenav-btn[data-tab]');
    var panels   = document.querySelectorAll('.pr__panel');

    tabBtns.forEach(function (btn) {
        btn.addEventListener('click', function () {
            var tab = btn.getAttribute('data-tab');

            tabBtns.forEach(function (b) {
                b.classList.remove('pr__active');
                b.removeAttribute('aria-current');
            });
            panels.forEach(function (p) { p.classList.remove('pr__active'); });

            btn.classList.add('pr__active');
            btn.setAttribute('aria-current', 'true');
            var panel = document.getElementById('pr-panel-' + tab);
            if (panel) panel.classList.add('pr__active');
        });
    });

    /* ── Password eye toggles ───────────────────────────────── */
    document.querySelectorAll('.pr__eye').forEach(function (eyeBtn) {
        eyeBtn.addEventListener('click', function () {
            var inp = document.getElementById(eyeBtn.getAttribute('data-target'));
            if (!inp) return;
            var isHidden = inp.type === 'password';
            inp.type = isHidden ? 'text' : 'password';
            eyeBtn.setAttribute('aria-label', isHidden ? 'Hide password' : 'Show password');
            eyeBtn.querySelector('svg').innerHTML = isHidden
                ? '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/>'
                : '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>';
        });
    });

    /* ── Password strength meter ────────────────────────────── */
    var newPwEl      = document.getElementById('pr-new-pw');
    var strengthWrap = document.getElementById('pr-strength');
    var strengthFill = document.getElementById('pr-strength-fill');
    var strengthLbl  = document.getElementById('pr-strength-lbl');

    if (newPwEl && strengthWrap) {
        newPwEl.addEventListener('input', function () {
            var pw = newPwEl.value;
            if (!pw) { strengthWrap.classList.remove('pr__show'); return; }
            strengthWrap.classList.add('pr__show');

            var score = 0;
            if (pw.length >= 8)           score++;
            if (pw.length >= 12)          score++;
            if (/[A-Z]/.test(pw))         score++;
            if (/[0-9]/.test(pw))         score++;
            if (/[^A-Za-z0-9]/.test(pw))  score++;

            var pct, color, lbl;
            if      (score <= 1) { pct = '25%';  color = '#c0392b'; lbl = 'Weak'; }
            else if (score <= 2) { pct = '50%';  color = '#e67e22'; lbl = 'Fair'; }
            else if (score <= 3) { pct = '75%';  color = '#f1c40f'; lbl = 'Good'; }
            else                 { pct = '100%'; color = '#2a6e48'; lbl = 'Strong'; }

            strengthFill.style.width      = pct;
            strengthFill.style.background = color;
            strengthLbl.textContent       = lbl;
            strengthLbl.style.color       = color;
        });
    }

    /* ── Details form validation ────────────────────────────── */
    var detailsForm = document.getElementById('pr-details-form');
    if (detailsForm) {
        var emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        var phoneRe = /^[\d\s\+\-\(\)]{6,15}$/;

        function setErr(inputId, errId) {
            var inp = document.getElementById(inputId);
            var err = document.getElementById(errId);
            if (inp) inp.classList.add('pr__bad');
            if (err) err.classList.add('pr__show');
        }
        function clearErr(inputId, errId) {
            var inp = document.getElementById(inputId);
            var err = document.getElementById(errId);
            if (inp) inp.classList.remove('pr__bad');
            if (err) err.classList.remove('pr__show');
        }

        [
            ['pr-first', 'pr-first-err'],
            ['pr-last',  'pr-last-err'],
            ['pr-email', 'pr-email-err'],
            ['pr-phone', 'pr-phone-err'],
        ].forEach(function (pair) {
            var el = document.getElementById(pair[0]);
            if (el) el.addEventListener('input', function () { clearErr(pair[0], pair[1]); });
        });

        detailsForm.addEventListener('submit', function (e) {
            var valid = true;

            if (!document.getElementById('pr-first').value.trim()) { setErr('pr-first', 'pr-first-err'); valid = false; }
            if (!document.getElementById('pr-last').value.trim())  { setErr('pr-last',  'pr-last-err');  valid = false; }

            var email = document.getElementById('pr-email').value.trim();
            if (!email || !emailRe.test(email)) { setErr('pr-email', 'pr-email-err'); valid = false; }

            var phone = document.getElementById('pr-phone').value.trim();
            if (!phone || !phoneRe.test(phone)) { setErr('pr-phone', 'pr-phone-err'); valid = false; }

            if (!valid) { e.preventDefault(); return; }

            var btn = document.getElementById('pr-details-btn');
            btn.disabled = true;
            btn.innerHTML =
                '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"' +
                ' style="animation:pr-spin 1s linear infinite" aria-hidden="true">' +
                '<path d="M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z" opacity=".25"/>' +
                '<path d="M21 12a9 9 0 0 0-9-9"/></svg> Saving\u2026';
        });
    }

    /* ── Password form validation ───────────────────────────── */
    var pwForm = document.getElementById('pr-pw-form');
    if (pwForm) {
        var curPwEl  = document.getElementById('pr-cur-pw');
        var newPwFrm = document.getElementById('pr-new-pw');
        var confPwEl = document.getElementById('pr-conf-pw');

        var pwErrMap = {
            'pr-cur-pw':  'pr-cur-err',
            'pr-new-pw':  'pr-new-err',
            'pr-conf-pw': 'pr-conf-err',
        };
        Object.keys(pwErrMap).forEach(function (id) {
            var el = document.getElementById(id);
            if (el) el.addEventListener('input', function () {
                el.classList.remove('pr__bad');
                var err = document.getElementById(pwErrMap[id]);
                if (err) err.classList.remove('pr__show');
            });
        });

        pwForm.addEventListener('submit', function (e) {
            var valid = true;

            if (!curPwEl.value) {
                curPwEl.classList.add('pr__bad');
                document.getElementById('pr-cur-err').classList.add('pr__show');
                valid = false;
            }
            if (!newPwFrm.value || newPwFrm.value.length < 8) {
                newPwFrm.classList.add('pr__bad');
                document.getElementById('pr-new-err').classList.add('pr__show');
                valid = false;
            }
            if (!confPwEl.value || confPwEl.value !== newPwFrm.value) {
                confPwEl.classList.add('pr__bad');
                document.getElementById('pr-conf-err').classList.add('pr__show');
                valid = false;
            }

            if (!valid) { e.preventDefault(); return; }

            var btn = document.getElementById('pr-pw-btn');
            btn.disabled = true;
            btn.innerHTML =
                '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"' +
                ' style="animation:pr-spin 1s linear infinite" aria-hidden="true">' +
                '<path d="M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z" opacity=".25"/>' +
                '<path d="M21 12a9 9 0 0 0-9-9"/></svg> Updating\u2026';
        });
    }

    /* ── Open correct tab from ?tab= URL param ──────────────── */
    var params = new URLSearchParams(window.location.search);
    var tabParam = params.get('tab');
    if (tabParam) {
        var targetBtn = document.querySelector('.pr__sidenav-btn[data-tab="' + tabParam + '"]');
        if (targetBtn) targetBtn.click();
    }

}());
