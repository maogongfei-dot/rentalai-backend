/**
 * Phase 5 Round3/4 + Round5 Step3/4 — GET /api/analysis/history/records
 * 登录用户读取自己账户下的历史；游客读取自己 guest:<session> 桶；两者不合并。
 * 统一带 X-Guest-Session；已登录时亦可带，后端仍以 Bearer 解析用户为准。
 * userId query 须与当前历史作用域一致。响应可含 _httpStatus / _authError。
 */
(function (global) {
  function apiUrl(path) {
    return typeof global.rentalaiApiUrl === "function" ? global.rentalaiApiUrl(path) : path;
  }

  function getBearerTokenForHistory() {
    if (typeof global.rentalaiGetBearerToken === "function") {
      return global.rentalaiGetBearerToken();
    }
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

  function mergeHistoryHeaders() {
    var h = {};
    if (typeof global.rentalaiMergeAuthHeaders === "function") {
      h = global.rentalaiMergeAuthHeaders({});
    } else {
      var tok = getBearerTokenForHistory();
      if (tok) h["Authorization"] = "Bearer " + tok;
    }

    // 游客历史读取/删除/清空也要带自己的会话桶；
    // 登录用户与游客历史不合并，后端 Bearer 优先。
    try {
      var S = global.RentalAIUserStore;
      if (S && typeof S.getOrCreateGuestSessionId === "function") {
        h["X-Guest-Session"] = S.getOrCreateGuestSessionId();
      }
    } catch (e) {}

    return h;
  }

  function fetchCredentials() {
    if (typeof global.rentalaiDefaultFetchCredentials === "function") {
      return global.rentalaiDefaultFetchCredentials();
    }
    return "same-origin";
  }

  /**
   * 拉取分析历史（不传 type 则为全部类型，最多后端 limit）。
   * @param {string} userId 与当前历史作用域一致；可省略，此时默认用 getCurrentHistoryScopeUserId()
   * @param {{ type?: 'property'|'contract' }} [opts] 可选按类型过滤
   * @returns {Promise<{ success?: boolean, message?: string, records?: unknown[] }>}
   */
  /**
   * 历史列表云端获取点：登录用户读账户历史，游客读 guest:<session>；不合并。
   */
  function fetchUserHistory(userId, opts) {
    opts = opts || {};
    var headers = mergeHistoryHeaders();
    var q = new URLSearchParams();
    var uid = String(userId || "").trim();
    if (!uid) {
      try {
        var S = global.RentalAIUserStore;
        if (S && typeof S.getCurrentHistoryScopeUserId === "function") {
          uid = String(S.getCurrentHistoryScopeUserId() || "").trim();
        }
      } catch (e) {}
    }
    if (uid) q.set("userId", uid);
    if (opts.type) q.set("type", String(opts.type));
    if (opts.cacheBust) q.set("_t", String(Date.now()));
    var qs = q.toString();
    var url = apiUrl("/api/analysis/history/records" + (qs ? "?" + qs : ""));
    if (typeof global.rentalaiDebugAuthLog === "function") {
      global.rentalaiDebugAuthLog("GET /api/analysis/history/records", url, !!headers["Authorization"]);
    }
    return global
      .fetch(url, { method: "GET", headers: headers, credentials: fetchCredentials() })
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
   * Phase 5 Round7 Step3 — DELETE /api/analysis/history/records/{record_id}
   * 删除当前历史作用域内的一条（登录=账户桶；游客=guest:<session>）。
   * @returns {Promise<{ success?: boolean, message?: string, _httpStatus?: number }>}
   */
  function deleteHistoryRecord(recordId) {
    var rid = String(recordId || "").trim();
    if (!rid) {
      return Promise.resolve({ success: false, message: "record_id is required", _httpStatus: 0 });
    }
    var headers = mergeHistoryHeaders();
    var url = apiUrl("/api/analysis/history/records/" + encodeURIComponent(rid));
    if (typeof global.rentalaiDebugAuthLog === "function") {
      global.rentalaiDebugAuthLog("DELETE history record", url, !!headers["Authorization"]);
    }
    return global
      .fetch(url, { method: "DELETE", headers: headers, credentials: fetchCredentials() })
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

  /**
   * Phase 5 Round7 Step4 — DELETE /api/analysis/history/clear
   * 清空当前历史作用域内的全部记录（登录与游客桶互不干扰）。
   * @returns {Promise<{ success?: boolean, message?: string, deleted_count?: number, _httpStatus?: number }>}
   */
  function clearAllHistory() {
    var headers = mergeHistoryHeaders();
    var url = apiUrl("/api/analysis/history/clear");
    if (typeof global.rentalaiDebugAuthLog === "function") {
      global.rentalaiDebugAuthLog("DELETE /api/analysis/history/clear", url, !!headers["Authorization"]);
    }
    return global
      .fetch(url, { method: "DELETE", headers: headers, credentials: fetchCredentials() })
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
    clearAllHistory: clearAllHistory,
  };
})(window);
