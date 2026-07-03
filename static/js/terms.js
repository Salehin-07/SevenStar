/**
 * SevenStar Limo & Chauffeur — terms.js
 * Terms & Conditions page interactions:
 *   - IntersectionObserver scroll reveal
 *   - TOC active section highlight on scroll
 */

(function () {
    'use strict';

    /* ── Scroll reveal ─────────────────────────────────────── */
    var els = document.querySelectorAll('.tc__reveal');
    if ('IntersectionObserver' in window) {
        var obs = new IntersectionObserver(function (entries) {
            entries.forEach(function (e) {
                if (e.isIntersecting) {
                    e.target.classList.add('tc__in');
                    obs.unobserve(e.target);
                }
            });
        }, { threshold: 0.08 });
        els.forEach(function (el) { obs.observe(el); });
    } else {
        els.forEach(function (el) { el.classList.add('tc__in'); });
    }

    /* ── TOC active highlight on scroll ───────────────────── */
    var links   = document.querySelectorAll('.tc__toc-link');
    var clauses = document.querySelectorAll('.tc__clause');
    if (!links.length || !clauses.length) return;

    var scrollObs = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
            if (entry.isIntersecting) {
                links.forEach(function (l) { l.classList.remove('tc__active'); });
                var active = document.querySelector('.tc__toc-link[href="#' + entry.target.id + '"]');
                if (active) active.classList.add('tc__active');
            }
        });
    }, { rootMargin: '-15% 0px -70% 0px' });

    clauses.forEach(function (c) { scrollObs.observe(c); });

}());
