/**
 * Phase 5 Round3 Step4 — 最小封装：GET /api/analysis/history/records（为后续「云端历史」切换预留）。
 * 默认不改变分析历史页行为；在 URL 加 ?server_history=1 时由 analysis_history_page 打一次探测日志。
 */
(function (global) {
  function apiUrl(path) {
    return typeof global.rentalaiApiUrl === "function" ? global.rentalaiApiUrl(path) : path;
  }

  /**
   * @param {string} userId
   * @param {{ type?: string }} [opts]  property | contract
   * @returns {Promise<{ success?: boolean, message?: string, records?: unknown[] }>}
   */
  function fetchServerHistoryRecords(userId, opts) {
    opts = opts || {};
    var q = new URLSearchParams();
    q.set("userId", (userId || "guest").trim() || "guest");
    if (opts.type) q.set("type", String(opts.type));
    return global
      .fetch(apiUrl("/api/analysis/history/records?" + q.toString()), { method: "GET" })
      .then(function (r) {
        return r.json().then(function (j) {
          return j;
        });
      })
      .catch(function () {
        return { success: false, message: "network_error", records: [] };
      });
  }

  global.RentalAIServerHistoryApi = {
    fetchServerHistoryRecords: fetchServerHistoryRecords,
  };
})(window);
