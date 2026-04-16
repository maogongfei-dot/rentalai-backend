/*
 * P10-4：AI 首页，POST /api/ai/query，sessionStorage ai_housing_query_last，跳转 /ai-result
 * P10-4-3：loading、error、重试
 *
 * 推定主提交链路：用于 index.html 房源分析区，绑定 DOM：井号 ai-query、井号 ai-go
 * 角色：当前主产品下由本脚本发起对路径 api/ai/query 的 POST，即 RentAI 主分析链路的 HTTP 侧
 * ShortRentAI：后续短租或合租分支宜复用本 fetch 或扩展请求体，避免平行再造一套提交流程
 * 本文件未包含其它备用或注释掉的 API 路径；主接口路径为 /api/ai/query（经 rentalaiApiUrl 拼绝对 URL）
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

  /*
   * Phase 4 Round7：智能入口（/assistant）一次性预填井号 ai-query，见 assistant_prefill.js
   * 旁路：仅填文案与滚动，不发起分析；真正提交走下方 submit
   */
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
            "已从「智能入口」带入描述，可编辑后点击「开始分析」（不会自动提交）。";
          hint.classList.remove("hidden");
        }
      }
      var h = document.getElementById("ai-rental-heading");
      if (h && text) {
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

  /*
   * 主产品需求提交入口：点击「开始分析」或文本框 Enter（无 Shift）
   * 进入 RentAI 主分析，后端编排 run_housing_ai_query
   */
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
    // 主后端：POST，路径 api/ai/query，对应 api_server 中 api_ai_query；rentalaiApiUrl 仅拼部署前缀
    // 前端到主分析 API 的关键链路；勿擅自改为测试 URL
    var url =
      typeof window.rentalaiApiUrl === "function"
        ? window.rentalaiApiUrl("/api/ai/query")
        : "/api/ai/query";

    var body = { user_text: q };
    try {
      var P = window.RentalAIAnalysisHistoryPersist;
      if (P && typeof P.getHistoryUserIdForApi === "function") {
        var uid = P.getHistoryUserIdForApi();
        if (uid) body.userId = uid;
      }
    } catch (eUid) {}

    var headers = { "Content-Type": "application/json" };
    if (typeof window.rentalaiMergeAuthHeaders === "function") {
      headers = window.rentalaiMergeAuthHeaders(headers);
    } else {
      try {
        var P2 = window.RentalAIAnalysisHistoryPersist;
        if (P2 && typeof P2.mergeAuthHeadersForFetch === "function") {
          headers = P2.mergeAuthHeadersForFetch(headers);
        }
      } catch (eH) {}
    }
    if (typeof window.rentalaiDebugAuthLog === "function") {
      window.rentalaiDebugAuthLog("POST /api/ai/query", url, !!headers["Authorization"]);
    }
    var cred =
      typeof window.rentalaiDefaultFetchCredentials === "function"
        ? window.rentalaiDefaultFetchCredentials()
        : "same-origin";

    // 连接主后端分析接口；ShortRentAI、信任等扩展宜经同一 API 返回字段或由后端分流，在此处统一接 JSON
    fetch(url, {
      method: "POST",
      headers: headers,
      body: JSON.stringify(body),
      credentials: cred,
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
        /*
         * 成功：将分析 JSON 写入 sessionStorage，再跳转到 /ai-result
         * 本文件不渲染列表；展示由 ai-result 页读取键 ai_housing_query_last
         * 后续可在同一 payload 接 RentAI、ShortRentAI、信任等扩展字段
         */
        try {
          if (
            data &&
            data.history_write &&
            data.history_write.success &&
            window.RentalAIAnalysisHistoryPersist &&
            typeof window.RentalAIAnalysisHistoryPersist.markCloudHistoryNeedsRefresh === "function"
          ) {
            window.RentalAIAnalysisHistoryPersist.markCloudHistoryNeedsRefresh();
          }
        } catch (eMark) {}
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

  // 主入口：「开始分析」按钮，需求提交，RentAI 主分析
  btn.addEventListener("click", submit);
  // 重试：同一 POST api/ai/query，非独立测试接口
  if (retryBtn) retryBtn.addEventListener("click", submit);
  // Enter（无 Shift）：与「开始分析」同一条提交链路
  ta.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  });
})();
