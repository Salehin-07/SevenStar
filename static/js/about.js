(function () {
    'use strict';

    /**
     * Initialize Scroll Reveal Animations
     * Uses IntersectionObserver for high performance SEO-friendly reveals
     */
    const initScrollReveal = () => {
        const revealElements = document.querySelectorAll('.ab__reveal');
        
        if (!revealElements.length) return;

        // Configuration for the observer
        const observerOptions = {
            threshold: 0.15, // Trigger when 15% of the element is visible
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('ab__in');
                    // Stop observing once the animation has triggered
                    observer.unobserve(entry.target);
                }
            });
        }, observerOptions);

        revealElements.forEach((el) => observer.observe(el));
    };

    // Run on DOM Content Loaded
    document.addEventListener('DOMContentLoaded', () => {
        initScrollReveal();
    });

}());
