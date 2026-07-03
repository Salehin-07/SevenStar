/**
 * SevenStar Limo & Chauffeur — booking_form.js
 * Booking form interactions:
 *   - Vehicle card selection + hidden input sync
 *   - Passenger & bag dropdowns (built from data-* on cards)
 *   - Auto-upgrade vehicle when passenger/bag count exceeds capacity
 *   - Toggle switch add-ons (baby seat, return ride)
 *   - Baby / Child seat: dynamic per-child age fields
 *   - Google Places autocomplete (pickup, destination, extra stop)
 *   - Date min = today
 *   - Submit loading state
 *
 * Depends on globals injected by booking_form.html:
 *   BF_TYPE, BF_RATES, BF_IS_HOURLY, BF_CHILD_AGES
 */

/* ── Init ───────────────────────────────────────────────────── */
(function bfInit() {
    'use strict';

    if (!window.BF_RATES || !BF_RATES.length) return;

    var vehicleInput = document.getElementById('bfVehicleInput');
    if (vehicleInput && !vehicleInput.value && BF_RATES.length) {
        vehicleInput.value = BF_RATES[0].name;
    }
    if (vehicleInput) {
        window.bfCurrent = vehicleInput.value || BF_RATES[0].name;
    }

    bfBuildDropdowns();

    var dateEl = document.getElementById('bfDate');
    if (dateEl) {
        var today = new Date().toISOString().split('T')[0];
        dateEl.min = today;
        if (!dateEl.value) dateEl.value = today;
    }

    // If page loaded with baby seat already on (POST error re-render),
    // sync the child age fields to the pre-populated seat count.
    var seatSel = document.getElementById('bfNumSeats');
    if (seatSel && parseInt(seatSel.value, 10) > 0) {
        bfUpdateChildAgeFields(seatSel.value, window.BF_CHILD_AGES || []);
    }

    // Wire baby seat toggle to show/hide child panel (in addition to the generic toggle)
    var babyCb = document.getElementById('bfBabySeatCb');
    if (babyCb) {
        babyCb.addEventListener('change', function () {
            bfSyncChildPanel();
        });
    }
})();


/* ── Show / hide the child fields panel ─────────────────────── */
function bfSyncChildPanel() {
    var cb     = document.getElementById('bfBabySeatCb');
    var panel  = document.getElementById('bfChildFields');
    var seatSel = document.getElementById('bfNumSeats');
    if (!cb || !panel) return;

    if (cb.checked) {
        panel.style.display = '';
        // If no seats chosen yet, focus the selector
        if (seatSel && parseInt(seatSel.value, 10) === 0) {
            seatSel.focus();
        }
    } else {
        panel.style.display = 'none';
        // Clear age fields and reset selector
        if (seatSel) seatSel.value = '0';
        bfClearChildAgeFields();
    }
}


/* ── Child age field builder ─────────────────────────────────── */
/**
 * Called when the "Number of Seats" selector changes.
 * Rebuilds the per-child age inputs for exactly `n` children.
 * Existing values are preserved when count increases.
 *
 * @param {string|number} n       - number of seats selected
 * @param {string[]}      [seed]  - optional array of pre-filled age strings
 */
window.bfUpdateChildAgeFields = function (n, seed) {
    n = parseInt(n, 10) || 0;
    var container = document.getElementById('bfChildAgeFields');
    if (!container) return;

    // Collect current values before re-render so we don't lose what user typed
    var existing = [];
    container.querySelectorAll('input[name^="child_age_"]').forEach(function (inp) {
        existing.push(inp.value);
    });

    // Use seed array (from server-rendered data) only on first call
    var values = seed || existing;

    // Clear and rebuild
    container.innerHTML = '';

    if (n === 0) return;

    for (var i = 1; i <= n; i++) {
        var prefill = (values[i - 1] !== undefined) ? values[i - 1] : '';

        var row = document.createElement('div');
        row.className  = 'bf__child-age-row';
        row.dataset.child = i;

        var fieldDiv = document.createElement('div');
        fieldDiv.className = 'bf__f';

        var label = document.createElement('label');
        label.setAttribute('for', 'bfChildAge' + i);
        label.innerHTML =
            'Age of Child ' + i +
            ' <small style="text-transform:none;letter-spacing:0;font-weight:300;color:var(--bf-ink-muted);">(optional)</small>';

        var input = document.createElement('input');
        input.type        = 'text';
        input.id          = 'bfChildAge' + i;
        input.name        = 'child_age_' + i;
        input.placeholder = 'e.g. 7 months or 3 years';
        input.maxLength   = 30;
        input.value       = prefill;
        input.setAttribute('aria-label', 'Age of child ' + i);

        var help = document.createElement('span');
        help.className = 'bf__help';
        help.innerHTML =
            '<svg width="11" height="11" viewBox="0 0 12 12" fill="none" aria-hidden="true">' +
            '<circle cx="6" cy="6" r="5" stroke="#a09890" stroke-width="1.2"/>' +
            '<path d="M6 5v3M6 3.5v.5" stroke="#a09890" stroke-width="1.2" stroke-linecap="round"/>' +
            '</svg> Children accepted up to 10 years old';

        fieldDiv.appendChild(label);
        fieldDiv.appendChild(input);
        fieldDiv.appendChild(help);
        row.appendChild(fieldDiv);
        container.appendChild(row);
    }
};


