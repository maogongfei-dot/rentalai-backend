/**
 * Phase 5 Step2 — 最小前端用户状态（localStorage，无 React）
 * 统一：isAuthenticated / userId / email；与 auth_session.js 的 Bearer 键、current_user 兼容。
 * API：loadUserFromStorage、loginUser、logoutUser、registerUser（占位）
 */
(function (global) {
  var CURRENT_USER_KEY = "current_user";
  var K = {
    bearer: "rentalai_bearer",
    userId: "rentalai_user_id",
    email: "rentalai_user_email",
  };

  function apiUrl(path) {
    return typeof global.rentalaiApiUrl === "function" ? global.rentalaiApiUrl(path) : path;
  }

  function notifyAuthUiIfPresent() {
    var A = global.RentalAIAuth;
    if (!A) return;
    if (typeof A.initAuthNav === "function") A.initAuthNav();
    if (typeof A.updateHomeGuestNotice === "function") A.updateHomeGuestNotice();
    if (typeof A.updateResultGuestBanner === "function") A.updateResultGuestBanner();
  }

  /**
   * @returns {{
   *   isAuthenticated: boolean,
   *   userId: string|null,
   *   email: string|null,
   *   displayName: string|null,
   *   authMode: "bearer"|"local_demo"|null
   * }}
   */
  function loadUserFromStorage() {
    try {
      var token = localStorage.getItem(K.bearer);
      var uid = localStorage.getItem(K.userId);
      var em = localStorage.getItem(K.email);
      if (token && (uid || em)) {
        var uidStr = uid || em || null;
        var emailStr = em || null;
        return {
          isAuthenticated: true,
          userId: uidStr,
          email: emailStr,
          displayName: emailStr || uidStr,
          authMode: "bearer",
        };
      }
    } catch (e) {}

    try {
      var raw = localStorage.getItem(CURRENT_USER_KEY);
      if (raw) {
        var o = JSON.parse(raw);
        if (o && o.user_id) {
          var id = String(o.user_id);
          var disp = o.display_name != null ? String(o.display_name) : null;
          var mail = o.email != null ? String(o.email) : null;
          return {
            isAuthenticated: true,
            userId: id,
            email: mail,
            displayName: disp || mail || id,
            authMode: "local_demo",
          };
        }
      }
    } catch (e2) {}

    return {
      isAuthenticated: false,
      userId: null,
      email: null,
      displayName: null,
      authMode: null,
    };
  }

  /**
   * @param {{
   *   token?: string,
   *   userId?: string|number,
   *   email?: string,
   *   displayName?: string,
   *   source?: "api"|"local_demo"
   * }} opts
   */
  function loginUser(opts) {
    opts = opts || {};
    if (opts.token) {
      try {
        localStorage.removeItem(CURRENT_USER_KEY);
      } catch (e) {}
      localStorage.setItem(K.bearer, String(opts.token));
      if (opts.userId != null && opts.userId !== "") {
        localStorage.setItem(K.userId, String(opts.userId));
      }
      if (opts.email) localStorage.setItem(K.email, String(opts.email));
      notifyAuthUiIfPresent();
      return loadUserFromStorage();
    }

    if (opts.source === "local_demo") {
      try {
        localStorage.removeItem(K.bearer);
        localStorage.removeItem(K.userId);
        localStorage.removeItem(K.email);
      } catch (e2) {}
      if (global.RentalAIAuth && typeof global.RentalAIAuth.clearSession === "function") {
        global.RentalAIAuth.clearSession();
      }
      var user = {
        user_id: opts.userId || "u_" + Date.now(),
        display_name: opts.displayName || opts.email || "用户",
        login_at: new Date().toISOString(),
      };
      if (opts.email) user.email = opts.email;
      localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(user));
      notifyAuthUiIfPresent();
      return loadUserFromStorage();
    }

    return loadUserFromStorage();
  }

  /**
   * 登出：清理 current_user、Bearer 与 auth_session 键；可选 POST /auth/logout。
   * 登出后历史分桶自动回到 guest（见 getHistoryBucketId）。
   * @param {{ redirect?: boolean, redirectTo?: string, tryServerLogout?: boolean }} [options]
   * @returns {Promise<object>|object} redirect 为 false 时返回 loadUserFromStorage() 快照
   */
  function logoutUser(options) {
    options = options || {};
    var redirect = options.redirect !== false;
    var redirectTo = options.redirectTo || "/login";
    var tryServer = options.tryServerLogout !== false;

    var token = null;
    try {
      token = localStorage.getItem(K.bearer);
    } catch (e) {}

    function clearLocal() {
      try {
        localStorage.removeItem(CURRENT_USER_KEY);
        localStorage.removeItem(K.bearer);
        localStorage.removeItem(K.userId);
        localStorage.removeItem(K.email);
      } catch (e2) {}
      if (global.RentalAIAuth && typeof global.RentalAIAuth.clearSession === "function") {
        global.RentalAIAuth.clearSession();
      }
      notifyAuthUiIfPresent();
      if (
        redirect === false &&
        global.RentalAILocalAuth &&
        typeof global.RentalAILocalAuth.refreshIdentityUI === "function"
      ) {
        global.RentalAILocalAuth.refreshIdentityUI();
      }
    }

    if (token && tryServer && typeof global.fetch === "function") {
      return global
        .fetch(apiUrl("/auth/logout"), {
          method: "POST",
          headers: { Authorization: "Bearer " + token },
        })
        .catch(function () {})
        .then(function () {
          clearLocal();
          if (redirect) global.location.href = redirectTo;
          return loadUserFromStorage();
        });
    }

    clearLocal();
    if (redirect) global.location.href = redirectTo;
    return loadUserFromStorage();
  }

  /**
   * 占位：请使用 RentalAIAuthApi.registerApi（注册页）或 POST /auth/register。
   * @returns {Promise<{ ok: boolean, placeholder: boolean, message: string }>}
   */
  function registerUser() {
    return Promise.resolve({
      ok: false,
      placeholder: true,
      message: "请使用「注册」页；程序化注册请调用 RentalAIAuthApi.registerApi。",
    });
  }

  /** Phase 5 Step5：localStorage 历史分桶 id（guest | 已登录 userId 净化） */
  function sanitizeHistoryBucketId(uid) {
    var s = String(uid || "").replace(/[^a-zA-Z0-9._-]/g, "_");
    if (s.length > 96) s = s.slice(0, 96);
    return s || "guest";
  }

  function getHistoryBucketId() {
    var s = loadUserFromStorage();
    if (!s.isAuthenticated) return "guest";
    return sanitizeHistoryBucketId(s.userId);
  }

  function getUnifiedHistoryStorageKey() {
    return "rentalai_unified_analysis_history_v1__" + getHistoryBucketId();
  }

  function getManualHistoryStorageKey() {
    return "analysis_history__" + getHistoryBucketId();
  }

  global.RentalAIUserStore = {
    STORAGE_KEYS: { CURRENT_USER_KEY: CURRENT_USER_KEY, SESSION: K },
    loadUserFromStorage: loadUserFromStorage,
    loginUser: loginUser,
    logoutUser: logoutUser,
    registerUser: registerUser,
    getHistoryBucketId: getHistoryBucketId,
    getUnifiedHistoryStorageKey: getUnifiedHistoryStorageKey,
    getManualHistoryStorageKey: getManualHistoryStorageKey,
  };
})(window);
