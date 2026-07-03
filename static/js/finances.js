/* ============================================================
   SevenStar Limo — Finance Dashboard
   static/js/finances.js

   Responsibilities (UI only — all data comes from Django):
   · Tab button clicks → update hidden input + submit form
   · Custom panel show/hide
   · Apply button wires date inputs → hidden inputs + submit
   · Timestamp on load
   ============================================================ */

(function () {
  "use strict";

  const $ = (sel) => document.querySelector(sel);

  /* ── DOM refs ── */
  const form        = $("#fin-form");
  const inputTab    = $("#fin-input-tab");
  const inputCFrom  = $("#fin-input-custom-from");
  const inputCTo    = $("#fin-input-custom-to");
  const tabs        = document.querySelectorAll(".fin__tab");
  const customPanel = $("#fin-custom-panel");
  const dateFrom    = $("#fin-from");
  const dateTo      = $("#fin-to");
  const applyBtn    = $("#fin-apply");
  const tsEl        = $("#fin-timestamp");

  /* ── Timestamp ── */
  if (tsEl) {
    tsEl.textContent = "Loaded " + new Date().toLocaleDateString("en-AU", {
      day: "numeric", month: "short", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  }

  /* ── Tab clicks ── */
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const key = tab.dataset.tab;

      if (key === "custom") {
        // Show panel, don't submit yet — wait for Apply
        tabs.forEach((t) => t.classList.remove("active"));
        tab.classList.add("active");
        inputTab.value = "custom";
        customPanel.classList.add("visible");

        // Pre-fill date inputs with today if empty
        if (!dateFrom.value) {
          const today = new Date().toISOString().slice(0, 10);
          dateFrom.value = today;
          dateTo.value   = today;
        }
        return;
      }

      // Non-custom: hide panel, set tab, submit immediately
      customPanel.classList.remove("visible");
      inputTab.value = key;
      inputCFrom.value = "";
      inputCTo.value   = "";
      form.submit();
    });
  });

  /* ── Apply button (custom range) ── */
  if (applyBtn) {
    applyBtn.addEventListener("click", submitCustom);
  }

  /* ── Allow Enter key in date inputs ── */
  [dateFrom, dateTo].forEach((el) => {
    if (el) el.addEventListener("keydown", (e) => {
      if (e.key === "Enter") submitCustom();
    });
  });

  function submitCustom() {
    const from = dateFrom ? dateFrom.value : "";
    const to   = dateTo   ? dateTo.value   : "";
    if (!from || !to) return;
    inputTab.value   = "custom";
    inputCFrom.value = from;
    inputCTo.value   = to;
    form.submit();
  }

})();
