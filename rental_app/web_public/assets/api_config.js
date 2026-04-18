/**
 * API base URL: empty = same-origin (FastAPI + static 同进程)；非空 = 分域部署时 API 根（无尾部斜杠）。
 * 读取顺序：meta vite-rentalai-api-base > rentalai-api-base > 构建前预设的 window.RENTALAI_API_BASE（测试用）。
 * 与 scripts/inject-api-base.mjs、Vercel Build 环境变量 RENTALAI_API_BASE 等配合。
 */
(function () {
  function getMeta(name) {
    var el = document.querySelector('meta[name="' + name + '"]');
    return el ? String(el.getAttribute("content") || "").trim() : "";
  }

  var preset =
    typeof window.RENTALAI_API_BASE === "string"
      ? String(window.RENTALAI_API_BASE).trim()
      : "";
  var viteBase = getMeta("vite-rentalai-api-base");
  var rentalBase = getMeta("rentalai-api-base");
  var base = (viteBase || rentalBase || preset || "").replace(/\/$/, "");
  window.RENTALAI_API_BASE = base;

  var envMeta = getMeta("rentalai-env");
  if (envMeta) {
    window.RENTALAI_ENV = envMeta;
  } else {
    var h = (location.hostname || "").toLowerCase();
    window.RENTALAI_ENV =
      h === "localhost" || h === "127.0.0.1" || h === "[::1]"
        ? "development"
        : "production";
  }

  window.rentalaiApiUrl = function (path) {
    var p = (path || "").trim();
    if (!p) return "";
    if (p.charAt(0) !== "/") p = "/" + p;
    if (!base) return p;
    return base + p;
  };

  function getBearerToken() {
    try {
      var t = localStorage.getItem("rentalai_bearer");
      if (t && String(t).trim()) return String(t).trim();
    } catch (e) {}
    try {
      if (window.RentalAIUserStore && typeof window.RentalAIUserStore.loadUserFromStorage === "function") {
        var u = window.RentalAIUserStore.loadUserFromStorage();
        if (u && u.authToken) return String(u.authToken).trim();
      }
    } catch (e2) {}
    return null;
  }

  function isDevAuthDebug() {
    if (typeof window.__RENTALAI_DEBUG_AUTH !== "undefined" && window.__RENTALAI_DEBUG_AUTH) return true;
    if (window.RENTALAI_ENV === "development") return true;
    try {
      var h = (location.hostname || "").toLowerCase();
      if (h === "localhost" || h === "127.0.0.1" || h === "[::1]") return true;
    } catch (e) {}
    try {
      if ((location.search || "").indexOf("debug_auth=1") >= 0) return true;
    } catch (e3) {}
    return false;
  }

  window.rentalaiDebugAuthLog = function (kind, url, hasToken) {
    if (!isDevAuthDebug()) return;
    try {
      console.log("[RentalAI auth]", kind, "url=", url, "hasToken=", !!hasToken);
    } catch (e) {}
  };

  window.rentalaiGetBearerToken = getBearerToken;

  /**
   * 游客会话隔离逻辑（持久化 localStorage）：
   * 为未登录用户生成稳定 guest_session_id，供 X-Guest-Session 与后端 guest:<session> 历史桶对齐，
   * 避免所有访客共用 guest:anonymous。
   */
  var GUEST_SESSION_ID_KEY = "guest_session_id";

  function rentalaiGetOrCreateGuestSessionId() {
    try {
      var existing = window.localStorage.getItem(GUEST_SESSION_ID_KEY);
      if (existing && String(existing).trim()) return String(existing).trim();
      var generated =
        typeof crypto !== "undefined" && crypto.randomUUID
          ? crypto.randomUUID()
          : String(Date.now()) +
            "-" +
            Math.random().toString(16).slice(2) +
            "-" +
            Math.random().toString(16).slice(2);
      window.localStorage.setItem(GUEST_SESSION_ID_KEY, generated);
      return generated;
    } catch (_) {
      return "fallback-" + Date.now() + "-" + Math.random().toString(16).slice(2);
    }
  }

  /**
   * 历史请求作用域 userId（游客）：与后端 resolve_history_read/write 中 guest:<hex> 桶一致。
   * 登录用户与游客历史不合并；写入 JSON body 仍用「显式 guest 或省略」由 getHistoryUserIdForApi 单独处理。
   */
  function rentalaiBuildGuestHistoryUserId() {
    var raw = rentalaiGetOrCreateGuestSessionId();
    return "guest:" + String(raw).replace(/-/g, "").slice(0, 48);
  }

  window.rentalaiGetOrCreateGuestSessionId = rentalaiGetOrCreateGuestSessionId;
  window.rentalaiBuildGuestHistoryUserId = rentalaiBuildGuestHistoryUserId;

  window.rentalaiMergeAuthHeaders = function (headers) {
    headers = headers || {};
    var tok = getBearerToken();
    if (tok && !headers["Authorization"] && !headers["authorization"]) {
      headers["Authorization"] = "Bearer " + tok;
    }
    if (!headers["X-Guest-Session"] && !headers["x-guest-session"]) {
      headers["X-Guest-Session"] = rentalaiGetOrCreateGuestSessionId();
    }
    return headers;
  };

  function defaultFetchCredentials() {
    if (!base) return "same-origin";
    try {
      if (String(base).indexOf("http") !== 0) return "same-origin";
      var o = new URL(base).origin;
      return o === location.origin ? "same-origin" : "omit";
    } catch (e) {
      return "same-origin";
    }
  }

  window.rentalaiDefaultFetchCredentials = defaultFetchCredentials;

  window.rentalaiApiFetch = function (path, init) {
    init = init || {};
    var url = window.rentalaiApiUrl(path);
    var h = init.headers;
    if (h instanceof Headers) {
      var o = {};
      h.forEach(function (v, k) {
        o[k] = v;
      });
      h = o;
    }
    h = window.rentalaiMergeAuthHeaders(h && typeof h === "object" ? h : {});
    var hasTok = !!(h["Authorization"] || h["authorization"]);
    window.rentalaiDebugAuthLog(init.method || "GET", url, hasTok);
    var cred = init.credentials != null ? init.credentials : defaultFetchCredentials();
    return fetch(url, {
      method: init.method || "GET",
      headers: h,
      body: init.body,
      credentials: cred,
      signal: init.signal,
      cache: init.cache,
    });
  };
})();
