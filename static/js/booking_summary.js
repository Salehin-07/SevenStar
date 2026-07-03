/**
 * SevenStar Limo & Chauffeur — booking_summary.js
 * Review / price step interactions:
 *   - Confirm button loading state (disable, show spinner, swap label)
 */

(function () {
    'use strict';

    var form    = document.getElementById('bs-confirm-form');
    var btn     = document.getElementById('bs-confirm-btn');
    var spinner = document.getElementById('bs-spin');
    var arrow   = document.getElementById('bs-btn-arrow');
    var label   = document.getElementById('bs-btn-label');

    if (!form || !btn) return;

    form.addEventListener('submit', function () {
        btn.disabled = true;
        if (spinner) spinner.style.display = 'block';
        if (arrow)   arrow.style.display   = 'none';
        if (label)   label.textContent     = 'Redirecting to payment\u2026';
    });

}());
