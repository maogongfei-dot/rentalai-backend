/*
 * Phase11：首页房源分析区 — 写入 sessionStorage 后跳转 /analyzing，由 analyzing.html POST /analyze，
 * 结果写入 rentalai_result 并跳转 /ai-result（与 Phase10 结果页对齐）。
 * DOM：#ai-query、#ai-go；assistant 预填见 consumeAssistantHandoff。
 */
(function () {
  var ta = document.getElementById("ai-query");
  var btn = document.getElementById("ai-go");
  var err = document.getElementById("ai-err");
  var loading = document.getElementById("ai-loading");
  var retryRow = document.getElementById("ai-retry-row");
  var retryBtn = document.getElementById("ai-retry");
  if (!btn || !ta) return;

  var PENDING_KEY = "rentalai_analyze_pending_v1";

  (function applyAssistantPrefill() {
    try {
      var P = window.RentalAIAssistantPrefill;
      if (!P || typeof P.consumeAssistantHandoff !== "function") return;
      var handoff = P.consumeAssistantHandoff("property");
      if (!handoff) return;
      var raw = handoff.draft;
      var text = raw != null ? String(raw).trim() : "";
      if (text) {
        ta.value = raw;
        ta.focus();
        var hint = document.getElementById("assistant-prefill-hint");
        if (hint) {
          hint.textContent =
            "Draft loaded from Assistant — edit below, then tap Analyze Property (does not auto-submit).";
          hint.classList.remove("hidden");
        }
      }
      var h = document.getElementById("ai-rental-heading");
      if (h && text) {
        h.scrollIntoView({ block: "start", behavior: "smooth" });
      }
    } catch (e) {}
  })();

  function showErr(msg, opts) {
    opts = opts || {};
    if (!err) return;
    err.textContent = msg;
    err.classList.remove("hidden");
    if (retryRow) {
      if (opts.noRetry) retryRow.classList.add("hidden");
      else retryRow.classList.remove("hidden");
    }
  }
  function clearErr() {
    if (!err) return;
    err.classList.add("hidden");
    err.textContent = "";
    if (retryRow) retryRow.classList.add("hidden");
  }

  function hideLoading() {
    if (loading) {
      loading.classList.add("hidden");
      loading.setAttribute("aria-busy", "false");
    }
  }

  function submit() {
    var q = (ta.value || "").trim();
    if (!q) {
      showErr("Please enter some property details before analysis.", { noRetry: true });
      try {
        ta.focus();
      } catch (ef) {}
      return;
    }
    clearErr();
    hideLoading();
    try {
      sessionStorage.setItem(PENDING_KEY, JSON.stringify({ user_text: q }));
    } catch (e) {
      showErr("Could not save your input. Check that browser storage is enabled.");
      return;
    }
    window.location.href = "/analyzing";
  }

  btn.addEventListener("click", submit);
  if (retryBtn) retryBtn.addEventListener("click", submit);
  ta.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  });
})();
