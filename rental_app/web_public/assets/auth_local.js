/**
 * 本地假登录 v1：current_user 存 localStorage，无后端鉴权。
 * 页面登录检查：非 /login 且无 current_user 则跳转 /login。
 * Demo 收口：统一顶部导航（Phase 4 第五轮：首页 / 房源分析 / 合同分析并列主入口，见 renderUnifiedNav）。
 */
(function (global) {
  var KEY = "current_user";

  function getUser() {
    try {
      var raw = localStorage.getItem(KEY);
      if (!raw) return null;
      var o = JSON.parse(raw);
      if (!o || !o.user_id) return null;
      return o;
    } catch (e) {
      return null;
    }
  }

  /** 收藏按用户隔离：fav_list_{user_id} */
  function favStorageKey() {
    var u = getUser();
    if (!u || !u.user_id) return "fav_list";
    return "fav_list_" + u.user_id;
  }

  function requireLogin() {
    var path = (window.location.pathname || "").replace(/\/$/, "") || "/";
    if (path === "/login") return;
    if (!getUser()) {
      window.location.replace("/login");
    }
  }

  function logout() {
    localStorage.removeItem(KEY);
    window.location.href = "/login";
  }

  function escapeHtml(s) {
    var d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  /** 各业务页共用的顶部导航：首页 / 两条主流程 / 历史 / 对比 / 用户 / 退出 */
  function renderUnifiedNav() {
    var nav = document.getElementById("demo-unified-nav");
    if (!nav) return;
    var u = getUser();
    var name = u ? escapeHtml(String(u.display_name || u.user_id || "用户")) : "—";
    nav.innerHTML =
      '<a href="/">首页</a>' +
      '<span class="nav-sep">·</span>' +
      '<a href="/#ai-rental-heading">房源分析</a>' +
      '<span class="nav-sep">·</span>' +
      '<a href="/contract-analysis">合同分析</a>' +
      '<span class="nav-sep">·</span>' +
      '<a href="/history">历史记录</a>' +
      '<span class="nav-sep">·</span>' +
      '<a href="/compare">房源对比</a>' +
      '<span class="nav-sep">·</span>' +
      '<span class="local-user-name">当前用户：' +
      name +
      "</span>" +
      '<span class="nav-sep">·</span>' +
      '<button type="button" class="local-logout-btn">退出登录</button>';
    var btn = nav.querySelector(".local-logout-btn");
    if (btn) btn.addEventListener("click", logout);
  }

  /** Demo：清空本地测试数据（仅当前用户相关项 + 当前分析缓存，不误删其它 localStorage 键） */
  function initDemoClearStorage() {
    var btn = document.getElementById("demo-clear-storage-btn");
    if (!btn) return;
    btn.addEventListener("click", function () {
      if (!confirm("确定清空本地测试数据？将退出登录。")) return;
      var favKey = favStorageKey();
      var uid = (getUser() || {}).user_id;
      try {
        sessionStorage.removeItem("ai_analyze_last");
        sessionStorage.removeItem("history_current");
      } catch (e) {}
      try {
        localStorage.removeItem(favKey);
        var rawHist = localStorage.getItem("analysis_history");
        if (rawHist && uid) {
          var arr = JSON.parse(rawHist);
          if (Array.isArray(arr)) {
            var kept = arr.filter(function (x) {
              return !x || x.user_id !== uid;
            });
            localStorage.setItem("analysis_history", JSON.stringify(kept));
          }
        } else if (rawHist && !uid) {
          localStorage.removeItem("analysis_history");
        }
      } catch (e) {
        try {
          localStorage.removeItem("analysis_history");
        } catch (e2) {}
      }
      try {
        localStorage.removeItem(KEY);
      } catch (e) {}
      window.location.href = "/login";
    });
  }

  function initDemoChrome() {
    function run() {
      renderUnifiedNav();
      initDemoClearStorage();
    }
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", run);
    } else {
      run();
    }
  }

  global.RentalAILocalAuth = {
    getUser: getUser,
    requireLogin: requireLogin,
    logout: logout,
    favStorageKey: favStorageKey,
  };

  requireLogin();
  initDemoChrome();
})(window);
