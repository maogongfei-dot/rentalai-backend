/**
 * Phase 5 Round3/4 + Round5 Step3/4 — GET /api/analysis/history/records
 * 云端读取统一由此模块带 Authorization: Bearer（RentalAIUserStore / rentalai_bearer）。
 * userId query 可选，须与 token 用户一致。响应体可含 _httpStatus / _authError 供上层区分 401/403。
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
    if (opts.cacheBust) q.set("_t", String(Date.now()));
    var qs = q.toString();
    var url = apiUrl("/api/analysis/history/records" + (qs ? "?" + qs : ""));
    return global
      .fetch(url, { method: "GET", headers: headers })
      .then(function (r) {
        return r
          .json()
          .then(function (j) {
            var obj =
              j && typeof j === "object"
                ? j
                : { success: false, message: "invalid_json", records: [] };
            obj._httpStatus = r.status;
            obj._authError = r.status === 401 || r.status === 403;
            if (!r.ok && (!j || typeof j !== "object")) {
              obj.success = false;
              if (!obj.message) obj.message = "http_" + r.status;
            }
            return obj;
          })
          .catch(function () {
            return { success: false, message: "bad_json", records: [], _httpStatus: r.status, _authError: false };
          });
      })
      .catch(function () {
        return { success: false, message: "network_error", records: [], _httpStatus: 0, _authError: false };
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

  /**
   * Phase 5 Round7 Step3 — DELETE /api/analysis/history/records/{record_id}（须 Bearer）。
   * @returns {Promise<{ success?: boolean, message?: string, _httpStatus?: number }>}
   */
  function deleteHistoryRecord(recordId) {
    var rid = String(recordId || "").trim();
    if (!rid) {
      return Promise.resolve({ success: false, message: "record_id is required", _httpStatus: 0 });
    }
    var tok = getBearerTokenForHistory();
    var headers = {};
    if (tok) headers["Authorization"] = "Bearer " + tok;
    var url =
      apiUrl("/api/analysis/history/records/" + encodeURIComponent(rid));
    return global
      .fetch(url, { method: "DELETE", headers: headers })
      .then(function (r) {
        return r
          .json()
          .then(function (j) {
            var obj =
              j && typeof j === "object"
                ? j
                : { success: false, message: "invalid_json" };
            obj._httpStatus = r.status;
            if (!r.ok) {
              obj.success = false;
              if (obj.message == null || obj.message === "") {
                obj.message = "http_" + r.status;
              }
            }
            return obj;
          })
          .catch(function () {
            return {
              success: false,
              message: "bad_json",
              _httpStatus: r.status,
            };
          });
      })
      .catch(function () {
        return { success: false, message: "network_error", _httpStatus: 0 };
      });
  }

  global.RentalAIServerHistoryApi = {
    fetchUserHistory: fetchUserHistory,
    getHistoryRecords: getHistoryRecords,
    fetchServerHistoryRecords: fetchServerHistoryRecords,
    getBearerTokenForHistory: getBearerTokenForHistory,
    deleteHistoryRecord: deleteHistoryRecord,
  };
})(window);
