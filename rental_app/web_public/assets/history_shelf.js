/**
 * P10 Phase3 Step3 — auto-save completed analysis to /records/ui-history (logged-in only).
 */
(function (global) {
  function apiUrl(path) {
    return typeof global.rentalaiApiUrl === "function" ? global.rentalaiApiUrl(path) : path;
  }

  var SAVE_KEY_PREFIX = "rentalai_ui_saved_task_";

  function getToken() {
    var A = global.RentalAIAuth;
    if (!A || typeof A.requireToken !== "function") {
      return Promise.reject(new Error("not_logged_in"));
    }
    return A.requireToken();
  }

  function deriveInputValue(rawTaskState) {
    if (!rawTaskState || typeof rawTaskState !== "object") return "";
    var s = rawTaskState.input_summary;
    if (!s || typeof s !== "object") return "";
    if (s.listing_url) return String(s.listing_url);
    var parts = [];
    if (s.target_postcode) parts.push(String(s.target_postcode));
    if (s.property_type) parts.push(String(s.property_type));
    if (s.bedrooms) parts.push(String(s.bedrooms) + " bed");
    if (s.budget != null && String(s.budget).trim()) parts.push("£" + String(s.budget));
    return parts.length ? parts.join(" · ") : "";
  }

  function setSaveBanner(ok, text) {
    var b = document.getElementById("save-status");
    if (!b) return;
    b.classList.remove("hidden");
    b.classList.remove("save-banner-ok");
    b.classList.remove("save-banner-err");
    b.classList.remove("save-banner-warn");
    b.classList.add(ok ? "save-banner-ok" : "save-banner-err");
    b.textContent = text;
  }

  function setSaveBannerWarn(text) {
    var b = document.getElementById("save-status");
    if (!b) return;
    b.classList.remove("hidden");
    b.classList.remove("save-banner-ok");
    b.classList.remove("save-banner-err");
    b.classList.add("save-banner-warn");
    b.textContent = text;
  }

  function trySaveCompletedResult(vm) {
    if (!vm || vm.phase !== "ready") return;
    var dp = vm.display_payload;
    var tid =
      (dp && dp.task_id) ||
      (vm.raw_task_state && vm.raw_task_state.task_id) ||
      "";
    tid = String(tid).trim();
    if (!tid) return;
    try {
      if (sessionStorage.getItem(SAVE_KEY_PREFIX + tid)) return;
    } catch (e) {
      return;
    }

    var Auth = global.RentalAIAuth;
    if (!Auth || !Auth.isLoggedIn || !Auth.isLoggedIn()) {
      setSaveBannerWarn("You are not logged in. Your analysis will not be saved.");
      return;
    }

    getToken()
      .then(function (token) {
        var body = {
          task_id: tid,
          input_value: deriveInputValue(vm.raw_task_state),
          display_payload: dp || {},
          raw_task_snapshot: vm.raw_task_state || null,
        };
        return fetch(apiUrl("/records/ui-history"), {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: "Bearer " + token,
          },
          body: JSON.stringify(body),
        }).then(function (r) {
          if (!r.ok) return Promise.reject(new Error("save failed"));
          try {
            sessionStorage.setItem(SAVE_KEY_PREFIX + tid, "1");
          } catch (e2) {}
          setSaveBanner(true, "Analysis saved to your history.");
        });
      })
      .catch(function (e) {
        if (e && e.message === "not_logged_in") {
          setSaveBannerWarn("Login to save your analysis history");
          return;
        }
        setSaveBanner(false, "Failed to save analysis record");
      });
  }

  global.RentalAIHistoryShelf = {
    getToken: getToken,
    trySaveCompletedResult: trySaveCompletedResult,
  };
})(window);
