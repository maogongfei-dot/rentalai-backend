/*
 * Phase11 Step2-1：首页房源分析 — 结构化字段 + Additional details 合并为 user_text，
 * 写入 sessionStorage 后跳转 /analyzing → POST /analyze（analyzing.html 不变）。
 * DOM：#ai-field-*、#ai-query、#ai-go；assistant 预填见 consumeAssistantHandoff（仅 #ai-query）。
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

  function fieldVal(id) {
    var el = document.getElementById(id);
    return el ? String(el.value || "").trim() : "";
  }

  function hasAnyPropertyInput() {
    if (fieldVal("ai-field-rent")) return true;
    if (fieldVal("ai-field-location")) return true;
    if (fieldVal("ai-field-bedrooms")) return true;
    if (fieldVal("ai-field-bills")) return true;
    if (fieldVal("ai-field-concerns")) return true;
    if ((ta.value || "").trim()) return true;
    return false;
  }

  function buildMergedUserText() {
    var lines = [];
    var rent = fieldVal("ai-field-rent");
    var loc = fieldVal("ai-field-location");
    var beds = fieldVal("ai-field-bedrooms");
    var bills = fieldVal("ai-field-bills");
    var concerns = fieldVal("ai-field-concerns");
    var extra = (ta.value || "").trim();
    if (rent) lines.push("Monthly rent: " + rent);
    if (loc) lines.push("Location / postcode: " + loc);
    if (beds) lines.push("Bedrooms: " + beds);
    if (bills) lines.push("Bills included: " + bills);
    if (concerns) lines.push("Contract or property concerns: " + concerns);
    if (extra) lines.push("Additional details: " + extra);
    return lines.join("\n");
  }

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
    if (!hasAnyPropertyInput()) {
      showErr("Please enter some property details before analysis.", { noRetry: true });
      try {
        document.getElementById("ai-field-rent").focus();
      } catch (ef) {
        try {
          ta.focus();
        } catch (ef2) {}
      }
      return;
    }
    clearErr();
    hideLoading();
    var merged = buildMergedUserText();
    try {
      sessionStorage.setItem(PENDING_KEY, JSON.stringify({ user_text: merged }));
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
