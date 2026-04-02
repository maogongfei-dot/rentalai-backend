/**
 * Phase 5 Round4 — 统一历史保存（与 analysis_history_source 读路径对称）
 * - guest：写入 RentalAIAnalysisHistoryStore（localStorage 分桶）
 * - 已登录：依赖请求体 userId 由后端追加 persistence JSON；本函数默认不写本地，避免与 /analysis-history 云端列表重复
 * - alsoWriteLocalBackup：已登录时仍写本地（可选兜底）
 * Phase 6 Round1：服务端 JSON 写入需 Bearer；**mergeAuthHeadersForFetch** 给房源/合同 POST。
 * Phase 6 Round2：分析成功后 **persistAnalysisResult** 根据 **`serverHistoryWrite`/`history_write`** 决定：云端成功则跳过本地重复写入；失败则回退本机摘要。
 */
(function (global) {
  function loadU() {
    try {
      var S = global.RentalAIUserStore;
      if (S && typeof S.loadUserFromStorage === "function") {
        return S.loadUserFromStorage();
      }
    } catch (e) {}
    return { isAuthenticated: false, userId: null };
  }

  /** 供 JSON body / FormData：已登录返回 userId，否则 null（后端记 guest）。 */
  function getHistoryUserIdForApi() {
    var u = loadU();
    if (!u || !u.isAuthenticated || !u.userId) return null;
    return String(u.userId).trim().slice(0, 128) || null;
  }

  function isGuestForHistory() {
    return !loadU().isAuthenticated;
  }

  /** 与 server_history_api 一致：供写入类请求带 Authorization */
  function getBearerTokenForApi() {
    try {
      var S = global.RentalAIUserStore;
      if (S && typeof S.loadUserFromStorage === "function") {
        var u = S.loadUserFromStorage();
        if (u && u.authToken) return String(u.authToken);
      }
    } catch (e) {}
    try {
      return localStorage.getItem("rentalai_bearer");
    } catch (e2) {}
    return null;
  }

  /**
   * @param {Record<string, string>} [headers]
   * @returns {Record<string, string>}
   */
  function mergeAuthHeadersForFetch(headers) {
    headers = headers || {};
    var tok = getBearerTokenForApi();
    if (tok) headers["Authorization"] = "Bearer " + tok;
    return headers;
  }

  var HINT_CLOUD_OK =
    "已同步至账户云端历史（本页未重复写入本地「最近分析」摘要）。";
  var HINT_FALLBACK = "云端历史未保存，已写入本机「最近分析」摘要。";

  /**
   * 统一保存入口：guest → 仅本地；已登录 → 若 **`serverHistoryWrite.success`** 为 true 则跳过本地（避免与云端重复）；为 false 则回退本地。
   * @param {{
   *   kind: 'housing'|'legacy'|'contract',
   *   data: object,
   *   sourceMeta?: object,
   *   alsoWriteLocalBackup?: boolean,
   *   serverHistoryWrite?: { success?: boolean, message?: string },
   *   history_write?: { success?: boolean, message?: string }
   * }} opts
   * @returns {object} 含可选 **hint**（供结果页轻提示）
   */
  function persistAnalysisResult(opts) {
    opts = opts || {};
    var kind = opts.kind;
    var guest = isGuestForHistory();
    var Store = global.RentalAIAnalysisHistoryStore;
    var hw =
      opts.serverHistoryWrite != null
        ? opts.serverHistoryWrite
        : opts.history_write != null
          ? opts.history_write
          : opts.data && typeof opts.data === "object"
            ? opts.data.history_write
            : null;

    function pushLocalProperty() {
      if (!Store) return false;
      if (kind === "housing" && opts.data) {
        Store.pushPropertyFromHousingData(opts.data);
        return true;
      }
      if (kind === "legacy" && opts.data) {
        Store.pushPropertyFromLegacyData(opts.data);
        return true;
      }
      return false;
    }

    function pushLocalContract() {
      if (!Store || kind !== "contract" || !opts.data) return false;
      Store.pushContractFromContractData(opts.data, opts.sourceMeta || {});
      return true;
    }

    try {
      if (guest) {
        if (!Store) return { mode: "local_guest", localWritten: false, reason: "no_store" };
        if (kind === "contract") {
          if (!pushLocalContract()) return { mode: "local_guest", localWritten: false, reason: "bad_args" };
          return { mode: "local_guest", localWritten: true, remote: false };
        }
        if (pushLocalProperty()) {
          return { mode: "local_guest", localWritten: true, remote: false };
        }
        return { mode: "local_guest", localWritten: false, reason: "bad_args" };
      }

      if (hw && hw.success === true) {
        return {
          mode: "remote_user",
          localWritten: false,
          remote: true,
          serverHistoryOk: true,
          skippedLocalDuplicate: true,
          hint: HINT_CLOUD_OK,
        };
      }

      if (hw && hw.success === false) {
        var wrote = false;
        if (kind === "contract") wrote = pushLocalContract();
        else wrote = pushLocalProperty();
        return {
          mode: "remote_user",
          localWritten: wrote,
          remote: false,
          serverHistoryOk: false,
          fallbackLocal: true,
          hint: wrote ? HINT_FALLBACK : null,
        };
      }

      if (opts.alsoWriteLocalBackup === true && Store) {
        if (kind === "housing" && opts.data) {
          Store.pushPropertyFromHousingData(opts.data);
        } else if (kind === "legacy" && opts.data) {
          Store.pushPropertyFromLegacyData(opts.data);
        } else if (kind === "contract" && opts.data) {
          Store.pushContractFromContractData(opts.data, opts.sourceMeta || {});
        }
        return { mode: "remote_user", localWritten: true, remote: true };
      }

      return { mode: "remote_user", localWritten: false, remote: true };
    } catch (e) {
      return { mode: guest ? "local_guest" : "remote_user", localWritten: false, error: String(e) };
    }
  }

  function saveAnalysisHistory(opts) {
    return persistAnalysisResult(opts);
  }

  global.RentalAIAnalysisHistoryPersist = {
    getHistoryUserIdForApi: getHistoryUserIdForApi,
    getBearerTokenForApi: getBearerTokenForApi,
    mergeAuthHeadersForFetch: mergeAuthHeadersForFetch,
    isGuestForHistory: isGuestForHistory,
    persistAnalysisResult: persistAnalysisResult,
    saveAnalysisHistory: saveAnalysisHistory,
  };
})(window);
