/**
 * Phase 4 Round6 Step2：统一本地「最近分析」记录（localStorage）
 * 与手动「保存到 analysis_history」全量快照并存；本模块为轻量摘要列表。
 */
(function (global) {
  var STORAGE_KEY = "rentalai_unified_analysis_history_v1";
  var MAX_ITEMS = 50;
  /** 与 sessionStorage ai_housing_query_last 内容比对，避免同一次结果页刷新重复写入 */
  var DEDUP_HOUSING = "rentalai_unified_hist_dedup_property";
  /** 与 sessionStorage ai_analyze_last 比对 */
  var DEDUP_LEGACY = "rentalai_unified_hist_dedup_legacy";

  function getUserId() {
    try {
      if (global.RentalAILocalAuth && global.RentalAILocalAuth.getUser) {
        var u = global.RentalAILocalAuth.getUser();
        return u && u.user_id ? String(u.user_id) : null;
      }
    } catch (e) {}
    return null;
  }

  function truncate(s, n) {
    s = s == null ? "" : String(s);
    n = n || 120;
    if (s.length <= n) return s;
    return s.slice(0, n - 1) + "…";
  }

  function newId(prefix) {
    return (
      (prefix || "r") +
      "_" +
      Date.now().toString(36) +
      "_" +
      Math.random().toString(36).slice(2, 9)
    );
  }

  function loadRaw() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      var arr = raw ? JSON.parse(raw) : [];
      return Array.isArray(arr) ? arr : [];
    } catch (e) {
      return [];
    }
  }

  function saveRaw(arr) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(arr));
    } catch (e) {}
  }

  function prepend(entry) {
    entry.user_id = getUserId();
    var list = loadRaw();
    list.unshift(entry);
    if (list.length > MAX_ITEMS) {
      list = list.slice(0, MAX_ITEMS);
    }
    saveRaw(list);
  }

  function housingSnippet(data) {
    var pq = data.parsed_query || {};
    var nf = data.normalized_filters || {};
    var loc =
      nf.location ||
      pq.location ||
      nf.area ||
      pq.area ||
      nf.postcode ||
      pq.postcode ||
      "—";
    var minP = nf.min_price != null ? nf.min_price : pq.min_price;
    var maxP = nf.max_price != null ? nf.max_price : pq.max_price;
    var budget = "—";
    if (minP != null && maxP != null) {
      budget = "£" + minP + " – " + maxP + "/月";
    } else if (maxP != null) {
      budget = "≤ £" + maxP + "/月";
    } else if (minP != null) {
      budget = "≥ £" + minP + "/月";
    }
    return truncate(String(loc) + " · " + budget, 160);
  }

  function housingPreview(data) {
    var rep = data.recommendation_report || {};
    var v = rep.star_final_verdict || {};
    if (v && typeof v === "object" && v.overall_advice) {
      return truncate(String(v.overall_advice), 200);
    }
    var snap = rep.market_snapshot_zh;
    if (snap && String(snap).trim()) {
      return truncate(String(snap).trim(), 200);
    }
    if (data.message && String(data.message).trim()) {
      return truncate(String(data.message), 200);
    }
    return "房源分析已完成";
  }

  /**
   * @param {object} data — POST /api/ai/query 成功体（housing）
   * @returns {object|null}
   */
  function pushPropertyFromHousingData(data) {
    if (!data || data.success === false) return null;
    if (typeof data.user_text !== "string") return null;
    try {
      var raw = sessionStorage.getItem("ai_housing_query_last");
      if (!raw) return null;
      var mark = sessionStorage.getItem(DEDUP_HOUSING);
      if (mark === raw) return null;
      sessionStorage.setItem(DEDUP_HOUSING, raw);
    } catch (e) {
      return null;
    }

    var entry = {
      id: newId("p"),
      type: "property",
      title: truncate(data.user_text, 100),
      created_at: new Date().toISOString(),
      summary_snippet: housingSnippet(data),
      result_preview: housingPreview(data),
    };
    prepend(entry);
    return entry;
  }

  /**
   * @param {object} data — 旧版 ai-analyze 成功体
   */
  function pushPropertyFromLegacyData(data) {
    if (!data || !data.success) return null;
    try {
      var raw = sessionStorage.getItem("ai_analyze_last");
      if (!raw) return null;
      var mark = sessionStorage.getItem(DEDUP_LEGACY);
      if (mark === raw) return null;
      sessionStorage.setItem(DEDUP_LEGACY, raw);
    } catch (e) {
      return null;
    }

    var sum = data.summary || {};
    var recos = data.recommendations || [];
    var first = recos.length ? recos[0] : {};
    var preview =
      (first.title || first.house_label || sum.note || "—") + "";
    var entry = {
      id: newId("p"),
      type: "property",
      title: truncate(data.raw_user_query || "房源分析", 100),
      created_at: new Date().toISOString(),
      summary_snippet: truncate(
        "Legacy · 候选 " +
          (sum.total_candidates != null ? sum.total_candidates : "—") +
          " 套",
        160
      ),
      result_preview: truncate(preview, 200),
    };
    prepend(entry);
    return entry;
  }

  function contractTitle(sourceMeta) {
    if (!sourceMeta || !sourceMeta.kind) return "合同分析";
    if (sourceMeta.kind === "text") return "粘贴文本";
    if (sourceMeta.kind === "upload") {
      return truncate(sourceMeta.label || "上传文件", 80);
    }
    if (sourceMeta.kind === "path") {
      return truncate(sourceMeta.label || "服务端路径", 80);
    }
    return "合同分析";
  }

  /**
   * @param {object} data — normalize 后的合同 API JSON（ok === true）
   * @param {object} [sourceMeta] — 与 contract_analysis_api 一致
   */
  function pushContractFromContractData(data, sourceMeta) {
    if (!data || data.ok !== true) return null;
    var res = (data && data.result) || {};
    var sv = res.summary_view || {};
    var oc = typeof sv.overall_conclusion === "string" ? sv.overall_conclusion.trim() : "";
    var kr = typeof sv.key_risk_summary === "string" ? sv.key_risk_summary.trim() : "";
    var entry = {
      id: newId("c"),
      type: "contract",
      title: contractTitle(sourceMeta),
      created_at: new Date().toISOString(),
      summary_snippet: truncate(kr || oc || "合同分析完成", 160),
      result_preview: truncate(oc || kr || "—", 200),
    };
    prepend(entry);
    return entry;
  }

  function listForUser() {
    var uid = getUserId();
    var all = loadRaw();
    if (!uid) {
      return all.filter(function (x) {
        return x && !x.user_id;
      });
    }
    return all.filter(function (x) {
      return x && (x.user_id === uid || !x.user_id);
    });
  }

  function listByType(type) {
    return listForUser().filter(function (x) {
      return x && x.type === type;
    });
  }

  global.RentalAIAnalysisHistoryStore = {
    STORAGE_KEY: STORAGE_KEY,
    pushPropertyFromHousingData: pushPropertyFromHousingData,
    pushPropertyFromLegacyData: pushPropertyFromLegacyData,
    pushContractFromContractData: pushContractFromContractData,
    listForUser: listForUser,
    listByType: listByType,
    loadRaw: loadRaw,
  };
})(window);
