/**
 * P10-4：AI 首页 → POST /api/ai/query → sessionStorage ai_housing_query_last → /ai-result
 * P10-4-3：loading / error + 重试
 */
(function () {
  var ta = document.getElementById("ai-query");
  var btn = document.getElementById("ai-go");
  var err = document.getElementById("ai-err");
  var loading = document.getElementById("ai-loading");
  var loadingText = document.getElementById("ai-loading-text");
  var retryRow = document.getElementById("ai-retry-row");
  var retryBtn = document.getElementById("ai-retry");
  if (!btn || !ta) return;

  /** Phase 4 Round7：智能入口跳转后一次性预填 */
  (function applyAssistantPrefill() {
    try {
      var nav = sessionStorage.getItem("rentalai_assistant_navigate");
      if (nav !== "property") return;
      var draft = sessionStorage.getItem("rentalai_assistant_draft");
      if (draft) {
        ta.value = draft;
        ta.focus();
      }
      sessionStorage.removeItem("rentalai_assistant_navigate");
      var h = document.getElementById("ai-rental-heading");
      if (h) {
        h.scrollIntoView({ block: "start", behavior: "smooth" });
      }
    } catch (e) {}
  })();

  var LOADING_MSGS = [
    "Analyzing market...",
    "Finding best deals...",
    "Building recommendation...",
  ];
  var loadingTimer = null;
  var loadingIdx = 0;

  function showErr(msg) {
    if (!err) return;
    err.textContent = msg;
    err.classList.remove("hidden");
    if (retryRow) retryRow.classList.remove("hidden");
  }
  function clearErr() {
    if (!err) return;
    err.classList.add("hidden");
    err.textContent = "";
    if (retryRow) retryRow.classList.add("hidden");
  }

  function showLoading() {
    if (!loading) return;
    loading.classList.remove("hidden");
    loading.setAttribute("aria-busy", "true");
    if (loadingText) {
      loadingIdx = 0;
      loadingText.textContent = LOADING_MSGS[0];
    }
    if (loadingTimer) clearInterval(loadingTimer);
    loadingTimer = setInterval(function () {
      loadingIdx = (loadingIdx + 1) % LOADING_MSGS.length;
      if (loadingText) loadingText.textContent = LOADING_MSGS[loadingIdx];
    }, 1800);
  }

  function hideLoading() {
    if (loadingTimer) {
      clearInterval(loadingTimer);
      loadingTimer = null;
    }
    if (loading) {
      loading.classList.add("hidden");
      loading.setAttribute("aria-busy", "false");
    }
  }

  function setBusy(on) {
    btn.disabled = on;
    ta.disabled = on;
  }

  function submit() {
    var q = (ta.value || "").trim();
    if (!q) {
      showErr("请输入需求后再试（不能只含空格）");
      return;
    }
    clearErr();
    hideLoading();
    showLoading();
    setBusy(true);

    var navigating = false;
    var url =
      typeof window.rentalaiApiUrl === "function"
        ? window.rentalaiApiUrl("/api/ai/query")
        : "/api/ai/query";

    fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_text: q }),
    })
      .then(function (r) {
        return r.text().then(function (text) {
          var body = {};
          try {
            body = text ? JSON.parse(text) : {};
          } catch (e) {
            throw new Error("服务器返回非 JSON（" + r.status + "）");
          }
          if (!r.ok) {
            var msg =
              (body && (body.message || body.detail)) ||
              "Request failed (" + r.status + ")";
            throw new Error(msg);
          }
          return body;
        });
      })
      .then(function (data) {
        try {
          sessionStorage.setItem("ai_housing_query_last", JSON.stringify(data));
        } catch (e) {
          hideLoading();
          showErr("无法保存结果，请检查浏览器是否禁用存储");
          return;
        }
        navigating = true;
        window.location.href = "/ai-result";
      })
      .catch(function (e) {
        hideLoading();
        showErr(e.message || "网络错误，请检查后端是否已启动。");
      })
      .finally(function () {
        if (!navigating) {
          hideLoading();
          setBusy(false);
        }
      });
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