function bfClearChildAgeFields() {
    var container = document.getElementById('bfChildAgeFields');
    if (container) container.innerHTML = '';
}


/* ── Vehicle card selection ─────────────────────────────────── */
window.bfPick = function (card) {
    document.querySelectorAll('.bf__vc').forEach(function (c) { c.classList.remove('sel'); });
    card.classList.add('sel');
    window.bfCurrent = card.dataset.name;
    var inp = document.getElementById('bfVehicleInput');
    if (inp) inp.value = window.bfCurrent;
    bfBuildDropdowns();
};

/* ── Get current rate object ─────────────────────────────────── */
function bfCurrentRate() {
    for (var i = 0; i < BF_RATES.length; i++) {
        if (BF_RATES[i].name === window.bfCurrent) return BF_RATES[i];
    }
    return BF_RATES[0];
}

/* ── Passenger & bag dropdowns ──────────────────────────────── */
function bfBuildDropdowns() {
    var rate = bfCurrentRate();
    if (!rate) return;

    var pSel = document.getElementById('bfPassSel');
    var bSel = document.getElementById('bfBagSel');
    if (!pSel || !bSel) return;

    var curP = parseInt(pSel.value, 10) || window.BF_DEFAULT_PASS || 2;
    var curB = parseInt(bSel.value, 10) || window.BF_DEFAULT_BAGS || 2;

    pSel.innerHTML = '';
    bSel.innerHTML = '';

    for (var p = 1; p <= rate.maxP; p++) {
        var op = document.createElement('option');
        op.value = p;
        op.textContent = p === 1 ? '1 Passenger' : p + ' Passengers';
        if (p === Math.min(curP, rate.maxP)) op.selected = true;
        pSel.appendChild(op);
    }
    for (var b = 0; b <= rate.maxB; b++) {
        var ob = document.createElement('option');
        ob.value = b;
        ob.textContent = b === 0 ? '0 Bags' : b === 1 ? '1 Bag' : b + ' Bags';
        if (b === Math.min(curB, rate.maxB)) ob.selected = true;
        bSel.appendChild(ob);
    }
}

window.bfPassChange = function () {
    var p       = parseInt(document.getElementById('bfPassSel').value, 10);
    var curIdx  = BF_RATES.findIndex(function (r) { return r.name === window.bfCurrent; });
    var needed  = BF_RATES.find(function (r) { return r.maxP >= p; });
    if (needed && BF_RATES.indexOf(needed) > curIdx) {
        bfUpgrade(needed, p + ' passengers require a larger vehicle.');
    }
};

window.bfBagChange = function () {
    var b       = parseInt(document.getElementById('bfBagSel').value, 10);
    var curIdx  = BF_RATES.findIndex(function (r) { return r.name === window.bfCurrent; });
    var needed  = BF_RATES.find(function (r) { return r.maxB >= b; });
    if (needed && BF_RATES.indexOf(needed) > curIdx) {
        bfUpgrade(needed, b + ' bags require a larger vehicle.');
    }
};

function bfUpgrade(rate, msg) {
    document.querySelectorAll('.bf__vc').forEach(function (c) {
        c.classList.toggle('sel', c.dataset.name === rate.name);
    });
    window.bfCurrent = rate.name;
    var inp = document.getElementById('bfVehicleInput');
    if (inp) inp.value = window.bfCurrent;

    var noteEl = document.getElementById('bfUpNote');
    var textEl = document.getElementById('bfUpText');
    if (textEl) textEl.textContent = msg;
    if (noteEl) {
        noteEl.classList.add('show');
        setTimeout(function () { noteEl.classList.remove('show'); }, 4000);
    }
    bfBuildDropdowns();
}

