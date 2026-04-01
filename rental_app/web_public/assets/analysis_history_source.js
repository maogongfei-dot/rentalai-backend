/**
 * Phase 5 Round4 — 历史来源解析层（双模式收尾）
 * - 读：未登录 → local_guest + 本地 listByType；已登录 → remote_user + fetchUserHistory 全量后按 property/contract 拆分
 * - 写：不在此文件；见 analysis_history_persist（guest 本地）与后端 analysis_history_writer（已登录 JSON）
 * - 记录：normalizeRemoteRecord 与本地项对齐字段（created_at 均为 ISO 字符串）；远端行带 _historySource: "remote"
 * 未实现：分页、搜索、guest→user 迁移、冲突处理 — 见 rental_app/README.md「Phase 5 第四轮」
 * 依赖：RentalAIUserStore、RentalAIAnalysisHistoryStore、RentalAIServerHistoryApi。
 */
(function (global) {
  var MODE_LOCAL_GUEST = "local_guest";
  var MODE_REMOTE_USER = "remote_user";

  function resolveHistoryMode() {
    var auth = false;
    var bucket = "guest";
    try {
      var S = global.RentalAIUserStore;
      if (S && typeof S.loadUserFromStorage === "function") {
        var u = S.loadUserFromStorage();
        auth = !!(u && u.isAuthenticated);
      }
      if (S && typeof S.getHistoryBucketId === "function") {
        bucket = String(S.getHistoryBucketId() || "guest");
      }
    } catch (e) {}
    return {
      mode: auth ? MODE_REMOTE_USER : MODE_LOCAL_GUEST,
      bucketId: bucket,
      isAuthenticated: auth,
    };
  }

  function getHistorySourceStrategy() {
    var r = resolveHistoryMode();
    return {
      mode: r.mode,
      bucketId: r.bucketId,
      isAuthenticated: r.isAuthenticated,
      preferRemote: r.mode === MODE_REMOTE_USER,
      preferLocalGuest: r.mode === MODE_LOCAL_GUEST,
    };
  }

  function listLocalByType(type) {
    var S = global.RentalAIAnalysisHistoryStore;
    if (!S || typeof S.listByType !== "function") return [];
    return S.listByType(type) || [];
  }

  /**
   * 将后端单条 record 转为与 unified history 列表项兼容的结构。
   * @param {object} rec
   * @returns {object|null}
   */
  function normalizeRemoteRecord(rec) {
    if (!rec || typeof rec !== "object") return null;
    var t = String(rec.type || "").toLowerCase();
    var sum = rec.summary && typeof rec.summary === "object" ? rec.summary : {};
    var snippet = "—";
    var preview = "—";
    var detail = null;

    if (t === "property") {
      snippet =
        sum.user_text_preview ||
        sum.market_summary_title ||
        String(rec.title || "").trim() ||
        "—";
      preview = snippet;
      if (sum.top_deal_count != null) {
        snippet = (snippet !== "—" ? snippet + " · " : "") + "Top " + sum.top_deal_count;
      }
      detail = {
        variant: "remote_property",
        user_text_preview: String(sum.user_text_preview || ""),
        market_summary_title: String(sum.market_summary_title || ""),
        top_deal_count: sum.top_deal_count != null ? sum.top_deal_count : null,
        error_keys: Array.isArray(sum.error_keys) ? sum.error_keys : [],
        result_snapshot: rec.result_snapshot && typeof rec.result_snapshot === "object" ? rec.result_snapshot : null,
      };
    } else if (t === "contract") {
      snippet =
        sum.key_risk_preview ||
        sum.overall_conclusion_preview ||
        String(rec.title || "").trim() ||
        "—";
      preview = sum.overall_conclusion_preview || sum.key_risk_preview || snippet;
      if (rec.result_snapshot && typeof rec.result_snapshot === "object") {
        var rs = rec.result_snapshot;
        if (rs.summary_view && typeof rs.summary_view === "object") {
          detail = rs.summary_view;
        }
      }
    }

    return {
      id: String(rec.record_id || "").trim() || "remote_" + String(Math.random()).slice(2),
      type: t === "contract" ? "contract" : "property",
      title: String(rec.title || "—").trim() || "—",
      created_at: String(rec.created_at == null ? "" : rec.created_at).trim(),
      summary_snippet: String(snippet).slice(0, 260),
      result_preview: String(preview).slice(0, 260),
      detail_snapshot: detail,
      _historySource: "remote",
    };
  }

  function normalizeRemoteRecords(records, expectType) {
    if (!Array.isArray(records)) return [];
    var out = [];
    var i;
    for (i = 0; i < records.length; i++) {
      var row = normalizeRemoteRecord(records[i]);
      if (!row) continue;
      if (expectType && row.type !== expectType) continue;
      out.push(row);
    }
    return out;
  }

  /**
   * 单次拉取全部云端记录后按 type 拆分（减少往返）。
   */
  function splitCloudRecords(records) {
    var prop = [];
    var con = [];
    if (!Array.isArray(records)) return { propertyRecords: prop, contractRecords: con };
    var i;
    for (i = 0; i < records.length; i++) {
      var row = normalizeRemoteRecord(records[i]);
      if (!row) continue;
      if (row.type === "contract") con.push(row);
      else prop.push(row);
    }
    return { propertyRecords: prop, contractRecords: con };
  }

  function loadAnalysisHistory() {
    var info = resolveHistoryMode();
    if (info.mode === MODE_LOCAL_GUEST) {
      return Promise.resolve({
        mode: MODE_LOCAL_GUEST,
        bucketId: info.bucketId,
        success: true,
        message: "ok_local",
        propertyRecords: listLocalByType("property"),
        contractRecords: listLocalByType("contract"),
        usedFallback: false,
      });
    }

    var uid = info.bucketId;
    var api = global.RentalAIServerHistoryApi;
    if (!api || typeof api.fetchUserHistory !== "function") {
      return Promise.resolve({
        mode: MODE_REMOTE_USER,
        bucketId: uid,
        success: false,
        message: "server_history_api_missing",
        propertyRecords: listLocalByType("property"),
        contractRecords: listLocalByType("contract"),
        usedFallback: true,
      });
    }

    return api
      .fetchUserHistory(uid, {})
      .then(function (body) {
        if (!body || body.success === false) {
          return {
            mode: MODE_REMOTE_USER,
            bucketId: uid,
            success: false,
            message: String((body && body.message) || "remote_fetch_failed"),
            propertyRecords: listLocalByType("property"),
            contractRecords: listLocalByType("contract"),
            usedFallback: true,
          };
        }
        var split = splitCloudRecords(body.records || []);
        return {
          mode: MODE_REMOTE_USER,
          bucketId: uid,
          success: true,
          message: "ok_remote",
          propertyRecords: split.propertyRecords,
          contractRecords: split.contractRecords,
          usedFallback: false,
        };
      })
      .catch(function () {
        return {
          mode: MODE_REMOTE_USER,
          bucketId: uid,
          success: false,
          message: "network_error",
          propertyRecords: listLocalByType("property"),
          contractRecords: listLocalByType("contract"),
          usedFallback: true,
        };
      });
  }

  global.RentalAIAnalysisHistorySource = {
    MODE_LOCAL_GUEST: MODE_LOCAL_GUEST,
    MODE_REMOTE_USER: MODE_REMOTE_USER,
    resolveHistoryMode: resolveHistoryMode,
    getHistorySourceStrategy: getHistorySourceStrategy,
    loadAnalysisHistory: loadAnalysisHistory,
    normalizeRemoteRecord: normalizeRemoteRecord,
    normalizeRemoteRecords: normalizeRemoteRecords,
  };
})(window);
