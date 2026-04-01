/**
 * Phase 5 Round3/4 + Round5 Step3 — GET /api/analysis/history/records
 * 需 Authorization: Bearer（与登录 session 一致）；userId query 可选，若带则须与 token 用户一致。
 * 失败时 analysis_history_source 回退本地。
 */
(function (global) {
  function apiUrl(path) {
    return typeof global.rentalaiApiUrl === "function" ? global.rentalaiApiUrl(path) : path;
  }

  function getBearerTokenForHistory() {
    try {
      if (global.RentalAIUserStore && typeof global.RentalAIUserStore.loadUserFromStorage === "function") {
        var s = global.RentalAIUserStore.loadUserFromStorage();
        if (s && s.authToken) return String(s.authToken);
      }
    } catch (e) {}
    try {
      return localStorage.getItem("rentalai_bearer");
    } catch (e2) {}
    return null;
  }

  /**
   * 拉取当前 Bearer 会话用户的分析历史（不传 type 则为全部类型，最多后端 limit）。
   * @param {string} userId 与 RentalAIUserStore 分桶一致；可选写入 query 供校验
   * @param {{ type?: 'property'|'contract' }} [opts] 可选按类型过滤
   * @returns {Promise<{ success?: boolean, message?: string, records?: unknown[] }>}
   */
  function fetchUserHistory(userId, opts) {
    opts = opts || {};
    var tok = getBearerTokenForHistory();
    var headers = {};
    if (tok) headers["Authorization"] = "Bearer " + tok;
    var q = new URLSearchParams();
    var uid = (userId || "").trim();
    if (uid) q.set("userId", uid);
    if (opts.type) q.set("type", String(opts.type));
    var qs = q.toString();
    var url = apiUrl("/api/analysis/history/records" + (qs ? "?" + qs : ""));
    return global
      .fetch(url, { method: "GET", headers: headers })
      .then(function (r) {
        return r
          .json()
          .then(function (j) {
            if (!r.ok && (!j || typeof j !== "object")) {
              return { success: false, message: "http_" + r.status, records: [] };
            }
            return j && typeof j === "object" ? j : { success: false, message: "invalid_json", records: [] };
          })
          .catch(function () {
            return { success: false, message: "bad_json", records: [] };
          });
      })
      .catch(function () {
        return { success: false, message: "network_error", records: [] };
      });
  }

  /**
   * 同 fetchUserHistory，返回规整结构便于调用方使用。
   * @returns {Promise<{ ok: boolean, message: string, records: unknown[] }>}
   */
  function getHistoryRecords(userId, opts) {
    return fetchUserHistory(userId, opts).then(function (body) {
      if (!body || typeof body !== "object") {
        return { ok: false, message: "invalid_response", records: [] };
      }
      return {
        ok: body.success !== false,
        message: String(body.message || ""),
        records: Array.isArray(body.records) ? body.records : [],
      };
    });
  }

  /**
   * @deprecated 语义同 fetchUserHistory（保留兼容）
   */
  function fetchServerHistoryRecords(userId, opts) {
    return fetchUserHistory(userId, opts);
  }

  global.RentalAIServerHistoryApi = {
    fetchUserHistory: fetchUserHistory,
    getHistoryRecords: getHistoryRecords,
    fetchServerHistoryRecords: fetchServerHistoryRecords,
  };
})(window);
