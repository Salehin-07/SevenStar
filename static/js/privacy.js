/**
 * SevenStar Limo & Chauffeur — privacy.js
 * Privacy Policy page interactions:
 *   - IntersectionObserver scroll reveal
 *   - TOC active section highlight on scroll
 */

(function () {
    'use strict';

    /* ── Scroll reveal ─────────────────────────────────────── */
    var els = document.querySelectorAll('.pp__reveal');
    if ('IntersectionObserver' in window) {
        var obs = new IntersectionObserver(function (entries) {
            entries.forEach(function (e) {
                if (e.isIntersecting) {
                    e.target.classList.add('pp__in');
                    obs.unobserve(e.target);
                }
            });
        }, { threshold: 0.08 });
        els.forEach(function (el) { obs.observe(el); });
    } else {
        els.forEach(function (el) { el.classList.add('pp__in'); });
    }

    /* ── TOC active highlight on scroll ───────────────────── */
    var links   = document.querySelectorAll('.pp__toc-link');
    var clauses = document.querySelectorAll('.pp__clause');
    if (!links.length || !clauses.length) return;

    var scrollObs = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
            if (entry.isIntersecting) {
                links.forEach(function (l) { l.classList.remove('pp__active'); });
                var active = document.querySelector('.pp__toc-link[href="#' + entry.target.id + '"]');
                if (active) active.classList.add('pp__active');
            }
        });
    }, { rootMargin: '-15% 0px -70% 0px' });

    clauses.forEach(function (c) { if (c.id) scrollObs.observe(c); });

}());
