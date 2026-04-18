/**
 * Phase 5 Round4 — 统一历史保存（与 analysis_history_source 读路径对称）
 * - guest：仅写入 RentalAIAnalysisHistoryStore（localStorage 分桶），不上传账户
 * - 已登录：分析 POST 带 **mergeAuthHeadersForFetch**；后端以 **Bearer** 解析用户并追加 persistence JSON；本函数在 **`history_write.success`** 时跳过本地重复写入，避免与 /analysis-history 云端列表重复
 * - alsoWriteLocalBackup：已登录时仍写本地（可选兜底）
 * Phase 5 第六轮：服务端写入须 Bearer（guest 除外）；**persistAnalysisResult** 读 **`history_write`**；成功提示与 **markCloudHistoryNeedsRefresh** 供历史页 GET cache-bust
 */
(function (global) {
  var SESSION_CLOUD_REFRESH_KEY = "rentalai_cloud_history_need_refresh";
  function loadU() {
    try {
      var S = global.RentalAIUserStore;
      if (S && typeof S.loadUserFromStorage === "function") {
        return S.loadUserFromStorage();
      }
    } catch (e) {}
    return { isAuthenticated: false, userId: null };
  }

  /**
   * 供分析 POST 的 JSON body / FormData「写入」侧：已登录返回真实 userId；未登录返回 null
   *（body 不带 userId 时后端 resolve_history_user_id 为字面 guest，与无 Bearer 写入分支一致）。
   * 游客会话隔离依赖 X-Guest-Session（见 rentalaiMergeAuthHeaders）；勿在 body 传 guest:… 以免与后端「无 Bearer 且 claimed 须为 guest」冲突。
   */
  function getHistoryUserIdForApi() {
    var u = loadU();
    if (!u || !u.isAuthenticated || !u.userId) return null;
    return String(u.userId).trim().slice(0, 128) || null;
  }

  /**
   * 历史读取 / 删除 / 清空 / GET query 等作用域：已登录为 rentalai_user_id；未登录为 guest:<session>，
   * 与后端 resolve_history_read_user_id 一致；登录用户与游客历史不合并。
   */
  function getHistoryScopeUserIdForApi() {
    var u = loadU();
    if (u && u.isAuthenticated && u.userId) {
      return String(u.userId).trim().slice(0, 128) || null;
    }
    if (typeof global.rentalaiBuildGuestHistoryUserId === "function") {
      return global.rentalaiBuildGuestHistoryUserId();
    }
    return "guest:anonymous";
  }

  function isGuestForHistory() {
    return !loadU().isAuthenticated;
  }

  /** 与 server_history_api / api_config.rentalaiMergeAuthHeaders 一致 */
  function getBearerTokenForApi() {
    if (typeof global.rentalaiGetBearerToken === "function") {
      return global.rentalaiGetBearerToken();
    }
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
    if (typeof global.rentalaiMergeAuthHeaders === "function") {
      return global.rentalaiMergeAuthHeaders(headers || {});
    }
    headers = headers || {};
    var tok = getBearerTokenForApi();
    if (tok) headers["Authorization"] = "Bearer " + tok;
    return headers;
  }

  /** 云端写入成功后调用，历史页 GET 将带 cache-bust 拉最新。 */
  function markCloudHistoryNeedsRefresh() {
    try {
      sessionStorage.setItem(SESSION_CLOUD_REFRESH_KEY, String(Date.now()));
    } catch (e) {}
  }

  /** 供 analysis_history_source：若已标记则清除并返回 true（GET 加 `_t`）。 */
  function consumeCloudHistoryRefreshFlag() {
    try {
      if (sessionStorage.getItem(SESSION_CLOUD_REFRESH_KEY)) {
        sessionStorage.removeItem(SESSION_CLOUD_REFRESH_KEY);
        return true;
      }
    } catch (e) {}
    return false;
  }

  var HINT_CLOUD_OK =
    "Saved to your account history · 已保存到账户云端历史（分析历史页可查看）。";
  var HINT_FALLBACK =
    "Cloud history not saved · 云端未写入；已保存到本机「最近分析」摘要。";
  var HINT_LOCAL_GUEST =
    "Saved locally only · 已保存到本机「最近分析」（访客未登录，未上传账户）。";

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
  /**
   * 主产品历史写入前端承接点（结果页调用）：
   * - guest：写本机分桶（localStorage）
   * - 已登录：以后端 history_write.success 为准，成功则视为云端已落库并触发刷新标记
   * 该写入承接层同时覆盖 RentAI 与 ShortRentAI 的结果保存入口形态。
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
          return {
            mode: "local_guest",
            localWritten: true,
            remote: false,
            hint: HINT_LOCAL_GUEST,
            hintIsLocal: true,
          };
        }
        if (pushLocalProperty()) {
          return {
            mode: "local_guest",
            localWritten: true,
            remote: false,
            hint: HINT_LOCAL_GUEST,
            hintIsLocal: true,
          };
        }
        return { mode: "local_guest", localWritten: false, reason: "bad_args" };
      }

      if (hw && hw.success === true) {
        markCloudHistoryNeedsRefresh();
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
    getHistoryScopeUserIdForApi: getHistoryScopeUserIdForApi,
    getBearerTokenForApi: getBearerTokenForApi,
    mergeAuthHeadersForFetch: mergeAuthHeadersForFetch,
    isGuestForHistory: isGuestForHistory,
    persistAnalysisResult: persistAnalysisResult,
    saveAnalysisHistory: saveAnalysisHistory,
    SESSION_CLOUD_REFRESH_KEY: SESSION_CLOUD_REFRESH_KEY,
    markCloudHistoryNeedsRefresh: markCloudHistoryNeedsRefresh,
    consumeCloudHistoryRefreshFlag: consumeCloudHistoryRefreshFlag,
  };
})(window);
