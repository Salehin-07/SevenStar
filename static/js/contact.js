/**
 * SevenStar Limo & Chauffeur — contact.js
 * Contact page interactions: scroll reveal, char counter, email validation
 */

(function () {
    'use strict';

    /* ── Scroll reveal ─────────────────────────────────────── */
    var els = document.querySelectorAll('.cp__reveal');
    if ('IntersectionObserver' in window) {
        var obs = new IntersectionObserver(function (entries) {
            entries.forEach(function (e) {
                if (e.isIntersecting) {
                    e.target.classList.add('cp__in');
                    obs.unobserve(e.target);
                }
            });
        }, { threshold: 0.1 });
        els.forEach(function (el) { obs.observe(el); });
    } else {
        els.forEach(function (el) { el.classList.add('cp__in'); });
    }

    /* ── Char counter ──────────────────────────────────────── */
    var ta    = document.getElementById('cp-what-said');
    var count = document.getElementById('cp-count');
    if (ta && count) {
        ta.addEventListener('input', function () {
            count.textContent = ta.value.length + ' / 1200';
        });
    }

    /* ── Email-only validation, then normal POST submit ────── */
    var form     = document.getElementById('cp-form');
    var emailEl  = document.getElementById('cp-email');
    var emailErr = document.getElementById('cp-email-err');
    if (!form || !emailEl) return;

    var re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    /* Clear error as user types */
    emailEl.addEventListener('input', function () {
        emailEl.classList.remove('cp__bad');
        emailErr.classList.remove('cp__show');
    });

    form.addEventListener('submit', function (e) {
        var val = emailEl.value.trim();
        if (!val || !re.test(val)) {
            e.preventDefault();
            emailEl.classList.add('cp__bad');
            emailErr.classList.add('cp__show');
            emailEl.focus();
        }
        /* valid — browser submits the form normally to Django */
    });

}());
