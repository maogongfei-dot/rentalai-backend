/**
 * Phase 5 Step 12: front-end only analyzing transition page.
 */
(function () {
  var RESULT_STORAGE_KEY = "rentalai_latest_result_v1";
  var MIN_LOADING_MS = 2000;
  var SUCCESS_REDIRECT_DELAY_MS = 250;
  var ERROR_REDIRECT_DELAY_MS = 550;
  var MOCK_INPUT = {
    location: "Manchester",
    rent: 1250,
    bedrooms: 1,
    bills: "unclear",
  };

  function persistResult(payload) {
    try {
      localStorage.setItem(RESULT_STORAGE_KEY, JSON.stringify(payload));
    } catch (e) {}
  }

  function nowMs() {
    return Date.now();
  }

  function withMinLoading(startedAtMs, cb) {
    var elapsed = nowMs() - startedAtMs;
    var wait = Math.max(0, MIN_LOADING_MS - elapsed);
    window.setTimeout(cb, wait);
  }

  function requestAnalyzeOnce() {
    var body = {
      rent: MOCK_INPUT.rent,
      bedrooms: MOCK_INPUT.bedrooms,
      area: MOCK_INPUT.location,
      postcode: "M1",
      bills_included: false,
    };
    return fetch("/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(function (r) {
      if (!r.ok) throw new Error("analyze_http_" + r.status);
      return r.json();
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var statusEl = document.getElementById("analyzing-status-text");
    var rootCard = document.querySelector(".analyzing-card");
    var startedAt = nowMs();
    if (rootCard) rootCard.setAttribute("data-analysis-status", "loading");
    if (statusEl) statusEl.textContent = "Analyzing your rental option...";

    requestAnalyzeOnce()
      .then(function (result) {
        persistResult({
          source: "api",
          input: MOCK_INPUT,
          response: result,
          fetched_at: new Date().toISOString(),
        });
        if (rootCard) rootCard.setAttribute("data-analysis-status", "success");
        if (statusEl) statusEl.textContent = "Analysis complete. Opening your result...";
        withMinLoading(startedAt, function () {
          window.setTimeout(function () {
            window.location.assign("/result");
          }, SUCCESS_REDIRECT_DELAY_MS);
        });
      })
      .catch(function () {
        persistResult({
          source: "error",
          input: MOCK_INPUT,
          response: null,
          fetched_at: new Date().toISOString(),
        });
        if (rootCard) rootCard.setAttribute("data-analysis-status", "error");
        if (statusEl) statusEl.textContent = "We couldn't complete the analysis. Redirecting...";
        withMinLoading(startedAt, function () {
          window.setTimeout(function () {
            window.location.assign("/analysis-error");
          }, ERROR_REDIRECT_DELAY_MS);
        });
      });
  });
})();
