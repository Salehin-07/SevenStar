/**
 * SevenStar Limo & Chauffeur — index.js
 * Home page interactions: scroll reveal, FAQ accordion, scroll cue
 */

(function () {
    'use strict';

    /* ── Scroll reveal ──────────────────────────────────────── */
    var reveals = document.querySelectorAll('.hp__reveal');
    if ('IntersectionObserver' in window) {
        var io = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('hp__visible');
                    io.unobserve(entry.target);
                }
            });
        }, { threshold: 0.12 });
        reveals.forEach(function (el) { io.observe(el); });
    } else {
        /* Fallback for old browsers: show everything immediately */
        reveals.forEach(function (el) { el.classList.add('hp__visible'); });
    }

    /* ── FAQ accordion ──────────────────────────────────────── */
    document.querySelectorAll('.hp__faq-q').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var item   = btn.closest('.hp__faq-item');
            var answer = item.querySelector('.hp__faq-answer');
            var isOpen = item.classList.contains('hp__faq-open');

            /* Close all open items */
            document.querySelectorAll('.hp__faq-item.hp__faq-open').forEach(function (i) {
                i.classList.remove('hp__faq-open');
                i.querySelector('.hp__faq-q').setAttribute('aria-expanded', 'false');
                i.querySelector('.hp__faq-answer').setAttribute('aria-hidden', 'true');
            });

            /* Open clicked item (toggle off if already open) */
            if (!isOpen) {
                item.classList.add('hp__faq-open');
                btn.setAttribute('aria-expanded', 'true');
                answer.setAttribute('aria-hidden', 'false');
            }
        });
    });

    /* ── Hero scroll cue ────────────────────────────────────── */
    var cue = document.querySelector('.hp__scroll-cue');
    if (cue) {
        cue.addEventListener('click', function (e) {
            e.preventDefault();
            var target = document.getElementById('hp-bstrip');
            if (target) {
                target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    }

}());