/* ── Generic toggle switch ───────────────────────────────────── */
window.bfToggle = function (divId, cbId) {
    var div = document.getElementById(divId);
    var cb  = document.getElementById(cbId);
    if (!div || !cb) return;
    div.classList.toggle('on');
    cb.checked = div.classList.contains('on');
    div.setAttribute('aria-checked', cb.checked ? 'true' : 'false');

    // Extra: if this is the baby seat toggle, sync the child panel
    if (cbId === 'bfBabySeatCb') {
        bfSyncChildPanel();
    }
};

/* ── Google Places autocomplete ─────────────────────────────── */
function bfSetupAC(inputEl, listEl) {
    if (!inputEl || !listEl) return;
    var svc = null, items = [], hi = -1;

    function getService() {
        if (!svc && window.google && window.google.maps && window.google.maps.places) {
            svc = new window.google.maps.places.AutocompleteService();
        }
        return svc;
    }

    inputEl.addEventListener('input', function () {
        var v = inputEl.value.trim();
        if (v.length < 3) { listEl.classList.remove('open'); return; }
        var s = getService();
        if (!s) return;
        s.getPlacePredictions(
            { input: v, componentRestrictions: { country: 'au' } },
            function (preds, status) {
                if (status !== window.google.maps.places.PlacesServiceStatus.OK || !preds) {
                    listEl.classList.remove('open'); return;
                }
                items = preds; hi = -1;
                listEl.innerHTML = preds.map(function (p, i) {
                    return '<div class="bf__aci" data-i="' + i + '">' +
                        '<svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">' +
                        '<path d="M7 1C4.791 1 3 2.791 3 5c0 3 4 8 4 8s4-5 4-8c0-2.209-1.791-4-4-4z"' +
                        ' stroke="#b8902e" stroke-width="1.2" fill="none"/>' +
                        '<circle cx="7" cy="5" r="1.3" fill="#b8902e"/></svg>' +
                        '<span>' + p.description + '</span></div>';
                }).join('');
                listEl.classList.add('open');
            }
        );
    });

    listEl.addEventListener('click', function (e) {
        var it = e.target.closest('.bf__aci');
        if (!it) return;
        inputEl.value = items[parseInt(it.dataset.i, 10)].description;
        listEl.classList.remove('open');
    });

    inputEl.addEventListener('keydown', function (e) {
        var rows = listEl.querySelectorAll('.bf__aci');
        if (e.key === 'ArrowDown') {
            hi = Math.min(hi + 1, rows.length - 1); bfHL(rows); e.preventDefault();
        } else if (e.key === 'ArrowUp') {
            hi = Math.max(hi - 1, -1); bfHL(rows); e.preventDefault();
        } else if (e.key === 'Enter' && hi >= 0) {
            inputEl.value = items[hi].description;
            listEl.classList.remove('open'); e.preventDefault();
        } else if (e.key === 'Escape') {
            listEl.classList.remove('open');
        }
    });

    document.addEventListener('click', function (e) {
        if (!inputEl.contains(e.target) && !listEl.contains(e.target)) {
            listEl.classList.remove('open');
        }
    });

    function bfHL(rows) {
        rows.forEach(function (r, i) { r.classList.toggle('hi', i === hi); });
    }
}

/* Called by Google Maps script callback */
window.bfMapsReady = function () {
    if (!window.BF_LOCK_PICKUP) {
        bfSetupAC(document.getElementById('bfPickup'), document.getElementById('bfPickupList'));
    }
    // Destination & stop only for non-hourly service types
    if (!window.BF_IS_HOURLY) {
        if (!window.BF_LOCK_DEST) {
            bfSetupAC(document.getElementById('bfDest'), document.getElementById('bfDestList'));
        }
        bfSetupAC(document.getElementById('bfStop'), document.getElementById('bfStopList'));
    }
};

/* ── Submit: loading state ───────────────────────────────────── */
(function () {
    var form = document.getElementById('bfForm');
    if (!form) return;

    form.addEventListener('submit', function () {
        var btn     = document.getElementById('bfSubmit');
        var spinner = document.getElementById('bfSpin');
        var arrow   = document.getElementById('bfBtnArrow');
        var txtEl   = document.getElementById('bfBtnTxt');
        if (btn) btn.disabled = true;
        if (spinner) spinner.style.display = 'block';
        if (arrow)   arrow.style.display   = 'none';
        if (window.BF_IS_HOURLY) {
            if (txtEl) txtEl.innerHTML = 'Opening WhatsApp\u2026';
        } else {
            if (txtEl) txtEl.textContent = 'Calculating route\u2026';
        }
    });
})();
