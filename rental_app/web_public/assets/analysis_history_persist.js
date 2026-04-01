/**
 * Phase 5 Round4 — 统一历史保存（与 analysis_history_source 读路径对称）
 * - guest：写入 RentalAIAnalysisHistoryStore（localStorage 分桶）
 * - 已登录：依赖请求体 userId 由后端追加 persistence JSON；本函数默认不写本地，避免与 /analysis-history 云端列表重复
 * - alsoWriteLocalBackup：已登录时仍写本地（可选兜底）
 * 见 README「Phase 5 第四轮」；未做 token 校验与同步迁移。
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

  /**
   * @param {{
   *   kind: 'housing'|'legacy'|'contract',
   *   data: object,
   *   sourceMeta?: object,
   *   alsoWriteLocalBackup?: boolean
   * }} opts
   */
  function persistAnalysisResult(opts) {
    opts = opts || {};
    var kind = opts.kind;
    var guest = isGuestForHistory();
    var Store = global.RentalAIAnalysisHistoryStore;

    try {
      if (guest) {
        if (!Store) return { mode: "local_guest", localWritten: false, reason: "no_store" };
        if (kind === "housing" && opts.data) {
          Store.pushPropertyFromHousingData(opts.data);
        } else if (kind === "legacy" && opts.data) {
          Store.pushPropertyFromLegacyData(opts.data);
        } else if (kind === "contract" && opts.data) {
          Store.pushContractFromContractData(opts.data, opts.sourceMeta || {});
        } else {
          return { mode: "local_guest", localWritten: false, reason: "bad_args" };
        }
        return { mode: "local_guest", localWritten: true, remote: false };
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
    isGuestForHistory: isGuestForHistory,
    persistAnalysisResult: persistAnalysisResult,
    saveAnalysisHistory: saveAnalysisHistory,
  };
})(window);
