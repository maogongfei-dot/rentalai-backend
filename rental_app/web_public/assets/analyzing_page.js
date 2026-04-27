/**
 * Phase 5 Step 12: front-end only analyzing transition page.
 */
(function () {
  var REDIRECT_MS = 2000;

  document.addEventListener("DOMContentLoaded", function () {
    var statusEl = document.getElementById("analyzing-status-text");
    window.setTimeout(function () {
      if (statusEl) statusEl.textContent = "Done. Opening your result...";
    }, Math.max(500, REDIRECT_MS - 700));

    window.setTimeout(function () {
      window.location.assign("/result");
    }, REDIRECT_MS);
  });
})();
