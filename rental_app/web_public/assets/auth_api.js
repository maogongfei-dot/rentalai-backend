/**
 * Phase 5 Step4 + Round5 Step1/2 — /auth/login、/auth/register；成功响应写入 RentalAIUserStore（token + authType）。
 */
(function (global) {
  function apiUrl(path) {
    return typeof global.rentalaiApiUrl === "function" ? global.rentalaiApiUrl(path) : path;
  }

  function parseJsonResponse(r) {
    var ct = (r.headers.get("content-type") || "").toLowerCase();
    if (ct.indexOf("application/json") >= 0) {
      return r.json().then(function (j) {
        return { ok: r.ok, status: r.status, body: j };
      });
    }
    return r.text().then(function (t) {
      return {
        ok: r.ok,
        status: r.status,
        body: { message: t || "invalid response" },
      };
    });
  }

  /**
   * @param {string} body
   * @returns {string}
   */
  function getErrorMessage(body) {
    if (body == null) return "请求失败";
    if (typeof body.message === "string" && body.message) return body.message;
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail) && body.detail.length) {
      var first = body.detail[0];
      if (first && typeof first.msg === "string") return first.msg;
    }
    if (typeof body.error === "string") return body.error;
    return "请求失败";
  }

  /**
   * POST /auth/login
   * @returns {Promise<{ ok: boolean, status: number, body: object }>}
   */
  function loginApi(email, password) {
    return global
      .fetch(apiUrl("/auth/login"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: (email || "").trim(),
          password: password == null ? "" : String(password),
        }),
      })
      .then(parseJsonResponse)
      .catch(function () {
        return { ok: false, status: 0, body: { message: "网络错误" } };
      });
  }

  /**
   * POST /auth/register
   * @returns {Promise<{ ok: boolean, status: number, body: object }>}
   */
  function registerApi(email, password) {
    return global
      .fetch(apiUrl("/auth/register"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: (email || "").trim(),
          password: password == null ? "" : String(password),
        }),
      })
      .then(parseJsonResponse)
      .catch(function () {
        return { ok: false, status: 0, body: { message: "网络错误" } };
      });
  }

  /**
   * @param {object} body
   * @returns {string|null}
   */
  function getTokenFromAuthBody(body) {
    if (!body || typeof body !== "object") return null;
    if (body.auth && body.auth.token) return String(body.auth.token);
    if (body.token) return String(body.token);
    return null;
  }

  /**
   * @param {object} body
   * @returns {string|null}
   */
  function getAuthTypeFromAuthBody(body) {
    if (!body || typeof body !== "object") return null;
    if (body.auth && body.auth.auth_type) return String(body.auth.auth_type);
    if (typeof body.auth_type === "string" && body.auth_type) return body.auth_type;
    return null;
  }

  /**
   * 将 /auth/login 或 /auth/register 成功响应写入 RentalAIUserStore（Bearer + authType + userId + email）。
   * @param {{ token?: string, auth?: { token?: string, auth_type?: string }, user_id?: string, email?: string }} body
   */
  function applySessionFromAuthBody(body) {
    var token = getTokenFromAuthBody(body);
    if (!token) return;
    var authType = getAuthTypeFromAuthBody(body) || "session_placeholder";
    var S = global.RentalAIUserStore;
    if (S && typeof S.loginUser === "function") {
      S.loginUser({
        token: token,
        authToken: token,
        authType: authType,
        userId: body.user_id,
        email: body.email,
      });
    } else if (global.RentalAIAuth && typeof global.RentalAIAuth.persistSession === "function") {
      try {
        localStorage.removeItem("current_user");
      } catch (e) {}
      global.RentalAIAuth.persistSession({
        token: token,
        user_id: body.user_id,
        email: body.email,
        auth_type: authType,
      });
    }
  }

  global.RentalAIAuthApi = {
    loginApi: loginApi,
    registerApi: registerApi,
    getErrorMessage: getErrorMessage,
    getTokenFromAuthBody: getTokenFromAuthBody,
    getAuthTypeFromAuthBody: getAuthTypeFromAuthBody,
    applySessionFromAuthBody: applySessionFromAuthBody,
  };
})(window);
