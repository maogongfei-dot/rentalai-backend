/**
 * Phase 5 Round2 Step1：历史页「受保护访问」轻量状态（不拦截路由，仅提示）。
 * 依赖 RentalAIUserStore（guest vs 已登录分桶与 authMode 一致）。
 * 用户体系能力边界：rental_app/README.md「Phase 5 第二轮」。
 */
(function (global) {
  function esc(s) {
    var d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  /**
   * 游客历史：guest、guest:<session> 或本机键 sanitize 后的 guest_…；别再只用 === "guest"。
   * 登录用户与游客历史不合并。
   */
  function isGuestBucket(bucketId) {
    var s = String(bucketId || "").trim();
    return (
      !s ||
      s === "guest" ||
      s.indexOf("guest:") === 0 ||
      s.indexOf("guest_") === 0
    );
  }

  /**
   * @returns {{
   *   mode: "guest"|"logged_in",
   *   bucketId: string,
   *   userId: string|null,
   *   email: string|null,
   *   authMode: string|null,
   *   title: string,
   *   detail: string
   * }}
   */
  function resolveHistoryAccessState() {
    var S = global.RentalAIUserStore;
    var s =
      S && typeof S.loadUserFromStorage === "function"
        ? S.loadUserFromStorage()
        : {
            isAuthenticated: false,
            userId: null,
            email: null,
            authMode: null,
          };
    var bid =
      S && typeof S.getHistoryBucketId === "function" ? S.getHistoryBucketId() : "guest";

    if (!s.isAuthenticated || isGuestBucket(bid)) {
      return {
        mode: "guest",
        bucketId: bid,
        userId: null,
        email: null,
        authMode: null,
        title: "访客 · guest 历史",
        detail:
          "以下为当前访客历史作用域（" +
          String(bid || "guest") +
          "），仅保存在本机/当前游客会话中。登录后将使用账号自己的历史，且不会自动合并游客历史。",
      };
    }

    var mail = s.email || null;
    var uid = s.userId || null;
    var label = mail || uid || "当前账号";
    return {
      mode: "logged_in",
      bucketId: bid,
      userId: uid,
      email: mail,
      authMode: s.authMode || null,
      title: "已登录 · " + label,
      detail:
        "以下为与当前会话绑定的本地分桶（分桶 id：" +
        String(bid) +
        "）；「分析历史」页在登录后优先展示云端同步记录。",
    };
  }

  /** 单行摘要，供顶栏或调试 */
  function getCurrentHistoryBucketLabel() {
    var st = resolveHistoryAccessState();
    if (st.mode === "guest") return "Guest 历史（" + String(st.bucketId || "guest") + "）";
    return "已登录：" + (st.email || st.userId || st.bucketId);
  }

  /**
   * @param {"saved_list"|"unified_analysis"} [page] saved_list=/history；unified_analysis=/analysis-history
   */
  function renderBannerHtml(page) {
    page = page || "saved_list";
    var st = resolveHistoryAccessState();

    if (page === "unified_analysis") {
      if (st.mode === "guest") {
        return (
          '<p class="history-access-banner-lead"><strong>访客 · 本机历史</strong> · <span lang="en">Viewing guest history stored on this device</span></p>' +
          '<p class="hint muted history-access-banner-sub">' +
          "未登录时，下列摘要仅保存在本浏览器，<strong>不会</strong>同步到账户云端。登录后本页将<strong>优先</strong>显示与账号同步的分析记录。" +
          ' <code class="history-bucket-code">' +
          esc(st.bucketId || "guest") +
          "</code> · " +
          '<a href="/login">登录</a> · <a href="/register">注册</a> · <a href="/account">账户</a>' +
          "</p>"
        );
      }
      var who = esc(st.email || st.userId || "当前用户");
      return (
        '<p class="history-access-banner-lead"><strong>已登录 · 账户历史</strong> · <span lang="en">Viewing account history synced to this user</span></p>' +
        '<p class="hint muted history-access-banner-sub">' +
        "下列列表<strong>优先</strong>展示与 <span class=\"history-access-who\">" +
        who +
        "</span> 同步的云端分析记录（失败时回退本机缓存）。桶 <code class=\"history-bucket-code\">" +
        esc(st.bucketId) +
        "</code> · " +
        '<a href="/account">账户</a>' +
        "</p>"
      );
    }

    if (st.mode === "guest") {
      return (
        '<p class="history-access-banner-lead"><strong>访客模式</strong>：正在查看 <code class="history-bucket-code">' +
        esc(st.bucketId || "guest") +
        '</code> 桶；可照常使用，数据仅本机。</p>' +
        '<p class="hint muted history-access-banner-sub">' +
        esc(st.detail) +
        " " +
        '<a href="/login">登录</a> · <a href="/register">注册</a> · <a href="/account">账户</a>' +
        "</p>"
      );
    }
    var who = esc(st.email || st.userId || "当前用户");
    return (
      '<p class="history-access-banner-lead"><strong>已登录</strong>：正在查看与 <span class="history-access-who">' +
      who +
      "</span> 绑定的本地历史（桶 <code class=\"history-bucket-code\">" +
      esc(st.bucketId) +
      "</code>）。</p>" +
      '<p class="hint muted history-access-banner-sub">' +
      esc(st.detail) +
      ' <a href="/account">账户</a>' +
      "</p>"
    );
  }

  function bannerClass() {
    var st = resolveHistoryAccessState();
    return (
      "history-access-banner " +
      (st.mode === "guest" ? "history-access-banner--guest" : "history-access-banner--user")
    );
  }

  /**
   * @param {string} elementId
   * @param {{ page?: "saved_list"|"unified_analysis" }} [options]
   */
  function applyBannerById(elementId, options) {
    var el = document.getElementById(elementId);
    if (!el) return;
    var page =
      options && options.page === "unified_analysis" ? "unified_analysis" : "saved_list";
    el.className = bannerClass();
    el.innerHTML = renderBannerHtml(page);
    el.setAttribute("role", "status");
    el.setAttribute("aria-live", "polite");
  }

  global.RentalAIHistoryAccess = {
    resolveHistoryAccessState: resolveHistoryAccessState,
    getCurrentHistoryBucketLabel: getCurrentHistoryBucketLabel,
    renderBannerHtml: renderBannerHtml,
    bannerClass: bannerClass,
    applyBannerById: applyBannerById,
  };
})(window);
