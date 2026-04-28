/**
 * 本地假登录 + Phase 5：会话判定委托 RentalAIUserStore（auth_user_store.js）。
 * 公开页：/、/login、/register、/account、/assistant、/ai-result、/analysis-history、/history；
 * 其余路径无会话则跳转 /login。顶栏 Login·Sign Up / 邮箱·Logout /「账户」见 README「Phase 5 第二轮」。
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
        authToken: null,
        authType: null,
      };
    }
    return {
      isAuthenticated: true,
      userId: u.user_id,
      email: u.email || null,
      displayName: u.display_name || u.user_id,
      authMode: u.auth_bearer ? "bearer" : "local_demo",
      authToken: null,
      authType: null,
    };
  }

  function getGuestSessionIdForFavorites() {
    try {
      if (
        global.RentalAIUserStore &&
        typeof global.RentalAIUserStore.getOrCreateGuestSessionId === "function"
      ) {
        return global.RentalAIUserStore.getOrCreateGuestSessionId();
      }
    } catch (e) {}
    try {
      var raw = localStorage.getItem("guest_session_id");
      if (raw && String(raw).trim()) return String(raw).trim();
    } catch (e2) {}
    return "anonymous";
  }

  function buildGuestFavoriteScopeId() {
    return (
      "guest_" +
      String(getGuestSessionIdForFavorites())
        .replace(/[^a-zA-Z0-9]/g, "")
        .slice(0, 48)
    );
  }

  /**
   * 收藏按当前作用域隔离：
   * - 已登录：fav_list_{user_id}
   * - 未登录：fav_list_guest_<session>
   * 登录用户与游客收藏不合并。
   */
  function favStorageKey() {
    var u = getUser();
    if (!u || !u.user_id) {
      return "fav_list_" + buildGuestFavoriteScopeId();
    }
    return "fav_list_" + u.user_id;
  }

  /** Step9：旧版单一 key fav_list 等 → 当前作用域 fav_list_*；不合并 guest→用户，仅格式迁移。 */
  var LEGACY_LOCAL_FAV_KEYS = ["fav_list"];

  function migrateLocalFavoriteListMarkerKey(scopeKey) {
    var s = String(scopeKey || "default").replace(/[^a-zA-Z0-9:_-]/g, "_");
    if (s.length > 96) s = s.slice(0, 96);
    return "rentalai_fav_ls_migrated_v1__" + s;
  }

  function canonicalListingUrlMigrate(u) {
    var str = String(u || "").trim();
    if (!str) return "";
    try {
      var x = new URL(str);
      var path = x.pathname.replace(/\/+$/, "") || "/";
      return String(x.origin + path + x.search).toLowerCase();
    } catch (e0) {
      return str.toLowerCase().replace(/\/+$/, "");
    }
  }

  /** 与 server favoriteKey 对齐的字符串规范化（本地离线层；无 API 时自用）。 */
  function normalizeLegacyFavoriteEntryToKey(item) {
    if (item == null) return "";
    if (typeof item === "string" || typeof item === "number") {
      var z = String(item).trim();
      if (!z) return "";
      if (z.indexOf("u:") === 0 || z.indexOf("p:") === 0) return z;
      if (/^https?:\/\//i.test(z)) return "u:" + canonicalListingUrlMigrate(z);
      return "p:" + z;
    }
    if (typeof item === "object") {
      var o = item;
      if (o.favoriteKey != null && String(o.favoriteKey).trim()) {
        return normalizeLegacyFavoriteEntryToKey(String(o.favoriteKey).trim());
      }
      var url = (o.listing_url || o.source_url || o.url || "").trim();
      if (url && /^https?:\/\//i.test(url)) return "u:" + canonicalListingUrlMigrate(url);
      var pid = o.property_id != null ? String(o.property_id).trim() : "";
      var lid = o.listing_id != null ? String(o.listing_id).trim() : "";
      var rk = o.rank != null ? String(o.rank).trim() : "";
      var idpart = pid || lid || rk;
      if (idpart) return "p:" + idpart;
    }
    return "";
  }

  /**
   * 当前作用域 key 尚无收藏数组时，从 LEGACY_LOCAL_FAV_KEYS 读旧数据，规范化去重后写入当前 key；
   * 已迁移或当前 key 已有数据则跳过；不按登录合并 guest 桶。
   */
  function migrateLocalFavoriteListOnce() {
    var scopeKey = favStorageKey();
    var markerKey = migrateLocalFavoriteListMarkerKey(scopeKey);
    try {
      if (localStorage.getItem(markerKey) === "1") return;
      var existing = [];
      try {
        var exRaw = localStorage.getItem(scopeKey);
        if (exRaw) existing = JSON.parse(exRaw);
      } catch (e1) {}
      if (Array.isArray(existing) && existing.length > 0) {
        localStorage.setItem(markerKey, "1");
        return;
      }
      var merged = [];
      var seen = {};
      function ingest(storageKey) {
        if (!storageKey || storageKey === scopeKey) return;
        var raw = localStorage.getItem(storageKey);
        if (!raw || !String(raw).trim()) return;
        var arr;
        try {
          arr = JSON.parse(raw);
        } catch (e2) {
          return;
        }
        if (!Array.isArray(arr)) return;
        var i;
        for (i = 0; i < arr.length; i++) {
          var nk = normalizeLegacyFavoriteEntryToKey(arr[i]);
          if (!nk || seen[nk]) continue;
          seen[nk] = true;
          merged.push(nk);
        }
      }
      var li;
      for (li = 0; li < LEGACY_LOCAL_FAV_KEYS.length; li++) {
        ingest(LEGACY_LOCAL_FAV_KEYS[li]);
      }
      if (merged.length > 0) {
        localStorage.setItem(scopeKey, JSON.stringify(merged));
      }
      localStorage.setItem(markerKey, "1");
    } catch (e3) {}
  }

  /**
   * 当前收藏作用域 key（与 favStorageKey 一致；本地持久化键名保持不变以免破坏已有数据）。
   * 逻辑映射：已登录 → favorites_<userId>；未登录 → favorites_guest（物理存储仍为 fav_list_*）。
   */
  function getFavoriteScopeKey() {
    return favStorageKey();
  }

  /**
   * 登录/登出后切换收藏作用域：派发事件；对比页/结果页在无整站跳转时用 reload 立刻换桶（guest ↔ 用户互不串数据）。
   * opts.skipReload：即将 location 跳转（如登出转 /login）时不要 reload，避免与 redirect 打架。
   */
  function onFavoriteAuthTransition(reason, opts) {
    opts = opts || {};
    var u = getUser();
    var detail = {
      reason: reason || "",
      scopeKey: favStorageKey(),
      userId: u && u.user_id ? String(u.user_id) : null,
      isGuest: !(u && u.user_id),
    };
    try {
      window.dispatchEvent(new CustomEvent("rentalai-favorite-scope-change", { detail: detail }));
    } catch (e0) {}
    try {
      if (!opts.skipReload) {
        var path = (window.location.pathname || "").replace(/\/$/, "") || "/";
        if (
          (reason === "login" || reason === "logout") &&
          (path === "/compare" || path === "/ai-result")
        ) {
          window.location.reload();
        }
      }
    } catch (e1) {}
    try {
      migrateLocalFavoriteListOnce();
    } catch (eMig) {}
  }

  function requireLogin() {
    return; // temporary local testing: bypass all login redirects

    var path = (window.location.pathname || "").replace(/\/$/, "") || "/";
    var publicPaths = [
      "/",
      "/login",
      "/register",
      "/account",
      "/assistant",
      "/analyzing",
      "/analysis-error",
      "/ai-result",
      "/test-analyze",
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

  /** 首页主内容区：账户条（与导航状态一致） */
  function renderHomeAccountStrip() {
    var el = document.getElementById("home-account-strip");
    if (!el) return;
    var u = getUser();
    if (!u) {
      el.className = "home-account-strip home-account-strip--guest";
      el.setAttribute("data-auth-state", "guest");
      el.innerHTML =
        '<a href="/account" class="home-account-strip-label">账户</a>' +
        '<span class="nav-sep">·</span>' +
        '<a href="/login" class="nav-auth-link">Login</a>' +
        '<span class="nav-sep">·</span>' +
        '<a href="/register" class="nav-auth-link">Sign Up</a>' +
        '<span class="hint muted home-account-strip-hint">访客可完整使用；登录后按账号保留个人历史（仍本机）</span>';
      return;
    }
    var email = u.email ? String(u.email) : "";
    var who = email || String(u.display_name || u.user_id || "—");
    var prot =
      u.auth_bearer === true
        ? '<span class="nav-sep">·</span><span class="hint muted nav-auth-protected-hint" title="会话已就绪，可用于后续受保护 API">受保护会话</span>'
        : "";
    el.className = "home-account-strip home-account-strip--signed-in";
    el.setAttribute("data-auth-state", "signed-in");
    el.innerHTML =
      '<span class="home-account-strip-label" lang="en">Signed in</span>' +
      '<span class="nav-sep">·</span>' +
      '<a href="/account" class="nav-auth-link">账户</a>' +
      '<span class="nav-sep">·</span>' +
      '<span class="nav-account-email" title="Current account">' +
      escapeHtml(who) +
      "</span>" +
      prot +
      '<span class="nav-sep">·</span>' +
      '<button type="button" class="home-account-logout-btn" title="Log out">Logout</button>';
    var btn = el.querySelector(".home-account-logout-btn");
    if (btn) btn.addEventListener("click", logout);
  }

  function refreshIdentityUI() {
    renderUnifiedNav();
    renderHomeAccountStrip();
    syncNavFavoriteCountDisplay();
  }

  /** Step15：同步加载收藏 API（供顶栏数量；与结果页/对比页同源）。 */
  function ensureFavoritesApiLoadedSync() {
    if (typeof global.RentalAIServerFavoritesApi !== "undefined") return;
    try {
      if (typeof global.rentalaiMergeAuthHeaders === "undefined") {
        var xhr0 = new XMLHttpRequest();
        xhr0.open("GET", "/assets/api_config.js", false);
        xhr0.send(null);
        if (xhr0.status === 200 && xhr0.responseText) {
          (0, Function)(xhr0.responseText)();
        }
      }
      var xhr = new XMLHttpRequest();
      xhr.open("GET", "/assets/server_favorites_api.js", false);
      xhr.send(null);
      if (xhr.status === 200 && xhr.responseText) {
        (0, Function)(xhr.responseText)();
      }
    } catch (eLoad) {}
  }

  function refreshNavCountAfterFavoritesReady() {
    ensureFavoritesApiLoadedSync();
    var api = global.RentalAIServerFavoritesApi;
    if (api && typeof api.refreshFavoritesCache === "function") {
      return api
        .refreshFavoritesCache(200)
        .then(function () {
          syncNavFavoriteCountDisplay();
        })
        .catch(function () {
          syncNavFavoriteCountDisplay();
        });
    }
    syncNavFavoriteCountDisplay();
    return Promise.resolve();
  }

  /** Step15：顶栏「房源对比」旁数量，仅来自 RentalAIServerFavoritesApi 缓存条数。 */
  function syncNavFavoriteCountDisplay() {
    var span = document.getElementById("rentalai-nav-favorites-count");
    if (!span) return;
    var n = 0;
    try {
      ensureFavoritesApiLoadedSync();
      var api = global.RentalAIServerFavoritesApi;
      if (api && typeof api.getFavoriteCountForCurrentScope === "function") {
        n = api.getFavoriteCountForCurrentScope();
      }
    } catch (eN) {}
    span.textContent = n > 0 ? " (" + n + ")" : "";
  }

  var _navFavoriteCountListenersBound = false;

  function bindNavFavoriteCountListenersOnce() {
    if (_navFavoriteCountListenersBound) return;
    _navFavoriteCountListenersBound = true;
    try {
      window.addEventListener("rentalai-favorites-updated", function () {
        syncNavFavoriteCountDisplay();
      });
      window.addEventListener("rentalai-favorite-scope-change", function () {
        refreshNavCountAfterFavoritesReady();
      });
    } catch (eNav) {}
  }

  /** 各业务页共用的顶部导航：未登录 Login / Sign Up；已登录 email + Logout */
  function renderUnifiedNav() {
    var nav = document.getElementById("demo-unified-nav");
    if (!nav) return;
    var u = getUser();
    if (!u) {
      nav.setAttribute("data-auth-state", "guest");
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
        '<a href="/compare">房源对比<span id="rentalai-nav-favorites-count" class="hint muted nav-favorites-count" aria-live="polite"></span></a>' +
        '<span class="nav-sep">·</span>' +
        '<a href="/account">账户</a>' +
        '<span class="nav-sep">·</span>' +
        '<a href="/login" class="nav-auth-link">Login</a>' +
        '<span class="nav-sep">·</span>' +
        '<a href="/register" class="nav-auth-link">Sign Up</a>';
      return;
    }
    var email = u.email ? String(u.email) : "";
    var who = email || String(u.display_name || u.user_id || "—");
    var prot =
      u.auth_bearer === true
        ? '<span class="nav-sep">·</span><span class="hint muted nav-auth-protected-hint" title="会话已就绪">受保护会话</span>'
        : "";
    nav.setAttribute("data-auth-state", "signed-in");
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
        '<a href="/compare">房源对比<span id="rentalai-nav-favorites-count" class="hint muted nav-favorites-count" aria-live="polite"></span></a>' +
        '<span class="nav-sep">·</span>' +
        '<a href="/account">账户</a>' +
        '<span class="nav-sep">·</span>' +
        '<span class="nav-account-email" title="Current account">' +
      escapeHtml(who) +
      "</span>" +
      prot +
      '<span class="nav-sep">·</span>' +
      '<button type="button" class="local-logout-btn" title="Log out">Logout</button>';
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
      bindNavFavoriteCountListenersOnce();
      refreshIdentityUI();
      initDemoClearStorage();
      refreshNavCountAfterFavoritesReady();
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
    getFavoriteScopeKey: getFavoriteScopeKey,
    onFavoriteAuthTransition: onFavoriteAuthTransition,
    getGuestSessionIdForFavorites: getGuestSessionIdForFavorites,
    buildGuestFavoriteScopeId: buildGuestFavoriteScopeId,
    migrateLocalFavoriteListOnce: migrateLocalFavoriteListOnce,
    normalizeLegacyFavoriteEntryToKey: normalizeLegacyFavoriteEntryToKey,
    refreshIdentityUI: refreshIdentityUI,
    renderUnifiedNav: renderUnifiedNav,
    renderHomeAccountStrip: renderHomeAccountStrip,
    syncNavFavoriteCountDisplay: syncNavFavoriteCountDisplay,
    refreshNavCountAfterFavoritesReady: refreshNavCountAfterFavoritesReady,
  };

  migrateLocalFavoriteListOnce();

  requireLogin();
  initDemoChrome();
})(window);
