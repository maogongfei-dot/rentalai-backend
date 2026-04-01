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

    if (!s.isAuthenticated) {
      return {
        mode: "guest",
        bucketId: bid,
        userId: null,
        email: null,
        authMode: null,
        title: "访客 · guest 历史",
        detail:
          "以下为 guest 桶，仅本机。登录后历史与账号绑定，便于区分个人记录（仍本地存储）。",
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
        "以下为与当前会话绑定的本地历史（分桶 id：" + String(bid) + "）。",
    };
  }

  /** 单行摘要，供顶栏或调试 */
  function getCurrentHistoryBucketLabel() {
    var st = resolveHistoryAccessState();
    if (st.mode === "guest") return "Guest 历史（guest 桶）";
    return "已登录：" + (st.email || st.userId || st.bucketId);
  }

  function renderBannerHtml() {
    var st = resolveHistoryAccessState();
    if (st.mode === "guest") {
      return (
        '<p class="history-access-banner-lead"><strong>访客模式</strong>：正在查看 <code class="history-bucket-code">guest</code> 桶；可照常使用，数据仅本机。</p>' +
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

  function applyBannerById(elementId) {
    var el = document.getElementById(elementId);
    if (!el) return;
    el.className = bannerClass();
    el.innerHTML = renderBannerHtml();
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
