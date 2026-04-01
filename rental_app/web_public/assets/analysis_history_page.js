/**
 * Phase 4 Round6：/analysis-history — 统一历史列表 + detail_snapshot 展开回看。
 * Phase 5 Round4：优先经 RentalAIAnalysisHistorySource.loadAnalysisHistory（guest→本地，已登录→云端优先，失败回退本地）。
 */
(function () {
  var S = window.RentalAIAnalysisHistoryStore;
  if (!S || typeof S.listByType !== "function") return;

  function escapeHtml(s) {
    var d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  function fmtTime(iso) {
    if (!iso) return "—";
    try {
      var d = new Date(iso);
      if (isNaN(d.getTime())) return String(iso);
      return d.toLocaleString("zh-CN", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch (e) {
      return String(iso);
    }
  }

  function safeStr(x) {
    return x == null ? "" : String(x);
  }

  function renderEmpty(emptyHint) {
    return (
      '<div class="card empty-state-card unified-history-empty-state" role="status">' +
      "<strong>暂无记录</strong>" +
      '<p class="hint muted unified-history-empty">' +
      escapeHtml(emptyHint) +
      "</p>" +
      "</div>"
    );
  }

  function verdictPickHtml(label, pick) {
    if (!pick || !pick.title) {
      return (
        '<div class="verdict-pick unified-history-verdict-pick">' +
        '<div class="verdict-pick-label">' +
        escapeHtml(label) +
        "</div>" +
        '<p class="verdict-pick-body hint">暂无对应候选。</p>' +
        "</div>"
      );
    }
    return (
      '<div class="verdict-pick unified-history-verdict-pick">' +
      '<div class="verdict-pick-label">' +
      escapeHtml(label) +
      "</div>" +
      '<p class="verdict-pick-title"><strong>' +
      escapeHtml(pick.title) +
      "</strong></p>" +
      '<p class="verdict-pick-body">' +
      escapeHtml(pick.line || "") +
      "</p>" +
      "</div>"
    );
  }

  function renderHousingDetail(d) {
    if (!d || d.variant !== "housing") {
      return '<p class="hint muted">暂无房源详情快照。</p>';
    }
    var v = d.star_final_verdict || {};
    var html =
      '<div class="unified-history-detail-section">' +
      '<span class="history-record-label">市场摘要</span>' +
      '<p class="history-cond-v unified-history-detail-text">' +
      (d.market_snapshot_zh
        ? escapeHtml(d.market_snapshot_zh)
        : '<span class="hint">—</span>') +
      "</p>" +
      "</div>" +
      '<div class="unified-history-detail-section">' +
      '<span class="history-record-label">星级结论 / 推荐</span>' +
      '<div class="star-final-verdict unified-history-verdict-wrap">' +
      verdictPickHtml("最推荐的一套（星数高、租价也相对划算）", v.best_overall) +
      verdictPickHtml("价格最友好的一套", v.best_for_price) +
      verdictPickHtml("更稳妥的一套（资料更齐）", v.best_for_environment_safety) +
      '<div class="verdict-overall">' +
      '<div class="verdict-pick-label">一句话结论</div>' +
      '<p class="verdict-overall-text">' +
      escapeHtml(v.overall_advice || "—") +
      "</p>" +
      "</div>" +
      "</div>" +
      "</div>";

    var deals = d.top_deals || [];
    if (deals.length) {
      html += '<div class="unified-history-detail-section">';
      html += '<span class="history-record-label">Top 房源摘要（星级 / 建议）</span>';
      html += '<ul class="unified-history-mini-deals">';
      for (var i = 0; i < deals.length; i++) {
        var x = deals[i];
        html += "<li>";
        html += "<strong>" + escapeHtml(x.title || "—") + "</strong>";
        if (x.star_rating != null) {
          html +=
            ' <span class="hint muted">· ' + escapeHtml(String(x.star_rating)) + " 星</span>";
        }
        if (x.one_line_suggestion) {
          html +=
            '<p class="hint unified-history-mini-sug">' +
            escapeHtml(x.one_line_suggestion) +
            "</p>";
        }
        html += "</li>";
      }
      html += "</ul></div>";
    }
    return html;
  }

  function renderLegacyDetail(d) {
    if (!d || d.variant !== "legacy") {
      return '<p class="hint muted">暂无 Legacy 详情快照。</p>';
    }
    var sum = d.summary || {};
    var html =
      '<div class="unified-history-detail-section">' +
      '<span class="history-record-label">候选 / Top</span>' +
      "<p>" +
      "候选 " +
      escapeHtml(safeStr(sum.total_candidates != null ? sum.total_candidates : "—")) +
      " 套 · 展示 Top " +
      escapeHtml(safeStr(sum.top_count != null ? sum.top_count : "—")) +
      "</p>" +
      "</div>";
    var rec = d.recommendations_top || [];
    if (rec.length) {
      html += '<div class="unified-history-detail-section">';
      html += '<span class="history-record-label">推荐与决策</span>';
      html += '<ul class="unified-history-mini-deals">';
      for (var i = 0; i < rec.length; i++) {
        var r = rec[i];
        html += "<li><strong>" + escapeHtml(r.title || "—") + "</strong>";
        if (r.final_score != null) {
          html += ' <span class="hint muted">· 分 ' + escapeHtml(String(r.final_score)) + "</span>";
        }
        if (r.decision) {
          html +=
            ' <span class="unified-history-decision">' + escapeHtml(String(r.decision)) + "</span>";
        }
        if (r.decision_reason) {
          html +=
            '<p class="hint unified-history-mini-sug">' +
            escapeHtml(r.decision_reason) +
            "</p>";
        }
        html += "</li>";
      }
      html += "</ul></div>";
    }
    return html;
  }

  function renderContractDetail(d) {
    if (!d || typeof d !== "object") {
      return '<p class="hint muted">暂无合同详情快照。</p>';
    }
    var html =
      '<div class="unified-history-detail-section">' +
      '<span class="history-record-label">Overall conclusion</span>' +
      '<p class="history-cond-v unified-history-detail-text">' +
      escapeHtml(d.overall_conclusion || "—") +
      "</p>" +
      "</div>" +
      '<div class="unified-history-detail-section">' +
      '<span class="history-record-label">Key risk summary</span>' +
      '<p class="history-cond-v unified-history-detail-text">' +
      escapeHtml(d.key_risk_summary || "—") +
      "</p>" +
      "</div>";

    var cc = d.contract_completeness_overview;
    if (!cc || typeof cc !== "object") {
      html +=
        '<div class="unified-history-detail-section">' +
        '<span class="history-record-label">Contract completeness</span>' +
        '<p class="hint muted">暂无完整性结构数据</p>' +
        "</div>";
      return html;
    }

    html += '<div class="unified-history-detail-section">';
    html += '<span class="history-record-label">Contract completeness overview</span>';
    html += '<div class="unified-history-complete">';
    if (cc.overall_status || cc.completeness_score != null) {
      html += '<p class="unified-history-complete-top">';
      if (cc.overall_status) {
        html +=
          '<span class="contract-result-pill contract-result-pill--status">' +
          escapeHtml(String(cc.overall_status)) +
          "</span> ";
      }
      if (cc.completeness_score != null) {
        html +=
          '<span class="contract-result-pill contract-result-pill--muted">完整性分 ' +
          escapeHtml(String(cc.completeness_score)) +
          "</span>";
      }
      html += "</p>";
    }
    if (cc.short_summary) {
      html +=
        '<p class="contract-result-text contract-result-complete-summary">' +
        escapeHtml(cc.short_summary) +
        "</p>";
    }
    var miss = cc.missing_core_items || [];
    var unc = cc.unclear_items || [];
    if (miss.length) {
      html += '<div class="unified-history-subh">缺失核心项</div><ul class="unified-history-bullets">';
      for (var i = 0; i < miss.length; i++) {
        html += "<li>" + escapeHtml(miss[i]) + "</li>";
      }
      html += "</ul>";
    }
    if (unc.length) {
      html += '<div class="unified-history-subh">不明确项</div><ul class="unified-history-bullets">';
      for (var j = 0; j < unc.length; j++) {
        html += "<li>" + escapeHtml(unc[j]) + "</li>";
      }
      html += "</ul>";
    }
    html += "</div></div>";
    return html;
  }

  /** 云端 JSON 写入的房源历史（无本地 housing 大快照） */
  function renderRemotePropertyDetail(snap) {
    if (!snap || snap.variant !== "remote_property") {
      return '<p class="hint muted">暂无云端房源详情字段。</p>';
    }
    var html =
      '<div class="unified-history-detail-section">' +
      '<span class="history-record-label">来源</span>' +
      '<p class="hint muted">服务端 JSON 历史（摘要级）</p>' +
      "</div>";
    if (snap.user_text_preview) {
      html +=
        '<div class="unified-history-detail-section">' +
        '<span class="history-record-label">需求摘要</span>' +
        '<p class="history-cond-v unified-history-detail-text">' +
        escapeHtml(snap.user_text_preview) +
        "</p></div>";
    }
    if (snap.market_summary_title) {
      html +=
        '<div class="unified-history-detail-section">' +
        '<span class="history-record-label">市场摘要标题</span>' +
        '<p class="history-cond-v unified-history-detail-text">' +
        escapeHtml(snap.market_summary_title) +
        "</p></div>";
    }
    if (snap.top_deal_count != null) {
      html +=
        '<div class="unified-history-detail-section">' +
        '<span class="history-record-label">Top 条数</span>' +
        "<p>" +
        escapeHtml(String(snap.top_deal_count)) +
        "</p></div>";
    }
    if (snap.result_snapshot && typeof snap.result_snapshot === "object") {
      var rs = snap.result_snapshot;
      if (rs.parsed_intent != null || rs.message != null) {
        html += '<div class="unified-history-detail-section"><span class="history-record-label">快照</span>';
        if (rs.message) {
          html += '<p class="hint">' + escapeHtml(String(rs.message)) + "</p>";
        }
        if (rs.parsed_intent != null) {
          html += '<p class="hint muted">intent: ' + escapeHtml(String(rs.parsed_intent)) + "</p>";
        }
        html += "</div>";
      }
    }
    return html;
  }

  function renderDetailBody(it) {
    var snap = it.detail_snapshot;
    if (!snap) {
      return (
        '<p class="hint muted unified-history-no-snapshot">' +
        "该条为旧版记录，保存时未含详情快照；请重新做一次分析以生成可展开内容。" +
        "</p>"
      );
    }
    if (it.type === "contract") {
      return renderContractDetail(snap);
    }
    if (it.type === "property") {
      if (snap.variant === "housing") return renderHousingDetail(snap);
      if (snap.variant === "legacy") return renderLegacyDetail(snap);
      if (snap.variant === "remote_property") return renderRemotePropertyDetail(snap);
      return '<p class="hint muted">未知房源快照格式。</p>';
    }
    return '<p class="hint muted">未知记录类型。</p>';
  }

  function renderItem(it, idx) {
    var title = it.title || "—";
    var iso = it.created_at || "";
    var displayTime = fmtTime(iso);
    var snippet = it.summary_snippet != null && String(it.summary_snippet).trim() ? "" + it.summary_snippet : "—";
    var preview = it.result_preview != null && String(it.result_preview).trim() ? "" + it.result_preview : "—";
    var detailId = "uh-detail-" + String(it.id || idx).replace(/[^a-zA-Z0-9_-]/g, "_");

    return (
      '<li class="unified-history-item history-record-card" role="listitem">' +
      '<div class="unified-history-item-head">' +
      '<h3 class="history-record-top-title">' +
      escapeHtml(title) +
      "</h3>" +
      (iso
        ? '<time class="history-record-time" datetime="' +
          escapeHtml(iso) +
          '">' +
          escapeHtml(displayTime) +
          "</time>"
        : '<span class="history-record-time">' + escapeHtml(displayTime) + "</span>") +
      "</div>" +
      '<div class="unified-history-fields">' +
      '<div class="unified-history-field">' +
      '<span class="history-record-label">摘要</span>' +
      '<p class="history-cond-v unified-history-snippet">' +
      escapeHtml(snippet) +
      "</p>" +
      "</div>" +
      '<div class="unified-history-field">' +
      '<span class="history-record-label">要点 / 结论</span>' +
      '<p class="history-cond-v unified-history-preview">' +
      escapeHtml(preview) +
      "</p>" +
      "</div>" +
      "</div>" +
      '<details class="unified-history-details">' +
      '<summary class="unified-history-details-summary">查看详情 · 关键结果</summary>' +
      '<div class="unified-history-details-body" id="' +
      escapeHtml(detailId) +
      '">' +
      renderDetailBody(it) +
      "</div>" +
      "</details>" +
      "</li>"
    );
  }

  function renderList(container, items, emptyHint, countSourceLabel) {
    if (!container) return;
    container.setAttribute("aria-busy", "false");
    if (!items || !items.length) {
      container.innerHTML = renderEmpty(emptyHint);
      container.setAttribute("data-unified-history-state", "empty");
      return;
    }
    var n = items.length;
    var csl = countSourceLabel != null && String(countSourceLabel).trim() ? String(countSourceLabel).trim() : "自动保存";
    var html =
      '<p class="unified-history-count hint muted" aria-live="polite">共 ' +
      n +
      " 条记录（" +
      escapeHtml(csl) +
      "）</p>" +
      '<ul class="unified-history-list" role="list">';
    var i;
    for (i = 0; i < items.length; i++) {
      html += renderItem(items[i], i);
    }
    html += "</ul>";
    container.innerHTML = html;
    container.setAttribute("data-unified-history-state", "populated");
  }

  function renderLoading(container) {
    if (!container) return;
    container.innerHTML =
      '<div class="unified-history-loading" role="status">正在从服务器加载云端历史…</div>';
    container.setAttribute("data-unified-history-state", "loading");
    container.setAttribute("aria-busy", "true");
  }

  var _defaultAnalysisLeadHtml = null;

  function resetAnalysisLead() {
    var lead = document.getElementById("analysis-history-lead");
    if (!lead || _defaultAnalysisLeadHtml === null) return;
    lead.innerHTML = _defaultAnalysisLeadHtml;
  }

  function setAnalysisLeadCloud() {
    var lead = document.getElementById("analysis-history-lead");
    if (!lead) return;
    lead.innerHTML =
      "已登录：下列为<strong>服务端 JSON 历史</strong>（与本地自动摘要分源；本地仍可在未登录或回退时查看）。";
  }

  function setServerNotice(msg) {
    var n = document.getElementById("history-server-notice");
    if (!n) return;
    if (!msg || !String(msg).trim()) {
      n.textContent = "";
      n.classList.add("hidden");
      return;
    }
    n.textContent = String(msg).trim();
    n.classList.remove("hidden");
  }

  function run() {
    if (
      window.RentalAIHistoryAccess &&
      typeof window.RentalAIHistoryAccess.applyBannerById === "function"
    ) {
      window.RentalAIHistoryAccess.applyBannerById("history-access-banner");
    }
    var leadEl = document.getElementById("analysis-history-lead");
    if (leadEl && _defaultAnalysisLeadHtml === null) {
      _defaultAnalysisLeadHtml = leadEl.innerHTML;
    }

    var propEl = document.getElementById("unified-history-property-list");
    var contractEl = document.getElementById("unified-history-contract-list");
    var emptyProp =
      "暂无记录。完成房源分析并进入结果页后，将自动在此出现摘要；展开「查看详情」可回看本地保存的结论与市场摘要。";
    var emptyContract =
      "暂无记录。合同分析提交成功后，将自动在此出现摘要；展开「查看详情」可回看结论、风险与完整性要点。";

    function renderFromLocal() {
      resetAnalysisLead();
      setServerNotice("");
      renderList(propEl, S.listByType("property"), emptyProp, "本地自动保存");
      renderList(contractEl, S.listByType("contract"), emptyContract, "本地自动保存");
    }

    var strat =
      window.RentalAIAnalysisHistorySource &&
      typeof window.RentalAIAnalysisHistorySource.resolveHistoryMode === "function"
        ? window.RentalAIAnalysisHistorySource.resolveHistoryMode()
        : null;
    var isRemote = strat && strat.mode === "remote_user";

    if (isRemote && propEl && contractEl) {
      renderLoading(propEl);
      renderLoading(contractEl);
      setServerNotice("");
    } else {
      resetAnalysisLead();
      setServerNotice("");
    }

    if (
      window.RentalAIAnalysisHistorySource &&
      typeof window.RentalAIAnalysisHistorySource.loadAnalysisHistory === "function"
    ) {
      window.RentalAIAnalysisHistorySource
        .loadAnalysisHistory()
        .then(function (bundle) {
          if (!bundle || !Array.isArray(bundle.propertyRecords) || !Array.isArray(bundle.contractRecords)) {
            renderFromLocal();
            return;
          }
          try {
            var main = document.querySelector(".analysis-history-page");
            if (main) {
              main.setAttribute("data-history-source-mode", bundle.mode || "");
              main.setAttribute("data-history-used-fallback", bundle.usedFallback ? "1" : "0");
            }
          } catch (eMain) {}
          if (bundle.mode === "local_guest") {
            resetAnalysisLead();
            setServerNotice("");
          } else if (bundle.mode === "remote_user") {
            if (bundle.usedFallback) {
              resetAnalysisLead();
              setServerNotice(
                "云端历史暂时不可用，已显示本机缓存（" + (bundle.message || "error") + "）。"
              );
            } else {
              setAnalysisLeadCloud();
              setServerNotice("");
            }
          }
          var label =
            bundle.mode === "remote_user"
              ? bundle.usedFallback
                ? "本机回退（云端不可用）"
                : "服务端 JSON 历史"
              : "本地 guest 自动保存";
          renderList(propEl, bundle.propertyRecords, emptyProp, label);
          renderList(contractEl, bundle.contractRecords, emptyContract, label);
        })
        .catch(function () {
          setServerNotice("加载失败，已显示本机历史。");
          renderFromLocal();
        });
    } else {
      renderFromLocal();
    }

    try {
      if (
        window.location.search.indexOf("server_history=1") >= 0 &&
        window.RentalAIServerHistoryApi &&
        typeof window.RentalAIServerHistoryApi.fetchUserHistory === "function" &&
        window.RentalAIUserStore &&
        typeof window.RentalAIUserStore.getHistoryBucketId === "function"
      ) {
        var bucket = window.RentalAIUserStore.getHistoryBucketId();
        window.RentalAIServerHistoryApi.fetchUserHistory(bucket, {}).then(function (j) {
          console.info("[RentalAI] server history probe (GET /api/analysis/history/records)", bucket, j);
        });
      }
    } catch (e) {}
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run);
  } else {
    run();
  }
})();
