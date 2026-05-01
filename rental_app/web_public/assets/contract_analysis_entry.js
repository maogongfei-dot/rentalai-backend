/**
 * Contract analysis entry — POST /analyze (same shape as analyzing.html), then sessionStorage + /ai-result.
 */
(function () {
  var ta = document.getElementById("contract-entry-text");
  var btn = document.getElementById("contract-entry-submit");
  var errEl = document.getElementById("contract-entry-error");

  if (!btn) return;

  function setError(msg) {
    if (!errEl) return;
    if (!msg) {
      errEl.textContent = "";
      errEl.classList.add("hidden");
      return;
    }
    errEl.textContent = msg;
    errEl.classList.remove("hidden");
  }

  function attachLoggedInUserId(base) {
    try {
      if (
        sessionStorage.getItem("rentalai_login_status") === "logged_in" &&
        sessionStorage.getItem("rentalai_user_id")
      ) {
        var uid = String(sessionStorage.getItem("rentalai_user_id") || "").trim();
        if (uid) base.user_id = uid;
      }
    } catch (e2) {}
    return base;
  }

  /**
   * 与 web_public/analyzing.html buildAnalyzeBody 一致：默认房源字段 + area = 用户文本（合同全文）。
   */
  function buildAnalyzeBody(contractText) {
    var base = {
      rent: 1250,
      budget: 1500,
      commute_minutes: 30,
      bedrooms: 1,
      bills_included: false,
      postcode: "M1",
      area: (contractText || "").trim(),
    };
    return attachLoggedInUserId(base);
  }

  function goError() {
    window.location.href = "/analysis-error";
  }

  function goSuccess(response) {
    var payload =
      response && response.data !== undefined && response.data !== null
        ? response.data
        : response;
    try {
      if (payload !== undefined && payload !== null) {
        sessionStorage.setItem("rentalai_result", JSON.stringify(payload));
      }
    } catch (e0) {}
    try {
      var data = response;
      localStorage.setItem("rentalai_latest_result_v1", JSON.stringify(data));
      sessionStorage.setItem("rentalai_direct_analyze_result_v1", JSON.stringify(data));
    } catch (e) {
      goError();
      return;
    }
    window.location.href = "/ai-result";
  }

  function runAnalyze() {
    setError("");
    var text = ta && ta.value ? String(ta.value).trim() : "";
    if (!text) {
      setError("Please paste your contract text or concerns before analyzing.");
      return;
    }

    btn.disabled = true;
    btn.setAttribute("aria-busy", "true");
    var init = {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(buildAnalyzeBody(text)),
    };
    if (typeof window.rentalaiMergeAuthHeaders === "function") {
      init.headers = window.rentalaiMergeAuthHeaders(init.headers);
    }

    var req =
      typeof window.rentalaiApiFetch === "function"
        ? window.rentalaiApiFetch("/analyze", init)
        : fetch(
            typeof window.rentalaiApiUrl === "function"
              ? window.rentalaiApiUrl("/analyze")
              : "/analyze",
            init
          );

    req
      .then(function (r) {
        if (!r.ok) throw new Error("analyze_http_" + r.status);
        return r.json();
      })
      .then(function (body) {
        if (body && body.success === false) {
          btn.disabled = false;
          btn.setAttribute("aria-busy", "false");
          goError();
          return;
        }
        goSuccess(body);
      })
      .catch(function () {
        btn.disabled = false;
        btn.setAttribute("aria-busy", "false");
        goError();
      });
  }

  btn.addEventListener("click", runAnalyze);
})();
