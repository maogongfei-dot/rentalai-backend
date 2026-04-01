/**
 * /account：从 RentalAIUserStore 渲染基本账户与历史桶信息（只读）。
 * Phase 5 第二轮 Step4/5 — 最小账户体验；能力边界见 rental_app/README.md「Phase 5 第二轮」。
 */
(function () {
  function esc(s) {
    var d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  function run() {
    var root = document.getElementById("account-root");
    if (!root) return;

    var S = window.RentalAIUserStore;
    var s =
      S && typeof S.loadUserFromStorage === "function"
        ? S.loadUserFromStorage()
        : {
            isAuthenticated: false,
            userId: null,
            email: null,
            displayName: null,
            authMode: null,
            authToken: null,
            authType: null,
          };
    var bucket =
      S && typeof S.getHistoryBucketId === "function" ? S.getHistoryBucketId() : "guest";
    var unifiedKey =
      S && typeof S.getUnifiedHistoryStorageKey === "function"
        ? S.getUnifiedHistoryStorageKey()
        : "—";
    var manualKey =
      S && typeof S.getManualHistoryStorageKey === "function"
        ? S.getManualHistoryStorageKey()
        : "—";

    var statusLabel = s.isAuthenticated ? "已登录" : "未登录（访客）";
    var modeLabel =
      s.authMode === "bearer"
        ? "邮箱密码（Bearer）"
        : s.authMode === "local_demo"
          ? "本地演示"
          : "—";
    var authTypeDisp =
      s.isAuthenticated && s.authMode === "bearer" && s.authType
        ? esc(String(s.authType))
        : "—";
    var emailDisp = s.email ? esc(s.email) : "—";
    var uidDisp = s.userId ? esc(String(s.userId)) : "—";
    var bucketDisp = esc(bucket);
    var bindHint = s.isAuthenticated
      ? "「分析历史」在登录后<strong>优先</strong>从云端同步；本机键用于回退与缓存。手动保存列表仍仅保存在本浏览器。"
      : "未登录时分析摘要落在 <strong>guest</strong> 桶、仅本机；登录后「分析历史」优先看账户同步记录（原 guest 不会自动合并）。";

    root.innerHTML =
      '<section class="card form-card account-summary-card">' +
      '<h2 class="section-title" style="font-size:1.05rem">会话信息</h2>' +
      '<dl class="account-dl">' +
      "<dt>Auth status</dt><dd>" +
      esc(statusLabel) +
      "</dd>" +
      "<dt>Session type</dt><dd>" +
      esc(modeLabel) +
      "</dd>" +
      "<dt>Auth type</dt><dd>" +
      authTypeDisp +
      ' <span class="hint muted">（占位，非 token）</span></dd>' +
      "<dt>Email</dt><dd>" +
      emailDisp +
      "</dd>" +
      "<dt>User ID</dt><dd><code class=\"account-code\">" +
      uidDisp +
      "</code></dd>" +
      "<dt>History bucket</dt><dd><code class=\"account-code\">" +
      bucketDisp +
      "</code></dd>" +
      "</dl>" +
      "</section>" +
      '<section class="card account-hint-card">' +
      '<h2 class="section-title" style="font-size:1.05rem">本地历史归属</h2>' +
      "<p class=\"hint account-hint-text\">" +
      bindHint +
      "</p>" +
      '<p class="hint muted small-print account-storage-keys">' +
      "统一摘要键：<code class=\"account-code\">" +
      esc(unifiedKey) +
      "</code><br />" +
      "手动保存键：<code class=\"account-code\">" +
      esc(manualKey) +
      "</code>" +
      "</p>" +
      '<p class="hint small-print account-actions">' +
      '<a href="/analysis-history">分析历史</a> · <a href="/history">保存列表</a> · <a href="/login">登录</a>' +
      "</p>" +
      "</section>";
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run);
  } else {
    run();
  }
})();
