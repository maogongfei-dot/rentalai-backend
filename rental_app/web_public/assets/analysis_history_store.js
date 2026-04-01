/**
 * Phase 4 Round6 + Phase 5 Step5：统一「最近分析」localStorage，按 userId 分桶（guest | 已登录）。
 * 键：rentalai_unified_analysis_history_v1__{bucketId}；与 analysis_history__{bucketId} 手动保存并存。
 */
(function (global) {
  var STORAGE_PREFIX = "rentalai_unified_analysis_history_v1";
  var MAX_ITEMS = 50;
  var DEDUP_HOUSING = "rentalai_unified_hist_dedup_property";
  var DEDUP_LEGACY = "rentalai_unified_hist_dedup_legacy";

  function getBucketId() {
    try {
      if (global.RentalAIUserStore && typeof global.RentalAIUserStore.getHistoryBucketId === "function") {
        return global.RentalAIUserStore.getHistoryBucketId();
      }
    } catch (e) {}
    return "guest";
  }

  function getUnifiedStorageKey() {
    try {
      if (global.RentalAIUserStore && typeof global.RentalAIUserStore.getUnifiedHistoryStorageKey === "function") {
        return global.RentalAIUserStore.getUnifiedHistoryStorageKey();
      }
    } catch (e2) {}
    return STORAGE_PREFIX + "__" + getBucketId();
  }

  function getDedupHousingKey() {
    return DEDUP_HOUSING + "_" + getBucketId();
  }

  function getDedupLegacyKey() {
    return DEDUP_LEGACY + "_" + getBucketId();
  }

  /** 仅 guest：旧无后缀键一次性迁到 __guest */
  function migrateLegacyUnifiedIfNeeded() {
    if (getBucketId() !== "guest") return;
    var newKey = getUnifiedStorageKey();
    if (localStorage.getItem(newKey)) return;
    var legacy = localStorage.getItem(STORAGE_PREFIX);
    if (!legacy) return;
    try {
      localStorage.setItem(newKey, legacy);
      localStorage.removeItem(STORAGE_PREFIX);
    } catch (e) {}
  }

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
    migrateLegacyUnifiedIfNeeded();
    try {
      var raw = localStorage.getItem(getUnifiedStorageKey());
      var arr = raw ? JSON.parse(raw) : [];
      return Array.isArray(arr) ? arr : [];
    } catch (e) {
      return [];
    }
  }

  function saveRaw(arr) {
    try {
      localStorage.setItem(getUnifiedStorageKey(), JSON.stringify(arr));
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

  var DETAIL_STR_MAX = 12000;

  function clipStr(s, max) {
    s = s == null ? "" : String(s);
    max = max || DETAIL_STR_MAX;
    if (s.length <= max) return s;
    return s.slice(0, max - 1) + "…";
  }

  function buildContractDetailSnapshot(data) {
    var res = (data && data.result) || {};
    var sv = res.summary_view || {};
    var cc = sv.contract_completeness_overview;
    var ccOut = null;
    if (cc && typeof cc === "object") {
      ccOut = {
        overall_status: clipStr(cc.overall_status, 500),
        completeness_score: cc.completeness_score,
        short_summary: clipStr(cc.short_summary, 4000),
        missing_core_items: Array.isArray(cc.missing_core_items)
          ? cc.missing_core_items.slice(0, 24).map(function (x) {
              return clipStr(x, 800);
            })
          : [],
        unclear_items: Array.isArray(cc.unclear_items)
          ? cc.unclear_items.slice(0, 24).map(function (x) {
              return clipStr(x, 800);
            })
          : [],
      };
    }
    return {
      overall_conclusion: clipStr(
        typeof sv.overall_conclusion === "string" ? sv.overall_conclusion : "",
        8000
      ),
      key_risk_summary: clipStr(
        typeof sv.key_risk_summary === "string" ? sv.key_risk_summary : "",
        8000
      ),
      contract_completeness_overview: ccOut,
    };
  }

  function buildPropertyHousingDetailSnapshot(data) {
    var rep = data.recommendation_report || {};
    var v = rep.star_final_verdict || {};
    var td = (data.top_deals && data.top_deals.top_deals) || [];
    var deals = [];
    var i;
    for (i = 0; i < Math.min(5, td.length); i++) {
      var d = td[i] || {};
      deals.push({
        title: clipStr(d.title || d.address || "—", 300),
        star_rating: d.star_rating,
        one_line_suggestion: clipStr(d.one_line_suggestion || "", 500),
      });
    }
    return {
      variant: "housing",
      market_snapshot_zh: clipStr(rep.market_snapshot_zh || "", 8000),
      star_final_verdict: {
        overall_advice: clipStr(v.overall_advice || "", 4000),
        best_overall: v.best_overall && typeof v.best_overall === "object" ? v.best_overall : null,
        best_for_price: v.best_for_price && typeof v.best_for_price === "object" ? v.best_for_price : null,
        best_for_environment_safety:
          v.best_for_environment_safety && typeof v.best_for_environment_safety === "object"
            ? v.best_for_environment_safety
            : null,
      },
      top_deals: deals,
    };
  }

  function buildPropertyLegacyDetailSnapshot(data) {
    var recos = data.recommendations || [];
    var top = [];
    var i;
    for (i = 0; i < Math.min(5, recos.length); i++) {
      var r = recos[i] || {};
      top.push({
        title: clipStr(r.title || r.house_label || "—", 300),
        final_score: r.final_score,
        decision: r.decision,
        decision_reason: clipStr(r.decision_reason || "", 1500),
      });
    }
    var sum = data.summary || {};
    return {
      variant: "legacy",
      summary: {
        total_candidates: sum.total_candidates,
        top_count: sum.top_count,
      },
      recommendations_top: top,
    };
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

  function pushPropertyFromHousingData(data) {
    if (!data || data.success === false) return null;
    if (typeof data.user_text !== "string") return null;
    try {
      var raw = sessionStorage.getItem("ai_housing_query_last");
      if (!raw) return null;
      var mark = sessionStorage.getItem(getDedupHousingKey());
      if (mark === raw) return null;
      sessionStorage.setItem(getDedupHousingKey(), raw);
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
      detail_snapshot: buildPropertyHousingDetailSnapshot(data),
    };
    prepend(entry);
    return entry;
  }

  function pushPropertyFromLegacyData(data) {
    if (!data || !data.success) return null;
    try {
      var raw = sessionStorage.getItem("ai_analyze_last");
      if (!raw) return null;
      var mark = sessionStorage.getItem(getDedupLegacyKey());
      if (mark === raw) return null;
      sessionStorage.setItem(getDedupLegacyKey(), raw);
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
      detail_snapshot: buildPropertyLegacyDetailSnapshot(data),
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
      detail_snapshot: buildContractDetailSnapshot(data),
    };
    prepend(entry);
    return entry;
  }

  function listForUser() {
    return loadRaw();
  }

  function listByType(type) {
    return listForUser().filter(function (x) {
      return x && x.type === type;
    });
  }

  function clearCurrentBucket() {
    try {
      localStorage.removeItem(getUnifiedStorageKey());
      sessionStorage.removeItem(getDedupHousingKey());
      sessionStorage.removeItem(getDedupLegacyKey());
    } catch (e) {}
  }

  global.RentalAIAnalysisHistoryStore = {
    STORAGE_PREFIX: STORAGE_PREFIX,
    getBucketId: getBucketId,
    getUnifiedStorageKey: getUnifiedStorageKey,
    pushPropertyFromHousingData: pushPropertyFromHousingData,
    pushPropertyFromLegacyData: pushPropertyFromLegacyData,
    pushContractFromContractData: pushContractFromContractData,
    listForUser: listForUser,
    listByType: listByType,
    loadRaw: loadRaw,
    clearCurrentBucket: clearCurrentBucket,
  };
})(window);
