/**
 * Phase 5 Round3/4 — GET /api/analysis/history/records（Demo：无 Authorization 校验）
 * 已登录用户的 /analysis-history 优先经 fetchUserHistory(userId) 拉全量；失败由 analysis_history_source 回退本地。
 * 下一步安全增强：受保护 API + token 绑定 userId（见 README「Phase 5 第四轮」推荐下一步）。
 */
(function (global) {
  function apiUrl(path) {
    return typeof global.rentalaiApiUrl === "function" ? global.rentalaiApiUrl(path) : path;
  }

  /**
   * 拉取指定 userId 的分析历史（不传 type 则为该用户全部类型，最多后端 limit）。
   * @param {string} userId
   * @param {{ type?: 'property'|'contract' }} [opts] 可选按类型过滤
   * @returns {Promise<{ success?: boolean, message?: string, records?: unknown[] }>}
   */
  function fetchUserHistory(userId, opts) {
    opts = opts || {};
    var q = new URLSearchParams();
    q.set("userId", (userId || "guest").trim() || "guest");
    if (opts.type) q.set("type", String(opts.type));
    return global
      .fetch(apiUrl("/api/analysis/history/records?" + q.toString()), { method: "GET" })
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
