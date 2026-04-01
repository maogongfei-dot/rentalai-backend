/**
 * 本地假登录 + Phase 5：会话判定委托 RentalAIUserStore（auth_user_store.js）。
 * 公开页：/、/login、/register、/assistant；其余路径无会话则跳转 /login。
 */
(function (global) {
  var KEY = "current_user";
  var BEARER_KEY = "rentalai_bearer";
  var EMAIL_KEY = "rentalai_user_email";
  var UID_KEY = "rentalai_user_id";

  function getUser() {
    if (
      global.RentalAIUserStore &&
      typeof global.RentalAIUserStore.loadUserFromStorage === "function"
    ) {
      var s = global.RentalAIUserStore.loadUserFromStorage();
      if (!s.isAuthenticated) return null;
      return {
        user_id: s.userId,
        display_name: s.displayName || s.email || s.userId || "用户",
        email: s.email || undefined,
        auth_bearer: s.authMode === "bearer",
      };
    }
    try {
      var raw = localStorage.getItem(KEY);
      if (raw) {
        var o = JSON.parse(raw);
        if (o && o.user_id) return o;
      }
      var token = localStorage.getItem(BEARER_KEY);
      var email = localStorage.getItem(EMAIL_KEY);
      var uid = localStorage.getItem(UID_KEY);
      if (token && (email || uid)) {
        return {
          user_id: uid || email || "session",
          display_name: email || uid || "用户",
          auth_bearer: true,
        };
      }
    } catch (e) {}
    return null;
  }

  function loadUserState() {
    if (global.RentalAIUserStore && global.RentalAIUserStore.loadUserFromStorage) {
      return global.RentalAIUserStore.loadUserFromStorage();
    }
    var u = getUser();
    if (!u) {
      return {
        isAuthenticated: false,
        userId: null,
        email: null,
        displayName: null,
        authMode: null,
      };
    }
    return {
      isAuthenticated: true,
      userId: u.user_id,
      email: u.email || null,
      displayName: u.display_name || u.user_id,
      authMode: u.auth_bearer ? "bearer" : "local_demo",
    };
  }

  /** 收藏按用户隔离：fav_list_{user_id} */
  function favStorageKey() {
    var u = getUser();
    if (!u || !u.user_id) return "fav_list";
    return "fav_list_" + u.user_id;
  }

  function requireLogin() {
    var path = (window.location.pathname || "").replace(/\/$/, "") || "/";
    var publicPaths = [
      "/",
      "/login",
      "/register",
      "/assistant",
      "/ai-result",
      "/analysis-history",
      "/history",
    ];
    if (publicPaths.indexOf(path) !== -1) return;
    if (!getUser()) {
      window.location.replace("/login");
    }
  }

  function logout() {
    if (global.RentalAIUserStore && typeof global.RentalAIUserStore.logoutUser === "function") {
      global.RentalAIUserStore.logoutUser({ redirect: true });
      return;
    }
    window.location.href = "/login";
  }

  function escapeHtml(s) {
    var d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  /** 各业务页共用的顶部导航：未登录时显示 登录/注册；已登录显示用户与退出 */
  function renderUnifiedNav() {
    var nav = document.getElementById("demo-unified-nav");
    if (!nav) return;
    var u = getUser();
    if (!u) {
      nav.innerHTML =
        '<a href="/">首页</a>' +
        '<span class="nav-sep">·</span>' +
        '<a href="/assistant">智能入口</a>' +
        '<span class="nav-sep">·</span>' +
        '<a href="/#ai-rental-heading">房源分析</a>' +
        '<span class="nav-sep">·</span>' +
        '<a href="/contract-analysis">合同分析</a>' +
        '<span class="nav-sep">·</span>' +
        '<a href="/analysis-history">分析历史</a>' +
        '<span class="nav-sep">·</span>' +
        '<a href="/compare">房源对比</a>' +
        '<span class="nav-sep">·</span>' +
        '<a href="/login">登录</a>' +
        '<span class="nav-sep">·</span>' +
        '<a href="/register">注册</a>';
      return;
    }
    var email = u.email ? String(u.email) : "";
    var mainLabel = email
      ? "已登录：" + escapeHtml(email)
      : "当前用户：" + escapeHtml(String(u.display_name || u.user_id || "用户"));
    nav.innerHTML =
      '<a href="/">首页</a>' +
      '<span class="nav-sep">·</span>' +
      '<a href="/assistant">智能入口</a>' +
      '<span class="nav-sep">·</span>' +
      '<a href="/#ai-rental-heading">房源分析</a>' +
      '<span class="nav-sep">·</span>' +
      '<a href="/contract-analysis">合同分析</a>' +
      '<span class="nav-sep">·</span>' +
      '<a href="/analysis-history">分析历史</a>' +
      '<span class="nav-sep">·</span>' +
      '<a href="/compare">房源对比</a>' +
      '<span class="nav-sep">·</span>' +
      '<span class="local-user-name" title="当前登录状态">' +
      mainLabel +
      "</span>" +
      '<span class="nav-sep">·</span>' +
      '<button type="button" class="local-logout-btn" title="Logout">Logout</button>';
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
      try {
        sessionStorage.removeItem("ai_analyze_last");
        sessionStorage.removeItem("history_current");
      } catch (e) {}
      try {
        localStorage.removeItem(favKey);
        if (global.RentalAIUserStore && global.RentalAIUserStore.getManualHistoryStorageKey) {
          localStorage.removeItem(global.RentalAIUserStore.getManualHistoryStorageKey());
        } else {
          localStorage.removeItem("analysis_history");
        }
        if (
          global.RentalAIAnalysisHistoryStore &&
          typeof global.RentalAIAnalysisHistoryStore.clearCurrentBucket === "function"
        ) {
          global.RentalAIAnalysisHistoryStore.clearCurrentBucket();
        }
      } catch (e) {}
      if (global.RentalAIUserStore && typeof global.RentalAIUserStore.logoutUser === "function") {
        global.RentalAIUserStore.logoutUser({ redirect: true });
        return;
      }
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
    loadUserState: loadUserState,
    requireLogin: requireLogin,
    logout: logout,
    favStorageKey: favStorageKey,
  };

  requireLogin();
  initDemoChrome();
})(window);
