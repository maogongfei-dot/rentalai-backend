/**
 * Phase 4 Round6：/analysis-history — 统一历史列表 + detail_snapshot 展开回看。
 * Phase 5 Round4：RentalAIAnalysisHistorySource.loadAnalysisHistory；data-history-source-mode / 来源文案见 history_access_context。
 * 双模式收尾：未改列表行为，仅与 persist/source/API 对齐；能力边界见 rental_app/README.md「Phase 5 第四轮」。
 * Phase 5 Round5 Step4：cloudAuthStatus 提示（#history-cloud-load-hint / #history-server-notice），token 仅在 server_history_api 注入。
 * Phase 6 Round4：刷新按钮 + 保存后 sessionStorage 触发 GET cache-bust；pageshow(bfcache) 重载。
 * Phase 7 Round3：每条「删除」— 已登录云端走 DELETE API；guest/本机回退走 removeEntryById。
 * Phase 7 Round4：「清空全部」— guest 清本地桶；已登录调 DELETE /api/analysis/history/clear。
 * Phase 7 Round5：类型筛选（全部 / 房源 / 合同）— 仅前端切换两个 section 显隐，不调后端。
 */
(function () {
  var S = window.RentalAIAnalysisHistoryStore;
  if (!S || typeof S.listByType !== "function") return;

  try {
    if (typeof window.RentalAIServerFavoritesApi === "undefined") {
      var xhrF = new XMLHttpRequest();
      xhrF.open("GET", "/assets/server_favorites_api.js", false);
      xhrF.send(null);
      if (xhrF.status === 200 && xhrF.responseText) {
        (0, Function)(xhrF.responseText)();
      }
    }
  } catch (eFavLoad) {}

  var _uhFavBound = false;

  function uhFavStorageKey() {
    return window.RentalAILocalAuth && window.RentalAILocalAuth.favStorageKey
      ? window.RentalAILocalAuth.favStorageKey()
      : "fav_list";
  }

  function uhSyncLocalFavList(propertyKey, add) {
    var key = propertyKey != null ? String(propertyKey) : "";
    if (!key) return;
    try {
      var favs = JSON.parse(localStorage.getItem(uhFavStorageKey()) || "[]");
      if (!Array.isArray(favs)) favs = [];
      var ix = favs.indexOf(key);
      if (add) {
        if (ix < 0) favs.push(key);
      } else if (ix >= 0) {
        favs.splice(ix, 1);
      }
      localStorage.setItem(uhFavStorageKey(), JSON.stringify(favs));
    } catch (e0) {}
  }

  function uhFavBtnHtmlHousing(x, i) {
    var listUrl = (x.listing_url || "").trim();
    var propId = String(i + 1);
    var api = window.RentalAIServerFavoritesApi;
    var fk =
      api && typeof api.buildFavoriteKey === "function"
        ? api.buildFavoriteKey({
            listing_url: listUrl,
            property_id: listUrl ? undefined : propId,
            rank: i + 1,
          })
        : propId;
    return (
      '<button type="button" class="uh-fav-btn hint" data-id="' +
      escapeAttr(propId) +
      '" data-property-id="' +
      escapeAttr(propId) +
      '" data-listing-url="' +
      escapeAttr(listUrl) +
      '" data-title="' +
      escapeAttr(x.title || "—") +
      '" data-favorite-key="' +
      escapeAttr(fk) +
      '" data-server-favorite-id="">' +
      "⭐ 收藏" +
      "</button> "
    );
  }

  function uhFavBtnHtmlLegacy(r, i) {
    var listUrl = (r.source_url || "").trim();
    var pid = String(r.listing_id != null ? r.listing_id : r.rank != null ? r.rank : i + 1);
    var api = window.RentalAIServerFavoritesApi;
    var fk =
      api && typeof api.buildFavoriteKey === "function"
        ? api.buildFavoriteKey({
            listing_url: listUrl,
            source_url: r.source_url,
            property_id: pid,
            listing_id: r.listing_id,
            rank: r.rank,
          })
        : pid;
    return (
      '<button type="button" class="uh-fav-btn hint" data-id="' +
      escapeAttr(pid) +
      '" data-property-id="' +
      escapeAttr(pid) +
      '" data-listing-url="' +
      escapeAttr(listUrl) +
      '" data-title="' +
      escapeAttr(r.title || "—") +
      '" data-favorite-key="' +
      escapeAttr(fk) +
      '" data-server-favorite-id="">' +
      "⭐ 收藏" +
      "</button> "
    );
  }

  function applyUhFavButtons(rows) {
    rows = rows || [];
    var api = window.RentalAIServerFavoritesApi;
    if (!api || typeof api.favoriteMatchesIdentifiers !== "function") return;
    var buttons = document.querySelectorAll(".uh-fav-btn");
    for (var b = 0; b < buttons.length; b++) {
      var btn = buttons[b];
      var pid = (btn.getAttribute("data-property-id") || "").trim();
      var url = (btn.getAttribute("data-listing-url") || "").trim();
      var found = null;
      for (var j = 0; j < rows.length; j++) {
        if (api.favoriteMatchesIdentifiers(rows[j], pid, url)) {
          found = rows[j];
          break;
        }
      }
      if (found && found.id) {
        btn.setAttribute("data-server-favorite-id", found.id);
        btn.textContent = "✅ 已收藏";
      } else {
        btn.setAttribute("data-server-favorite-id", "");
        btn.textContent = "⭐ 收藏";
      }
    }
  }

  function hydrateUnifiedHistoryFavoriteButtons() {
    var api = window.RentalAIServerFavoritesApi;
    if (!api || typeof api.refreshFavoritesCache !== "function") return;
    api
      .refreshFavoritesCache(200)
      .then(function (rows) {
        if (rows) applyUhFavButtons(rows);
      })
      .catch(function () {});
  }

  function bindUnifiedHistoryFavoritesOnce() {
    if (_uhFavBound) return;
    _uhFavBound = true;
    document.addEventListener("click", function (ev) {
      var btn = ev.target && ev.target.closest && ev.target.closest(".uh-fav-btn");
      if (!btn) return;
      var api = window.RentalAIServerFavoritesApi;
      if (!api || typeof api.addFavorite !== "function") return;
      var sid = (btn.getAttribute("data-server-favorite-id") || "").trim();
      var propKey = btn.getAttribute("data-id");
      var localFavKey = (btn.getAttribute("data-favorite-key") || "").trim() || propKey;
      if (sid) {
        api
          .removeFavorite(sid)
          .then(function () {
            btn.setAttribute("data-server-favorite-id", "");
            btn.textContent = "⭐ 收藏";
            uhSyncLocalFavList(localFavKey, false);
          })
          .catch(function (err) {
            console.error(err);
          });
        return;
      }
      var payload = {
        propertyId: (btn.getAttribute("data-property-id") || "").trim(),
        listing_url: (btn.getAttribute("data-listing-url") || "").trim() || null,
        title: (btn.getAttribute("data-title") || "").trim() || "Listing",
      };
      api
        .addFavorite(payload)
        .then(function (res) {
          var fav = res && res.favorite;
          if (fav && fav.id) btn.setAttribute("data-server-favorite-id", fav.id);
          btn.textContent = "✅ 已收藏";
          uhSyncLocalFavList(localFavKey, true);
        })
        .catch(function (err) {
          if (err && err.status === 409 && typeof api.refreshFavoritesCache === "function") {
            api
              .refreshFavoritesCache(200)
              .then(function (rows) {
                if (!rows) return;
                for (var j = 0; j < rows.length; j++) {
                  var f = rows[j];
                  if (
                    f &&
                    f.id &&
                    api.favoriteMatchesIdentifiers(
                      f,
                      (payload.propertyId || "").trim(),
                      (payload.listing_url || "").trim()
                    )
                  ) {
                    btn.setAttribute("data-server-favorite-id", f.id);
                    btn.textContent = "✅ 已收藏";
                    uhSyncLocalFavList(localFavKey, true);
                    return;
                  }
                }
              })
              .catch(function (e2) {
                console.error(e2);
              });
            return;
          }
          console.error(err);
        });
    });
    try {
      window.addEventListener("rentalai-favorites-updated", function (ev) {
        var d = ev && ev.detail;
        var rows = d && d.favorites;
        if (rows) applyUhFavButtons(rows);
      });
    } catch (e1) {}
  }

  var _refreshClickBound = false;
  var _clearAllClickBound = false;
  var _deleteDelegateBound = false;
  var _filterBound = false;
  /** @type {'all'|'property'|'contract'} */
  var _historyFilter = "all";

  function escapeHtml(s) {
    var d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  function escapeAttr(s) {
    return String(s == null ? "" : String(s))
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/</g, "&lt;");
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
        html += uhFavBtnHtmlHousing(x, i);
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
        html += "<li>";
        html += uhFavBtnHtmlLegacy(r, i);
        html += "<strong>" + escapeHtml(r.title || "—") + "</strong>";
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

  function renderItem(it, idx, deleteContext) {
    var title = it.title || "—";
    var iso = it.created_at || "";
    var displayTime = fmtTime(iso);
    var snippet = it.summary_snippet != null && String(it.summary_snippet).trim() ? "" + it.summary_snippet : "—";
    var preview = it.result_preview != null && String(it.result_preview).trim() ? "" + it.result_preview : "—";
    var detailId = "uh-detail-" + String(it.id || idx).replace(/[^a-zA-Z0-9_-]/g, "_");
    var dc = deleteContext || {};
    var dm = dc.mode;
    var showDel = dm === "api" || dm === "local";
    var delRow = "";
    if (showDel && String(it.id || "").trim()) {
      delRow =
        '<div class="unified-history-item-actions">' +
        '<button type="button" class="btn-history-danger unified-history-delete-btn" ' +
        'data-delete-mode="' +
        escapeAttr(dm) +
        '" data-entry-id="' +
        escapeAttr(String(it.id)) +
        '">' +
        "删除" +
        "</button>" +
        '<span class="hint muted unified-history-delete-en" lang="en">Delete</span>' +
        "</div>";
    }

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
      delRow +
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

  /** Step17：收藏页「返回分析历史」深链 ?entry=<recordId>，与 uh-detail-* id 后缀规则一致 */
  function uhSanitizeDetailIdSuffix(raw) {
    return String(raw != null ? raw : "").replace(/[^a-zA-Z0-9_-]/g, "_");
  }

  function tryScrollToUnifiedHistoryEntryFromQuery() {
    try {
      var params = new URLSearchParams(window.location.search || "");
      var raw = params.get("entry");
      if (!raw || !String(raw).trim()) return;
      var suffix = uhSanitizeDetailIdSuffix(String(raw).trim());
      if (!suffix) return;
      var el = document.getElementById("uh-detail-" + suffix);
      if (!el || typeof el.scrollIntoView !== "function") return;
      el.scrollIntoView({ behavior: "smooth", block: "start" });
      var details = el.closest && el.closest("details.unified-history-details");
      if (details && !details.open) details.open = true;
    } catch (eUhEntry) {}
  }

  /**
   * 历史记录渲染主入口：
   * 接收标准化 records 后渲染列表卡片（摘要、要点、详情展开、删除动作）。
   */
  function renderList(container, items, emptyHint, countSourceLabel, deleteContext) {
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
      html += renderItem(items[i], i, deleteContext);
    }
    html += "</ul>";
    container.innerHTML = html;
    container.setAttribute("data-unified-history-state", "populated");
    hydrateUnifiedHistoryFavoriteButtons();
    tryScrollToUnifiedHistoryEntryFromQuery();
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
      "已登录：下列为与<strong>当前账户同步</strong>的最近分析摘要（云端优先；未登录访客仅见本机）。<span class=\"hint\" lang=\"en\">Account-synced history.</span>";
  }

  function setAnalysisLeadRemoteFallback() {
    var lead = document.getElementById("analysis-history-lead");
    if (!lead) return;
    lead.innerHTML =
      "已登录：云端历史暂不可用，下列为<strong>本机缓存</strong>中的最近分析摘要（恢复连接后将优先显示账户同步记录）。";
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

  /** 本地筛选：控制两个 `data-unified-history-section` 卡片的显隐。 */
  function applyHistoryFilter() {
    var v = _historyFilter || "all";
    var propSec = document.querySelector(
      '.analysis-history-block[data-unified-history-section="property"]'
    );
    var conSec = document.querySelector(
      '.analysis-history-block[data-unified-history-section="contract"]'
    );
    if (propSec) propSec.classList.toggle("hidden", v === "contract");
    if (conSec) conSec.classList.toggle("hidden", v === "property");
    var btns = document.querySelectorAll(".analysis-history-filter-btn");
    var i;
    for (i = 0; i < btns.length; i++) {
      var b = btns[i];
      var f = b.getAttribute("data-filter");
      if (f) b.classList.toggle("analysis-history-filter-btn--active", f === v);
    }
  }

  function bindFilterOnce() {
    if (_filterBound) return;
    _filterBound = true;
    document.addEventListener("click", function (ev) {
      var btn = ev.target && ev.target.closest && ev.target.closest(".analysis-history-filter-btn");
      if (!btn) return;
      var f = btn.getAttribute("data-filter");
      if (!f || f === _historyFilter) return;
      ev.preventDefault();
      _historyFilter = f;
      applyHistoryFilter();
    });
  }

  /** 云端历史成功时的轻量双语提示（不含 token）；空则隐藏 */
  function setCloudLoadHint(text) {
    var el = document.getElementById("history-cloud-load-hint");
    if (!el) return;
    var t = text && String(text).trim();
    if (!t) {
      el.textContent = "";
      el.classList.add("hidden");
      return;
    }
    el.textContent = t;
    el.classList.remove("hidden");
  }

  /**
   * 页面级链路编排：
   * 1) 读取来源策略与历史数据；
   * 2) 渲染房源/合同两组历史列表；
   * 3) 绑定刷新、删除、清空与过滤行为。
   */
  function run() {
    bindUnifiedHistoryFavoritesOnce();
    if (
      window.RentalAIHistoryAccess &&
      typeof window.RentalAIHistoryAccess.applyBannerById === "function"
    ) {
      window.RentalAIHistoryAccess.applyBannerById("history-access-banner", {
        page: "unified_analysis",
      });
    }
    var leadEl = document.getElementById("analysis-history-lead");
    if (leadEl && _defaultAnalysisLeadHtml === null) {
      _defaultAnalysisLeadHtml = leadEl.innerHTML;
    }

    var toolbarEl = document.getElementById("analysis-history-toolbar");
    var refreshBtn = document.getElementById("analysis-history-refresh-btn");
    if (!_refreshClickBound && refreshBtn) {
      _refreshClickBound = true;
      refreshBtn.addEventListener("click", function () {
        try {
          if (
            window.RentalAIAnalysisHistoryPersist &&
            typeof window.RentalAIAnalysisHistoryPersist.markCloudHistoryNeedsRefresh === "function"
          ) {
            window.RentalAIAnalysisHistoryPersist.markCloudHistoryNeedsRefresh();
          }
        } catch (eR) {}
        run();
      });
    }

    var clearAllBtn = document.getElementById("analysis-history-clear-all-btn");
    if (!_clearAllClickBound && clearAllBtn) {
      _clearAllClickBound = true;
      clearAllBtn.addEventListener("click", function () {
        if (!window.confirm("Are you sure?")) return;
        var strat =
          window.RentalAIAnalysisHistorySource &&
          typeof window.RentalAIAnalysisHistorySource.resolveHistoryMode === "function"
            ? window.RentalAIAnalysisHistorySource.resolveHistoryMode()
            : null;
        var mode = strat && strat.mode;
        if (mode !== "remote_user") {
          if (typeof S.clearCurrentBucket === "function") {
            S.clearCurrentBucket();
          }
          setServerNotice("");
          setCloudLoadHint("");
          run();
          return;
        }
        var api = window.RentalAIServerHistoryApi;
        if (!api || typeof api.clearAllHistory !== "function") {
          setServerNotice("清空失败：接口不可用。");
          return;
        }
        clearAllBtn.disabled = true;
        api
          .clearAllHistory()
          .then(function (j) {
            clearAllBtn.disabled = false;
            if (j && j.success === true) {
              try {
                if (typeof S.clearCurrentBucket === "function") {
                  S.clearCurrentBucket();
                }
              } catch (eL) {}
              try {
                if (
                  window.RentalAIAnalysisHistoryPersist &&
                  typeof window.RentalAIAnalysisHistoryPersist.markCloudHistoryNeedsRefresh === "function"
                ) {
                  window.RentalAIAnalysisHistoryPersist.markCloudHistoryNeedsRefresh();
                }
              } catch (eM) {}
              setServerNotice("");
              run();
              return;
            }
            var msg = (j && j.message) || "unknown";
            if (j && j._httpStatus === 401) {
              msg = "请先登录（会话无效）。";
            }
            setServerNotice("清空失败：" + String(msg));
          })
          .catch(function () {
            clearAllBtn.disabled = false;
            setServerNotice("清空失败：网络错误");
          });
      });
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
      setCloudLoadHint("");
      var localDel = { mode: "local" };
      renderList(propEl, S.listByType("property"), emptyProp, "本地自动保存", localDel);
      renderList(contractEl, S.listByType("contract"), emptyContract, "本地自动保存", localDel);
      applyHistoryFilter();
    }

    var strat =
      window.RentalAIAnalysisHistorySource &&
      typeof window.RentalAIAnalysisHistorySource.resolveHistoryMode === "function"
        ? window.RentalAIAnalysisHistorySource.resolveHistoryMode()
        : null;
    var isRemote = strat && strat.mode === "remote_user";

    if (toolbarEl) {
      toolbarEl.classList.toggle("hidden", !isRemote);
    }

    if (isRemote && propEl && contractEl) {
      renderLoading(propEl);
      renderLoading(contractEl);
      setServerNotice("");
      setCloudLoadHint("");
      applyHistoryFilter();
    } else {
      resetAnalysisLead();
      setServerNotice("");
      setCloudLoadHint("");
    }

    if (
      window.RentalAIAnalysisHistorySource &&
      typeof window.RentalAIAnalysisHistorySource.loadAnalysisHistory === "function"
    ) {
      // 历史列表获取点：统一通过 source 层加载（云端优先，本机回退）。
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
              main.setAttribute("data-history-cloud-auth-status", bundle.cloudAuthStatus || "");
            }
          } catch (eMain) {}
          if (bundle.mode === "local_guest") {
            resetAnalysisLead();
            setServerNotice("");
            setCloudLoadHint("");
          } else if (bundle.mode === "remote_user") {
            if (bundle.usedFallback) {
              setAnalysisLeadRemoteFallback();
              setCloudLoadHint("");
              var cas = bundle.cloudAuthStatus;
              if (cas === "missing_token") {
                setServerNotice(
                  "Authentication required to load cloud history. 未检测到有效会话，已显示本机缓存。请登录后重试。"
                );
              } else if (cas === "auth_error") {
                setServerNotice(
                  "Authentication failed or session expired. 云端会话无效或已过期，已显示本机缓存。请重新登录。"
                );
              } else {
                setServerNotice(
                  "云端历史暂时不可用，已显示本机缓存（" + (bundle.message || "error") + "）。"
                );
              }
            } else {
              setAnalysisLeadCloud();
              setServerNotice("");
              if (bundle.cacheBustUsed) {
                setCloudLoadHint(
                  "Latest cloud history loaded · 已拉取最新云端分析记录"
                );
              } else {
                setCloudLoadHint(
                  "Signed-in history loaded from account · 已从账户加载云端历史"
                );
              }
            }
          }
          var label =
            bundle.mode === "remote_user"
              ? bundle.usedFallback
                ? "本机回退（云端不可用）"
                : "服务端 JSON 历史"
              : "本地 guest 自动保存";
          var delCtx = {
            mode:
              bundle.mode === "remote_user" && !bundle.usedFallback ? "api" : "local",
          };
          renderList(propEl, bundle.propertyRecords, emptyProp, label, delCtx);
          renderList(contractEl, bundle.contractRecords, emptyContract, label, delCtx);
        })
        .catch(function () {
          setCloudLoadHint("");
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

  function bindDeleteDelegation() {
    if (_deleteDelegateBound) return;
    _deleteDelegateBound = true;
    document.addEventListener("click", function (ev) {
      var t = ev.target;
      if (!t || !t.closest) return;
      var btn = t.closest(".unified-history-delete-btn");
      if (!btn) return;
      var eid = btn.getAttribute("data-entry-id");
      var mode = btn.getAttribute("data-delete-mode");
      if (!eid || !mode) return;
      ev.preventDefault();
      if (mode === "local") {
        if (typeof S.removeEntryById !== "function") {
          setServerNotice("删除失败：本机存储不可用。");
          return;
        }
        if (S.removeEntryById(eid)) {
          setServerNotice("");
          run();
        } else {
          setServerNotice("删除失败：未找到该条本机记录。");
        }
        return;
      }
      if (mode === "api") {
        var api = window.RentalAIServerHistoryApi;
        if (!api || typeof api.deleteHistoryRecord !== "function") {
          setServerNotice("删除失败：云端接口不可用。");
          return;
        }
        btn.disabled = true;
        api
          .deleteHistoryRecord(eid)
          .then(function (j) {
            btn.disabled = false;
            if (j && j.success === true) {
              setServerNotice("");
              try {
                if (
                  window.RentalAIAnalysisHistoryPersist &&
                  typeof window.RentalAIAnalysisHistoryPersist.markCloudHistoryNeedsRefresh === "function"
                ) {
                  window.RentalAIAnalysisHistoryPersist.markCloudHistoryNeedsRefresh();
                }
              } catch (eM) {}
              run();
              return;
            }
            var msg = (j && j.message) || "unknown";
            if (j && j._httpStatus === 401) {
              msg = "请先登录（会话无效）。";
            }
            setServerNotice("删除失败：" + String(msg));
          })
          .catch(function () {
            btn.disabled = false;
            setServerNotice("删除失败：网络错误");
          });
      }
    });
  }

  /** 供收藏对比页等复用：与列表项「查看详情」同一套 HTML（含收藏按钮骨架，依赖全站 uh-fav 委托与 hydrate）。 */
  try {
    window.RentalAIUnifiedHistoryUi = {
      renderDetailBodyHtml: renderDetailBody,
      hydrateFavoriteButtons: hydrateUnifiedHistoryFavoriteButtons,
    };
  } catch (eUi) {}

  bindDeleteDelegation();
  bindFilterOnce();

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run);
  } else {
    run();
  }

  window.addEventListener("pageshow", function (ev) {
    if (ev.persisted) run();
  });
})();
