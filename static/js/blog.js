(function () {
    'use strict';

    /* ── Scroll reveal ──────────────────────────────────────── */
    var reveals = document.querySelectorAll('.bl__reveal');
    if ('IntersectionObserver' in window) {
        var io = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('bl__in');
                    io.unobserve(entry.target);
                }
            });
        }, { threshold: 0.12 });
        reveals.forEach(function (el) { io.observe(el); });
    } else {
        reveals.forEach(function (el) { el.classList.add('bl__in'); });
    }

}());
