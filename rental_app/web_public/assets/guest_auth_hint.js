/**
 * Phase 5 Round2 Step3 — 轻量访客提示（AuthHintBanner），不弹窗、不强制登录。
 * 依赖 RentalAIUserStore；挂载点由页面提供空 div。
 * 能力边界见 rental_app/README.md「Phase 5 第二轮」。
 */
(function (global) {
  function isGuest() {
    try {
      if (global.RentalAIUserStore && typeof global.RentalAIUserStore.loadUserFromStorage === "function") {
        return !global.RentalAIUserStore.loadUserFromStorage().isAuthenticated;
      }
    } catch (e) {}
    return true;
  }

  /** 两段式产品文案：guest 可用 + 登录保留个人历史 + 本机范围 */
  function htmlBanner() {
    return (
      '<div class="auth-hint-banner auth-hint-banner--guest" role="note">' +
      '<p class="auth-hint-banner-lead">' +
      "<strong>访客可用</strong>：分析照常使用；记录仅保存在本机浏览器。" +
      "</p>" +
      '<p class="hint muted auth-hint-banner-sub">' +
      '<a href="/login">登录</a> 后按账号保留<strong>个人</strong>历史（仍存本机；换设备需后续同步）。' +
      ' <a href="/account">账户</a> 页可查看当前分桶。' +
      "</p>" +
      "</div>"
    );
  }

  /** @param {string} elementId */
  function mount(elementId) {
    var el = document.getElementById(elementId);
    if (!el || !isGuest()) return;
    el.innerHTML = htmlBanner();
  }

  global.RentalAIAuthHint = {
    isGuest: isGuest,
    htmlBanner: htmlBanner,
    mount: mount,
  };
})(window);
