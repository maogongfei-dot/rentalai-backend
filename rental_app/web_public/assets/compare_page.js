(function () {
  function loadScriptSync(url) {
    try {
      var xhr = new XMLHttpRequest();
      xhr.open("GET", url, false);
      xhr.send(null);
      if (xhr.status === 200 && xhr.responseText) {
        (0, Function)(xhr.responseText)();
      }
    } catch (e) {}
  }

  if (typeof window.rentalaiMergeAuthHeaders === "undefined") {
    loadScriptSync("/assets/api_config.js");
  }
  if (typeof window.RentalAIServerFavoritesApi === "undefined") {
    loadScriptSync("/assets/server_favorites_api.js");
  }
  if (!window.RentalAIAnalysisHistoryStore) {
    loadScriptSync("/assets/analysis_history_store.js");
  }
  if (!window.RentalAIUnifiedHistoryUi) {
    loadScriptSync("/assets/analysis_history_page.js");
  }

  var raw = sessionStorage.getItem("ai_analyze_last");
  var data;
  try {
    data = raw ? JSON.parse(raw) : null;
  } catch (e3) {
    data = null;
  }

  var recos = (data && data.recommendations) || [];

  var container = document.getElementById("compare-list");
  if (!container) return;

  /** @type {Array<Object>} */
  var lastSelected = [];

  /** Step12：当前打开的详情对应的 favoriteKey（规范化后）；用于收藏变化时关闭错位详情 */
  var openDetailFavoriteKey = null;

  /** Step18：收藏页多选管理（仅存页面层，不写全局 store） */
  var compareManageMode = false;
  var compareSelectedKeys = [];
  /** 批量删除进行中：抑制 rentalai-favorites-updated 中间态重绘 */
  var compareBulkDeleting = false;
  /** Step22：管理模式「更多操作」占位菜单开关（仅页面层） */
  var compareBulkMoreMenuOpen = false;

  function escapeAttr(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/</g, "&lt;");
  }

  function escapeHtml(s) {
    var d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  function recoUrl(r) {
    return (r.source_url || r.listing_url || r.url || "").trim();
  }

  function recoPid(r) {
    return String(r.listing_id != null ? r.listing_id : r.rank != null ? r.rank : "");
  }

  /** Step17：基于 client meta（source / sourceType / historyId）生成来源文案与站内返回链接 */
  function getFavoriteSourceDisplayAndLink(r) {
    var meta = (r && r._favoriteMeta) || {};
    var src = meta.source != null ? String(meta.source).trim() : "";
    var st = meta.sourceType != null ? String(meta.sourceType).trim() : "";
    var hid =
      (r && r._historyId) ||
      meta.historyId ||
      meta.recordId ||
      meta.analysisId ||
      "";
    hid = hid != null ? String(hid).trim() : "";

    var label = "收藏项（来源未标注）";
    var href = "/analysis-history";
    var linkLabel = "前往分析历史";

    if (src === "ai_result") {
      label = "需求解析结果页";
      href = "/ai-result";
      linkLabel = "返回结果页";
    } else if (src === "unified_history" || st === "unified_property") {
      label = "统一分析历史";
      href = hid ? "/analysis-history?entry=" + encodeURIComponent(hid) : "/analysis-history";
      linkLabel = hid ? "在分析历史中定位" : "前往分析历史";
    } else if (hid) {
      label = "分析历史（已关联记录）";
      href = "/analysis-history?entry=" + encodeURIComponent(hid);
      linkLabel = "在分析历史中定位";
    } else if (src === "favorite" || src === "unified_history") {
      label = "收藏保存";
      href = "/analysis-history";
      linkLabel = "前往分析历史";
    }

    return { label: label, href: href, linkLabel: linkLabel };
  }

  function compareDetailSourceStripHtml(r) {
    var info = getFavoriteSourceDisplayAndLink(r);
    return (
      '<div class="compare-detail-source-strip hint muted small-print" style="margin-bottom:0.75rem;padding-bottom:0.5rem;border-bottom:1px solid rgba(0,0,0,.06)">' +
      "来源：" +
      escapeHtml(info.label) +
      (info.href
        ? ' · <a href="' +
          escapeAttr(info.href) +
          '">' +
          escapeHtml(info.linkLabel) +
          "</a>"
        : "") +
      "</div>"
    );
  }

  function parseSavedAtMs(iso) {
    if (!iso || typeof iso !== "string") return NaN;
    var t = Date.parse(iso);
    return isNaN(t) ? NaN : t;
  }

  /** 最近收藏在前：有 savedAt 的优先且倒序；无时间的置后；再用 url+pid 稳定排序 */
  function compareFavoriteRowsForComparePage(a, b) {
    var ma = a && a._favoriteMeta && a._favoriteMeta.savedAt;
    var mb = b && b._favoriteMeta && b._favoriteMeta.savedAt;
    var ta = parseSavedAtMs(ma);
    var tb = parseSavedAtMs(mb);
    var ha = !isNaN(ta);
    var hb = !isNaN(tb);
    if (ha && hb && tb !== ta) return tb - ta;
    if (ha && !hb) return -1;
    if (!ha && hb) return 1;
    var ka = recoUrl(a) + "\0" + recoPid(a);
    var kb = recoUrl(b) + "\0" + recoPid(b);
    if (ka < kb) return -1;
    if (ka > kb) return 1;
    return 0;
  }

  function sortCompareSelection(arr) {
    if (!arr || !arr.length) return arr || [];
    var copy = arr.slice();
    copy.sort(compareFavoriteRowsForComparePage);
    return copy;
  }

  function recoFavoriteKeyNormalized(r) {
    var api = window.RentalAIServerFavoritesApi;
    if (!api || typeof api.buildFavoriteKey !== "function") return "";
    var k = api.buildFavoriteKey({
      listing_url: (r.source_url || r.listing_url || r.url || "").trim(),
      source_url: r.source_url,
      url: r.url,
      property_id: String(r.listing_id != null ? r.listing_id : r.rank),
      listing_id: r.listing_id,
      rank: r.rank,
    });
    if (api.normalizeFavoriteKey) k = api.normalizeFavoriteKey(k);
    return k ? String(k).trim() : "";
  }

  function pruneCompareSelectedKeys(rows) {
    var keep = {};
    var i;
    for (i = 0; i < (rows || []).length; i++) {
      var kk = recoFavoriteKeyNormalized(rows[i]);
      if (kk) keep[kk] = true;
    }
    compareSelectedKeys = compareSelectedKeys.filter(function (k) {
      return keep[k];
    });
  }

  /** Step19：当前列表可见项的 favoriteKey（与渲染顺序一致，去重） */
  function compareVisibleFavoriteKeys(rows) {
    rows = rows || [];
    var out = [];
    var seen = {};
    var j;
    for (j = 0; j < rows.length; j++) {
      var k = recoFavoriteKeyNormalized(rows[j]);
      if (!k || seen[k]) continue;
      seen[k] = true;
      out.push(k);
    }
    return out;
  }

  function compareIsAllVisibleSelected(rows) {
    var vk = compareVisibleFavoriteKeys(rows);
    if (!vk.length) return false;
    var i;
    for (i = 0; i < vk.length; i++) {
      if (compareSelectedKeys.indexOf(vk[i]) < 0) return false;
    }
    return true;
  }

  /** Step20：管理模式操作栏派生状态（基于当前展示列表 lastSelected + compareSelectedKeys） */
  function getCompareBulkToolbarDerived() {
    var rows = lastSelected || [];
    var visibleKeys = compareVisibleFavoriteKeys(rows);
    var visibleCount = visibleKeys.length;
    var hasItems = visibleCount > 0;
    var selectedCount = compareSelectedKeys.length;
    var hasSelection = selectedCount > 0;
    var isAllSelected = hasItems && compareIsAllVisibleSelected(rows);
    return {
      visibleCount: visibleCount,
      hasItems: hasItems,
      selectedCount: selectedCount,
      hasSelection: hasSelection,
      isAllSelected: isAllSelected,
    };
  }

  function getServerFavoriteIdForReco(r) {
    var fr = r && r._favoriteRow;
    if (fr && fr.id) return String(fr.id).trim();
    var api = window.RentalAIServerFavoritesApi;
    if (!api || typeof api.buildFavoriteKey !== "function") return "";
    var fk = recoFavoriteKeyNormalized(r);
    if (!fk) return "";
    var rows = typeof api.getCachedFavoritesRows === "function" ? api.getCachedFavoritesRows() : null;
    if (!rows || !rows.length) return "";
    var j;
    for (j = 0; j < rows.length; j++) {
      var row = rows[j];
      if (!row || !row.id) continue;
      var rk = api.buildFavoriteKey({ listing_url: row.listing_url, property_id: row.property_id });
      if (api.normalizeFavoriteKey) rk = api.normalizeFavoriteKey(rk);
      if (rk === fk || (api.favoriteKeysEqual && api.favoriteKeysEqual(fk, rk)))
        return String(row.id).trim();
    }
    return "";
  }

  function findRecoByFavoriteKey(fkNorm) {
    var want = (fkNorm || "").trim();
    if (!want) return null;
    var list = lastSelected || [];
    var i;
    for (i = 0; i < list.length; i++) {
      if (recoFavoriteKeyNormalized(list[i]) === want) return list[i];
    }
    return null;
  }

  /** Step24：更多操作菜单焦点收口 */
  function compareBulkMoreFocusFirstMenuItemDeferred() {
    setTimeout(function () {
      var menu = document.getElementById("compare-bulk-more-menu");
      if (!menu || menu.hidden) return;
      var first = menu.querySelector("button[role='menuitem'], button");
      if (first) first.focus();
    }, 0);
  }

  function compareBulkMoreFocusMoreButtonDeferred() {
    setTimeout(function () {
      var b = document.getElementById("compare-bulk-more-btn");
      if (b && compareManageMode && !b.hidden && !b.disabled) b.focus();
    }, 0);
  }

  function updateCompareBulkToolbar() {
    var delBtn = document.getElementById("compare-delete-selected-btn");
    var toggleBtn = document.getElementById("compare-manage-toggle-btn");
    var selToggle = document.getElementById("compare-select-toggle-btn");
    var statusEl = document.getElementById("compare-bulk-selection-status");
    var moreAnchor = document.getElementById("compare-bulk-more-anchor");
    var moreBtn = document.getElementById("compare-bulk-more-btn");
    var moreMenu = document.getElementById("compare-bulk-more-menu");
    if (!delBtn || !toggleBtn) return;
    var snapMenuWasOpen = compareBulkMoreMenuOpen;
    var derived = getCompareBulkToolbarDerived();
    if (
      !compareManageMode ||
      !derived.hasSelection ||
      compareBulkDeleting ||
      !derived.hasItems
    ) {
      compareBulkMoreMenuOpen = false;
    }
    if (compareManageMode) {
      delBtn.hidden = false;
      toggleBtn.textContent = "完成";
      delBtn.disabled = !derived.hasSelection || compareBulkDeleting;
      if (statusEl) {
        statusEl.hidden = false;
        statusEl.textContent = "已选择 " + derived.selectedCount + " 项";
      }
      if (selToggle) {
        selToggle.hidden = false;
        if (!derived.hasItems) {
          selToggle.hidden = true;
        } else {
          selToggle.disabled = compareBulkDeleting;
          selToggle.textContent = derived.isAllSelected ? "取消全选" : "全选";
        }
      }
      if (moreAnchor) moreAnchor.hidden = false;
      if (moreBtn) moreBtn.disabled = !derived.hasSelection || compareBulkDeleting;
      if (delBtn && compareManageMode)
        delBtn.setAttribute("aria-label", "删除当前选中的收藏");
      if (selToggle && compareManageMode && !selToggle.hidden) {
        selToggle.setAttribute(
          "aria-label",
          derived.isAllSelected ? "取消全选当前列表" : "全选当前列表中的收藏"
        );
      }
      if (moreMenu) {
        moreMenu.hidden = !(
          compareBulkMoreMenuOpen &&
          derived.hasSelection &&
          !compareBulkDeleting
        );
        moreMenu.setAttribute(
          "aria-hidden",
          moreMenu.hidden ? "true" : "false"
        );
      }
      if (moreBtn) moreBtn.setAttribute("aria-expanded", compareBulkMoreMenuOpen ? "true" : "false");
      if (compareBulkDeleting) {
        toggleBtn.disabled = true;
        delBtn.disabled = true;
        if (moreBtn) moreBtn.disabled = true;
      } else {
        toggleBtn.disabled = false;
      }
    } else {
      delBtn.hidden = true;
      toggleBtn.textContent = "管理";
      toggleBtn.disabled = false;
      delBtn.disabled = true;
      compareBulkMoreMenuOpen = false;
      if (statusEl) statusEl.hidden = true;
      if (selToggle) selToggle.hidden = true;
      if (moreAnchor) moreAnchor.hidden = true;
      if (moreMenu) {
        moreMenu.hidden = true;
        moreMenu.setAttribute("aria-hidden", "true");
      }
      if (moreBtn) moreBtn.setAttribute("aria-expanded", "false");
    }
    var manageHintEl = document.getElementById("compare-bulk-manage-hint");
    if (manageHintEl) manageHintEl.hidden = !compareManageMode;
    if (toggleBtn)
      toggleBtn.setAttribute("aria-pressed", compareManageMode ? "true" : "false");
    if (snapMenuWasOpen && !compareBulkMoreMenuOpen) {
      compareBulkMoreFocusMoreButtonDeferred();
    }
  }

  function setOpenDetailKeyFromReco(r) {
    var api = window.RentalAIServerFavoritesApi;
    if (!api || typeof api.buildFavoriteKey !== "function") {
      openDetailFavoriteKey = null;
      return;
    }
    openDetailFavoriteKey = api.buildFavoriteKey({
      listing_url: (r.source_url || r.listing_url || r.url || "").trim(),
      source_url: r.source_url,
      url: r.url,
      property_id: String(r.listing_id != null ? r.listing_id : r.rank),
      listing_id: r.listing_id,
      rank: r.rank,
    });
    if (api.normalizeFavoriteKey) {
      openDetailFavoriteKey = api.normalizeFavoriteKey(openDetailFavoriteKey);
    }
  }

  function legacyTopMatchesR(r, row) {
    var url = recoUrl(r);
    var ru = (row && row.source_url ? String(row.source_url) : "").trim();
    if (ru && url && ru === url) return true;
    if (r.listing_id != null && row.listing_id != null && String(r.listing_id) === String(row.listing_id))
      return true;
    if (r.rank != null && row.rank != null && String(r.rank) === String(row.rank)) return true;
    var t1 = (r.title || "").trim();
    var t2 = (row && row.title ? String(row.title) : "").trim();
    if (t1 && t2 && t1 === t2) return true;
    return false;
  }

  function housingDealMatchesR(r, deal) {
    var url = recoUrl(r);
    var du = (deal && (deal.listing_url || deal.url) ? String(deal.listing_url || deal.url) : "").trim();
    if (du && url && du === url) return true;
    var t1 = (r.title || "").trim();
    var t2 = (deal && (deal.title || deal.address) ? String(deal.title || deal.address) : "").trim();
    if (t1 && t2 && t1 === t2) return true;
    return false;
  }

  function findHistoryEntryById(hid) {
    if (hid == null || String(hid).trim() === "") return null;
    var S = window.RentalAIAnalysisHistoryStore;
    if (!S || typeof S.listForUser !== "function") return null;
    var list = S.listForUser() || [];
    var i;
    for (i = 0; i < list.length; i++) {
      if (list[i] && String(list[i].id) === String(hid)) return list[i];
    }
    return null;
  }

  function mergeFavoriteServerRowWithMeta(f) {
    var api = window.RentalAIServerFavoritesApi;
    var meta =
      api && typeof api.getFavoriteDetailMetaForFavoriteRow === "function"
        ? api.getFavoriteDetailMetaForFavoriteRow(f)
        : null;
    var snap = meta && (meta.detailSnapshot || meta.detail_snapshot);
    var recoMin = snap && snap.variant === "reco_min";
    return {
      title: ((f.title || "").trim() || (recoMin && snap.title) || (meta && meta.titleHint) || "房源").trim(),
      rent: recoMin && snap.rent != null ? snap.rent : f.price,
      bedrooms: recoMin && snap.bedrooms != null ? snap.bedrooms : undefined,
      postcode: recoMin && snap.postcode ? snap.postcode : undefined,
      source_url: (f.listing_url || "").trim() || (recoMin && snap.listing_url) || "",
      listing_url: f.listing_url,
      explain: recoMin ? snap.explain : undefined,
      decision: recoMin ? snap.decision : undefined,
      decision_reason: recoMin ? snap.decision_reason : undefined,
      risks: recoMin ? snap.risks : undefined,
      final_score: recoMin ? snap.final_score : undefined,
      listing_id: recoMin && snap.listing_id != null ? snap.listing_id : undefined,
      rank: recoMin && snap.rank != null ? snap.rank : undefined,
      _historyId: meta && (meta.historyId || meta.recordId),
      _favoriteMeta: meta,
      _favoriteRow: f,
    };
  }

  function enrichRecoWithMetaKey(r) {
    var api = window.RentalAIServerFavoritesApi;
    if (
      !api ||
      typeof api.buildFavoriteKey !== "function" ||
      typeof api.getFavoriteDetailMetaByKey !== "function"
    )
      return r;
    var kk = api.buildFavoriteKey({
      listing_url: (r.source_url || r.listing_url || r.url || "").trim(),
      source_url: r.source_url,
      url: r.url,
      property_id: String(r.listing_id != null ? r.listing_id : r.rank),
      listing_id: r.listing_id,
      rank: r.rank,
    });
    var meta = api.getFavoriteDetailMetaByKey(kk);
    if (!meta) return r;
    var o = {};
    var k;
    for (k in r) {
      if (Object.prototype.hasOwnProperty.call(r, k)) o[k] = r[k];
    }
    o._favoriteMeta = meta;
    o._historyId = meta.historyId || meta.recordId;
    return o;
  }

  function enrichRecoWithFavoriteMeta(r, rows) {
    var api = window.RentalAIServerFavoritesApi;
    if (!api || typeof api.getFavoriteDetailMetaForFavoriteRow !== "function") return enrichRecoWithMetaKey(r);
    var i;
    for (i = 0; i < rows.length; i++) {
      if (rowMatchesFavorite(r, rows[i])) {
        var meta = api.getFavoriteDetailMetaForFavoriteRow(rows[i]);
        if (!meta) return enrichRecoWithMetaKey(r);
        var o = {};
        var k;
        for (k in r) {
          if (Object.prototype.hasOwnProperty.call(r, k)) o[k] = r[k];
        }
        o._favoriteMeta = meta;
        o._historyId = meta.historyId || meta.recordId;
        return o;
      }
    }
    return enrichRecoWithMetaKey(r);
  }

  function historyEntryFromFavoriteMeta(r) {
    var meta = r._favoriteMeta;
    if (!meta) return null;
    var ds = meta.detailSnapshot || meta.detail_snapshot;
    if (!ds) return null;
    if (ds.variant === "legacy" || ds.variant === "housing") {
      return {
        id: meta.historyId || meta.recordId || "favorite-meta",
        type: "property",
        title: meta.titleHint || r.title || "房源",
        detail_snapshot: ds,
      };
    }
    if (ds.variant === "reco_min") {
      return minimalHistoryEntryFromReco({
        title: ds.title,
        rent: ds.rent,
        bedrooms: ds.bedrooms,
        explain: ds.explain,
        decision: ds.decision,
        decision_reason: ds.decision_reason,
        risks: ds.risks,
        final_score: ds.final_score,
        listing_id: ds.listing_id,
        rank: ds.rank,
        source_url: ds.listing_url,
      });
    }
    return null;
  }

  function findUnifiedHistoryEntry(r) {
    var S = window.RentalAIAnalysisHistoryStore;
    if (!S || typeof S.listByType !== "function") return null;
    var items = S.listByType("property") || [];
    var i;
    for (i = 0; i < items.length; i++) {
      var it = items[i];
      var snap = it && it.detail_snapshot;
      if (!snap) continue;
      if (snap.variant === "legacy") {
        var tops = snap.recommendations_top || [];
        var j;
        for (j = 0; j < tops.length; j++) {
          if (legacyTopMatchesR(r, tops[j])) return it;
        }
      } else if (snap.variant === "housing") {
        var deals = snap.top_deals || [];
        var k;
        for (k = 0; k < deals.length; k++) {
          if (housingDealMatchesR(r, deals[k])) return it;
        }
      } else if (snap.variant === "remote_property") {
        var prev = snap.user_text_preview ? String(snap.user_text_preview) : "";
        var rt = (r.title || "").trim();
        if (rt && prev && prev.indexOf(rt.slice(0, Math.min(24, rt.length))) >= 0) return it;
      }
    }
    return null;
  }

  function minimalHistoryEntryFromReco(r) {
    var url = recoUrl(r);
    return {
      id: "compare-detail-fallback",
      type: "property",
      title: r.title || "房源",
      summary_snippet: r.decision || r.explain || "—",
      result_preview: r.explain || r.decision || "—",
      detail_snapshot: {
        variant: "legacy",
        summary: { total_candidates: null, top_count: null },
        recommendations_top: [
          {
            title: r.title || "—",
            final_score: r.final_score,
            decision: r.decision,
            decision_reason: r.decision_reason || r.explain || "",
            listing_id: r.listing_id,
            rank: r.rank,
            source_url: url,
          },
        ],
      },
    };
  }

  function ensureCompareDetailModal() {
    var id = "compare-detail-overlay";
    var ex = document.getElementById(id);
    if (ex) return ex;
    var ov = document.createElement("div");
    ov.id = id;
    ov.setAttribute("hidden", "");
    ov.style.cssText =
      "position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:9998;display:none;align-items:center;justify-content:center;padding:16px;";
    ov.innerHTML =
      '<div class="card compare-detail-dialog" style="max-width:720px;max-height:90vh;overflow:auto;width:100%;position:relative">' +
      '<p class="unified-history-item-actions" style="margin-top:0">' +
      '<button type="button" class="btn-history-primary compare-detail-close">关闭</button></p>' +
      '<div id="compare-detail-inner" class="unified-history-details-body"></div></div>';
    document.body.appendChild(ov);
    ov.addEventListener("click", function (ev) {
      if (ev.target === ov) closeCompareDetail();
    });
    var cls = ov.querySelector(".compare-detail-close");
    if (cls) cls.addEventListener("click", closeCompareDetail);
    return ov;
  }

  function closeCompareDetail() {
    openDetailFavoriteKey = null;
    var ov = document.getElementById("compare-detail-overlay");
    if (ov) {
      ov.style.display = "none";
      ov.setAttribute("hidden", "");
    }
  }

  function syncCompareDetailAfterFavoritesChange(rows) {
    if (!openDetailFavoriteKey) return;
    rows = rows || [];
    var api = window.RentalAIServerFavoritesApi;
    if (!api || typeof api.buildFavoriteKey !== "function") {
      closeCompareDetail();
      return;
    }
    var target = openDetailFavoriteKey;
    var i;
    for (i = 0; i < rows.length; i++) {
      var fk = api.buildFavoriteKey({
        listing_url: rows[i].listing_url,
        property_id: rows[i].property_id,
      });
      if (api.normalizeFavoriteKey) fk = api.normalizeFavoriteKey(fk);
      if (fk === target) return;
      if (api.favoriteKeysEqual && api.favoriteKeysEqual(openDetailFavoriteKey, fk)) return;
    }
    closeCompareDetail();
  }

  function openCompareDetail(r) {
    if (compareManageMode) return;
    setOpenDetailKeyFromReco(r);
    var ui = window.RentalAIUnifiedHistoryUi;
    var inner = document.getElementById("compare-detail-inner");
    if (!inner) ensureCompareDetailModal();
    inner = document.getElementById("compare-detail-inner");
    if (!inner) return;
    var hid = r._historyId;
    if ((hid == null || hid === "") && r._favoriteMeta) {
      hid = r._favoriteMeta.historyId || r._favoriteMeta.recordId;
    }
    var entry = null;
    if (hid != null && String(hid).trim() !== "") entry = findHistoryEntryById(hid);
    if (!entry) entry = findUnifiedHistoryEntry(r);
    if (!entry) entry = historyEntryFromFavoriteMeta(r);
    if (!entry) entry = minimalHistoryEntryFromReco(r);
    if (ui && typeof ui.renderDetailBodyHtml === "function") {
      inner.innerHTML = compareDetailSourceStripHtml(r) + ui.renderDetailBodyHtml(entry);
      if (typeof ui.hydrateFavoriteButtons === "function") ui.hydrateFavoriteButtons();
    } else {
      inner.innerHTML =
        compareDetailSourceStripHtml(r) +
        '<p class="hint muted">详情模块未加载。</p>' +
        "<p><strong>" +
        escapeHtml(r.title || "房源") +
        "</strong></p>" +
        "<p class=\"hint\">租金: £" +
        escapeHtml(r.rent != null ? String(r.rent) : "—") +
        "</p>" +
        "<p class=\"hint\">结论: " +
        escapeHtml(r.decision != null ? String(r.decision) : "—") +
        "</p>";
    }
    var ov = ensureCompareDetailModal();
    ov.style.display = "flex";
    ov.removeAttribute("hidden");
  }

  function findRecoFromButton(btn) {
    var wantPid = (btn.getAttribute("data-pid") || "").trim();
    var wantUrl = (btn.getAttribute("data-listing-url") || "").trim();
    var list = lastSelected || [];
    var i;
    for (i = 0; i < list.length; i++) {
      var r = list[i];
      if (wantUrl && recoUrl(r) === wantUrl) return r;
    }
    for (i = 0; i < list.length; i++) {
      var r2 = list[i];
      if (wantPid && recoPid(r2) === wantPid) return r2;
    }
    return list.length ? list[0] : null;
  }

  var _detailClickBound = false;
  function bindCompareDetailOnce() {
    if (_detailClickBound) return;
    _detailClickBound = true;
    container.addEventListener("click", function (ev) {
      if (compareManageMode) return;
      var btn = ev.target && ev.target.closest && ev.target.closest(".compare-detail-btn");
      if (!btn) return;
      ev.preventDefault();
      var r = findRecoFromButton(btn);
      if (!r) return;
      openCompareDetail(r);
    });
  }
  bindCompareDetailOnce();

  var _compareManageCardBound = false;
  function bindCompareManageCardToggleOnce() {
    if (_compareManageCardBound) return;
    _compareManageCardBound = true;
    container.addEventListener("click", function (ev) {
      if (!compareManageMode) return;
      var t = ev.target;
      if (t && t.closest && (t.closest("a") || t.closest("button"))) return;
      if (t && t.closest && (t.closest("label") || t.closest(".compare-select-cb"))) return;
      var card = t && t.closest && t.closest(".compare-card");
      if (!card) return;
      var fk = (card.getAttribute("data-favorite-key") || "").trim();
      if (!fk) return;
      ev.preventDefault();
      var ix = compareSelectedKeys.indexOf(fk);
      if (ix >= 0) compareSelectedKeys.splice(ix, 1);
      else compareSelectedKeys.push(fk);
      renderCards(lastSelected, null);
    });
  }
  bindCompareManageCardToggleOnce();

  var _compareCardKbBound = false;
  function bindCompareManageCardKeyboardOnce() {
    if (_compareCardKbBound) return;
    _compareCardKbBound = true;
    container.addEventListener("keydown", function (ev) {
      if (!compareManageMode) return;
      var key = ev.key || "";
      var code = ev.code || "";
      var isActivate =
        key === "Enter" ||
        key === " " ||
        code === "Enter" ||
        code === "Space" ||
        ev.keyCode === 13 ||
        ev.keyCode === 32;
      if (!isActivate) return;
      var el = ev.target;
      if (el && el.closest && el.closest(".compare-select-cb")) return;
      var card = el && el.closest && el.closest(".compare-card");
      if (!card) return;
      var fk = (card.getAttribute("data-favorite-key") || "").trim();
      if (!fk) return;
      ev.preventDefault();
      var ix = compareSelectedKeys.indexOf(fk);
      if (ix >= 0) compareSelectedKeys.splice(ix, 1);
      else compareSelectedKeys.push(fk);
      renderCards(lastSelected, null);
    });
  }
  bindCompareManageCardKeyboardOnce();

  var _compareSelectBound = false;
  function bindCompareSelectCheckboxOnce() {
    if (_compareSelectBound) return;
    _compareSelectBound = true;
    container.addEventListener("change", function (ev) {
      var t = ev.target;
      if (!t || !t.classList || !t.classList.contains("compare-select-cb")) return;
      var fk = (t.getAttribute("data-favorite-key") || "").trim();
      if (!fk) return;
      var ix = compareSelectedKeys.indexOf(fk);
      if (t.checked) {
        if (ix < 0) compareSelectedKeys.push(fk);
      } else if (ix >= 0) {
        compareSelectedKeys.splice(ix, 1);
      }
      updateCompareBulkToolbar();
    });
  }
  bindCompareSelectCheckboxOnce();

  function readLocalFavIds() {
    var favKey =
      window.RentalAILocalAuth && window.RentalAILocalAuth.favStorageKey
        ? window.RentalAILocalAuth.favStorageKey()
        : "fav_list";
    try {
      var favsLocal = JSON.parse(localStorage.getItem(favKey) || "[]");
      return Array.isArray(favsLocal) ? favsLocal : [];
    } catch (e1) {
      return [];
    }
  }

  function isGuestViewer() {
    try {
      var u = window.RentalAILocalAuth && window.RentalAILocalAuth.getUser && window.RentalAILocalAuth.getUser();
      return !u;
    } catch (e2) {
      return true;
    }
  }

  /** Step16：标题区作用域说明（guest / 已登录），随会话切换更新 */
  function syncComparePageHeaderScope() {
    var hdr = document.querySelector(".page-header");
    if (!hdr) return;
    var lead = document.getElementById("compare-page-scope-lead");
    if (!lead) {
      lead = document.createElement("p");
      lead.id = "compare-page-scope-lead";
      lead.className = "hint muted small-print";
      lead.setAttribute("aria-live", "polite");
      var h1 = hdr.querySelector("h1");
      var countEl = document.getElementById("compare-page-favorite-count");
      if (countEl && countEl.parentNode === hdr) {
        hdr.insertBefore(lead, countEl);
      } else if (h1) {
        hdr.insertBefore(lead, h1.nextSibling);
      } else {
        hdr.appendChild(lead);
      }
    }
    if (isGuestViewer()) {
      lead.textContent =
        "当前作用域：访客会话 · 以下为当前浏览器游客会话下的收藏（与登录账号收藏互不合并）。登录后将切换到账号收藏桶。";
    } else {
      lead.textContent =
        "当前作用域：已登录账号 · 以下为当前登录账户会话下的收藏列表（与访客会话互不合并）。";
    }
  }

  /** Step16：空态文案与 CTA 随作用域切换 */
  function emptyStateHtml() {
    if (isGuestViewer()) {
      return (
        '<p class="compare-empty-primary">暂无访客收藏。</p>' +
        '<p class="hint muted compare-empty-hint">请先完成<strong>房源分析</strong>，在需求解析结果页对推荐房源点击「⭐ 收藏」，即可出现在此处。数据仅保存在当前浏览器游客会话。</p>' +
        '<p class="hint compare-empty-cta">' +
        '<a href="/#ai-rental-heading">去房源分析</a> · ' +
        '<a href="/ai-result">需求解析结果</a> · ' +
        '<a href="/analysis-history">分析历史</a>' +
        "</p>"
      );
    }
    return (
      '<p class="compare-empty-primary">当前账号暂无收藏房源。</p>' +
      '<p class="hint muted compare-empty-hint">可在<strong>分析历史</strong>或<strong>需求解析结果页</strong>中将推荐房源加入收藏；以下为当前账号作用域。</p>' +
      '<p class="hint compare-empty-cta">' +
      '<a href="/analysis-history">分析历史</a> · ' +
      '<a href="/ai-result">需求解析结果</a> · ' +
      '<a href="/">首页</a>' +
      "</p>"
    );
  }

  function rowMatchesFavorite(r, f) {
    var api = window.RentalAIServerFavoritesApi;
    if (api && typeof api.favoriteRowMatchesReco === "function") {
      return api.favoriteRowMatchesReco(f, r);
    }
    var pid = String(r.listing_id != null ? r.listing_id : r.rank);
    var fp = f.property_id != null ? String(f.property_id).trim() : "";
    var url = (r.source_url || r.listing_url || r.url || "").trim();
    var fu = (f.listing_url || "").trim();
    if (fp && fp === pid) return true;
    if (fu && url && fu === url) return true;
    return false;
  }

  /** 收藏列表读取逻辑：与全站 RentalAIServerFavoritesApi 快照一致（跨页与结果页同步）。 */
  function selectedFromServerRows(rows) {
    rows = rows || [];
    if (!recos.length) {
      var built = [];
      var j;
      for (j = 0; j < rows.length; j++) {
        built.push(mergeFavoriteServerRowWithMeta(rows[j]));
      }
      return sortCompareSelection(built);
    }
    return sortCompareSelection(
      recos
        .filter(function (r) {
          return rows.some(function (f) {
            return rowMatchesFavorite(r, f);
          });
        })
        .map(function (r) {
          return enrichRecoWithFavoriteMeta(r, rows);
        })
    );
  }

  function selectedFromLocalIds() {
    var favsLocal = readLocalFavIds();
    var api = window.RentalAIServerFavoritesApi;
    if (!recos.length && api && typeof api.getCachedFavoritesRows === "function") {
      var cached = api.getCachedFavoritesRows();
      if (cached && cached.length) {
        var outCached = [];
        var c;
        for (c = 0; c < cached.length; c++) {
          outCached.push(mergeFavoriteServerRowWithMeta(cached[c]));
        }
        return sortCompareSelection(outCached);
      }
    }
    return sortCompareSelection(
      recos
        .filter(function (r) {
          var id = String(r.listing_id != null ? r.listing_id : r.rank);
          if (favsLocal.includes(id)) return true;
          if (api && typeof api.buildFavoriteKey === "function") {
            var kk = api.buildFavoriteKey({
              listing_url: (r.source_url || r.listing_url || r.url || "").trim(),
              source_url: r.source_url,
              url: r.url,
              property_id: id,
              listing_id: r.listing_id,
              rank: r.rank,
            });
            if (kk && favsLocal.includes(kk)) return true;
          }
          return false;
        })
        .map(function (r) {
          return enrichRecoWithMetaKey(r);
        })
    );
  }

  /** Step15：收藏页标题区数量 — 仅使用 RentalAIServerFavoritesApi.getFavoriteCountForCurrentScope（与列表同源）。 */
  function syncComparePageFavoriteCount() {
    var api = window.RentalAIServerFavoritesApi;
    var n = 0;
    if (api && typeof api.getFavoriteCountForCurrentScope === "function") {
      n = api.getFavoriteCountForCurrentScope();
    }
    var hdr = document.querySelector(".page-header");
    if (!hdr) return;
    var sub = document.getElementById("compare-page-favorite-count");
    if (!sub) {
      sub = document.createElement("p");
      sub.id = "compare-page-favorite-count";
      sub.className = "hint muted small-print";
      sub.setAttribute("aria-live", "polite");
      var h1 = hdr.querySelector("h1");
      var leadEl = document.getElementById("compare-page-scope-lead");
      if (leadEl && leadEl.parentNode === hdr) {
        hdr.insertBefore(sub, leadEl.nextSibling);
      } else if (h1) {
        hdr.insertBefore(sub, h1.nextSibling);
      } else {
        hdr.appendChild(sub);
      }
    }
    sub.textContent = "共 " + n + " 条收藏（当前作用域）";
  }

  function renderCards(selected, bannerText) {
    syncComparePageHeaderScope();
    lastSelected = selected || [];
    pruneCompareSelectedKeys(lastSelected);
    container.textContent = "";
    if (bannerText) {
      var pe = document.createElement("p");
      pe.className = "hint muted";
      pe.textContent = bannerText;
      container.appendChild(pe);
    }
    if (!selected.length) {
      var empWrap = document.createElement("div");
      empWrap.innerHTML = emptyStateHtml();
      while (empWrap.firstChild) {
        container.appendChild(empWrap.firstChild);
      }
      syncComparePageFavoriteCount();
      updateCompareBulkToolbar();
      return;
    }
    selected.forEach(function (r) {
      var div = document.createElement("div");
      div.className = "compare-card";
      var url = recoUrl(r);
      var pid = recoPid(r);
      var srcInfo = getFavoriteSourceDisplayAndLink(r);
      var fkNorm = recoFavoriteKeyNormalized(r);
      var pickLbl =
        "选择：「" + String((r.title || "房源").trim()).slice(0, 80) + "」";
      if (fkNorm) div.setAttribute("data-favorite-key", fkNorm);
      if (compareManageMode && fkNorm) {
        div.style.cursor = "pointer";
        div.setAttribute("tabindex", "0");
        div.setAttribute("role", "group");
        div.setAttribute("aria-label", pickLbl);
      }
      var selectRowHtml =
        compareManageMode && fkNorm
          ? '<p class="hint small-print compare-card-select-row"><label><input type="checkbox" class="compare-select-cb" data-favorite-key="' +
            escapeAttr(fkNorm) +
            '"' +
            (compareSelectedKeys.indexOf(fkNorm) >= 0 ? " checked" : "") +
            ' aria-label="' +
            escapeAttr(pickLbl) +
            '"/> 选择</label></p>'
          : "";

      var sourceLinkHtml =
        !compareManageMode && srcInfo.href
          ? '<p class="hint small-print compare-card-source-link"><a href="' +
            escapeAttr(srcInfo.href) +
            '">' +
            escapeHtml(srcInfo.linkLabel) +
            "</a></p>"
          : "";

      var detailActionsHtml = !compareManageMode
        ? '<p class="compare-card-actions">' +
          '<button type="button" class="btn-history-primary compare-detail-btn" data-listing-url="' +
          escapeAttr(url) +
          '" data-pid="' +
          escapeAttr(pid) +
          '" data-title="' +
          escapeAttr(r.title || "") +
          '">' +
          "查看详情" +
          "</button></p>"
        : "";

      div.innerHTML =
        "<h3>" +
        (r.title || "房源") +
        "</h3>" +
        selectRowHtml +
        '<p class="hint muted small-print compare-card-source">来源：' +
        escapeHtml(srcInfo.label) +
        "</p>" +
        sourceLinkHtml +
        "<p>租金: £" +
        (r.rent || "-") +
        "</p>" +
        "<p>卧室: " +
        (r.bedrooms || "-") +
        "</p>" +
        "<p>评分: " +
        (r.final_score || "-") +
        "</p>" +
        "<p>结论: " +
        (r.decision || "-") +
        "</p>" +
        "<p>解释: " +
        (r.explain || "-") +
        "</p>" +
        "<p>风险: " +
        (r.risks ? r.risks.join("，") : "-") +
        "</p>" +
        detailActionsHtml;

      container.appendChild(div);
    });
    syncComparePageFavoriteCount();
    updateCompareBulkToolbar();
  }

  function loadCompareFromServer() {
    var api = window.RentalAIServerFavoritesApi;
    if (api && typeof api.refreshFavoritesCache === "function") {
      return api.refreshFavoritesCache(200).then(function (rows) {
        if (rows === null) {
          renderCards(
            selectedFromLocalIds(),
            "Could not load favorites. Showing offline snapshot if available."
          );
          syncCompareDetailAfterFavoritesChange([]);
          return;
        }
        renderCards(selectedFromServerRows(rows || []));
        syncCompareDetailAfterFavoritesChange(rows || []);
      });
    }
    if (api && typeof api.fetchFavorites === "function") {
      return api.fetchFavorites(200).then(function (payload) {
        if (!payload || payload.success === false) {
          renderCards(
            selectedFromLocalIds(),
            "Could not load favorites. Showing offline snapshot if available."
          );
          syncCompareDetailAfterFavoritesChange([]);
          return;
        }
        var favs = payload.favorites || [];
        renderCards(selectedFromServerRows(favs));
        syncCompareDetailAfterFavoritesChange(favs);
      });
    }
    renderCards(selectedFromLocalIds());
    try {
      var apiFb = window.RentalAIServerFavoritesApi;
      if (apiFb && typeof apiFb.getCachedFavoritesRows === "function") {
        syncCompareDetailAfterFavoritesChange(apiFb.getCachedFavoritesRows() || []);
      }
    } catch (eFb) {}
    return Promise.resolve();
  }

  try {
    window.addEventListener("rentalai-favorite-scope-change", function () {
      compareManageMode = false;
      compareSelectedKeys = [];
      compareBulkMoreMenuOpen = false;
      syncComparePageHeaderScope();
      loadCompareFromServer().catch(function () {});
    });
  } catch (eScopePg) {}

  try {
    window.addEventListener("rentalai-favorites-updated", function (ev) {
      if (compareBulkDeleting) return;
      var rows = ev && ev.detail && ev.detail.favorites;
      if (!rows) {
        try {
          var apiEv = window.RentalAIServerFavoritesApi;
          if (apiEv && typeof apiEv.getCachedFavoritesRows === "function") {
            rows = apiEv.getCachedFavoritesRows();
          }
        } catch (eEv2) {}
      }
      if (rows == null) return;
      renderCards(selectedFromServerRows(rows));
      syncCompareDetailAfterFavoritesChange(rows);
    });
  } catch (eEv) {}

  (function bindCompareClearAllOnce() {
    var hdr = document.querySelector(".page-header");
    if (!hdr || document.getElementById("compare-clear-all-wrap")) return;
    var wrap = document.createElement("p");
    wrap.id = "compare-clear-all-wrap";
    wrap.className = "hint muted small-print";
    wrap.style.marginTop = "0.35rem";
    var btn = document.createElement("button");
    btn.type = "button";
    btn.id = "compare-clear-all-btn";
    btn.className = "btn-history-danger";
    btn.textContent = "清空收藏";
    wrap.appendChild(btn);
    hdr.appendChild(wrap);
    btn.addEventListener("click", function () {
      if (!window.confirm("清空当前会话/账号下的全部收藏？")) return;
      var api = window.RentalAIServerFavoritesApi;
      if (!api || typeof api.clearAllFavoritesForCurrentScope !== "function") return;
      btn.disabled = true;
      api
        .clearAllFavoritesForCurrentScope()
        .then(function () {
          btn.disabled = false;
          closeCompareDetail();
        })
        .catch(function () {
          btn.disabled = false;
          closeCompareDetail();
          renderCards([], null);
          lastSelected = [];
        });
    });
  })();

  (function bindCompareBulkManageOnce() {
    var hdr = document.querySelector(".page-header");
    if (!hdr || document.getElementById("compare-bulk-toolbar-wrap")) return;
    var wrap = document.createElement("p");
    wrap.id = "compare-bulk-toolbar-wrap";
    wrap.className = "hint muted small-print";
    wrap.style.marginTop = "0.25rem";
    wrap.setAttribute("role", "toolbar");
    wrap.setAttribute("aria-label", "收藏列表批量操作");
    var btnManage = document.createElement("button");
    btnManage.type = "button";
    btnManage.id = "compare-manage-toggle-btn";
    btnManage.className = "btn-history-primary";
    btnManage.textContent = "管理";
    btnManage.setAttribute("aria-pressed", "false");
    btnManage.setAttribute("aria-label", "进入或退出管理模式，以多选与批量操作");
    var btnDel = document.createElement("button");
    btnDel.type = "button";
    btnDel.id = "compare-delete-selected-btn";
    btnDel.className = "btn-history-danger";
    btnDel.textContent = "删除选中";
    btnDel.hidden = true;
    btnDel.disabled = true;
    btnDel.setAttribute("aria-label", "删除当前选中的收藏");
    var statusBulk = document.createElement("span");
    statusBulk.id = "compare-bulk-selection-status";
    statusBulk.className = "hint muted";
    statusBulk.setAttribute("aria-live", "polite");
    statusBulk.setAttribute("role", "status");
    statusBulk.setAttribute("aria-atomic", "true");
    statusBulk.hidden = true;
    statusBulk.textContent = "已选择 0 项";
    var manageHint = document.createElement("span");
    manageHint.id = "compare-bulk-manage-hint";
    manageHint.className = "hint muted small-print";
    manageHint.setAttribute("aria-live", "polite");
    manageHint.setAttribute("role", "status");
    manageHint.hidden = true;
    manageHint.textContent = "已进入管理模式";
    var btnSelToggle = document.createElement("button");
    btnSelToggle.type = "button";
    btnSelToggle.id = "compare-select-toggle-btn";
    btnSelToggle.className = "btn-history-primary";
    btnSelToggle.textContent = "全选";
    btnSelToggle.hidden = true;
    btnSelToggle.disabled = true;
    btnSelToggle.setAttribute("aria-label", "全选当前列表中的收藏");
    var moreAnchor = document.createElement("span");
    moreAnchor.id = "compare-bulk-more-anchor";
    moreAnchor.style.cssText = "position:relative;display:inline-block;vertical-align:middle";
    moreAnchor.hidden = true;
    var btnMore = document.createElement("button");
    btnMore.type = "button";
    btnMore.id = "compare-bulk-more-btn";
    btnMore.className = "btn-history-primary";
    btnMore.textContent = "更多操作";
    btnMore.disabled = true;
    btnMore.setAttribute("aria-expanded", "false");
    btnMore.setAttribute("aria-haspopup", "menu");
    btnMore.setAttribute("aria-controls", "compare-bulk-more-menu");
    var moreMenu = document.createElement("div");
    moreMenu.id = "compare-bulk-more-menu";
    moreMenu.hidden = true;
    moreMenu.setAttribute("role", "menu");
    moreMenu.setAttribute("aria-labelledby", "compare-bulk-more-btn");
    moreMenu.setAttribute("aria-hidden", "true");
    moreMenu.style.cssText =
      "position:absolute;left:0;top:100%;margin-top:4px;z-index:9999;min-width:11rem;padding:6px 0;background:#fff;border:1px solid rgba(0,0,0,.12);border-radius:6px;box-shadow:0 4px 12px rgba(0,0,0,.08)";
    function addCompareBulkMorePlaceholderItem(label) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "hint";
      b.setAttribute("role", "menuitem");
      b.style.cssText =
        "display:block;width:100%;text-align:left;padding:8px 14px;border:none;background:transparent;cursor:pointer;font:inherit";
      b.textContent = label;
      b.addEventListener("click", function (ev) {
        ev.stopPropagation();
        try {
          console.log("[RentalAI compare] bulk more placeholder:", label);
        } catch (eLog) {}
        window.alert("敬请期待（" + label + " · 占位，未接入数据）");
        compareBulkMoreMenuOpen = false;
        updateCompareBulkToolbar();
        compareBulkMoreFocusMoreButtonDeferred();
      });
      moreMenu.appendChild(b);
    }
    addCompareBulkMorePlaceholderItem("移至…");
    addCompareBulkMorePlaceholderItem("添加标签…");
    addCompareBulkMorePlaceholderItem("整理…");
    moreAnchor.appendChild(btnMore);
    moreAnchor.appendChild(moreMenu);

    wrap.appendChild(btnManage);
    wrap.appendChild(document.createTextNode(" "));
    wrap.appendChild(manageHint);
    wrap.appendChild(document.createTextNode(" "));
    wrap.appendChild(statusBulk);
    wrap.appendChild(document.createTextNode(" "));
    wrap.appendChild(btnSelToggle);
    wrap.appendChild(document.createTextNode(" "));
    wrap.appendChild(moreAnchor);
    wrap.appendChild(document.createTextNode(" "));
    wrap.appendChild(btnDel);
    hdr.appendChild(wrap);

    btnMore.addEventListener("mousedown", function (ev) {
      ev.stopPropagation();
    });
    btnMore.addEventListener("click", function (ev) {
      ev.stopPropagation();
      if (!compareManageMode || compareBulkDeleting) return;
      var dm = getCompareBulkToolbarDerived();
      if (!dm.hasSelection) return;
      var wasOpen = compareBulkMoreMenuOpen;
      compareBulkMoreMenuOpen = !wasOpen;
      updateCompareBulkToolbar();
      if (wasOpen && !compareBulkMoreMenuOpen) compareBulkMoreFocusMoreButtonDeferred();
      else if (!wasOpen && compareBulkMoreMenuOpen) compareBulkMoreFocusFirstMenuItemDeferred();
    });

    function compareBulkMoreCloseIfOutside(ev) {
      if (!compareBulkMoreMenuOpen || compareBulkDeleting) return;
      if (!compareManageMode) return;
      var a = document.getElementById("compare-bulk-more-anchor");
      if (!a || a.hidden) return;
      if (a.contains(ev.target)) return;
      compareBulkMoreMenuOpen = false;
      updateCompareBulkToolbar();
      compareBulkMoreFocusMoreButtonDeferred();
    }
    document.addEventListener("mousedown", compareBulkMoreCloseIfOutside, true);

    function compareBulkMoreOnEscape(ev) {
      if (!compareBulkMoreMenuOpen || !compareManageMode) return;
      var key = ev.key || "";
      var code = ev.code || "";
      if (key !== "Escape" && code !== "Escape" && ev.keyCode !== 27) return;
      ev.preventDefault();
      compareBulkMoreMenuOpen = false;
      updateCompareBulkToolbar();
      compareBulkMoreFocusMoreButtonDeferred();
    }
    document.addEventListener("keydown", compareBulkMoreOnEscape, true);

    btnSelToggle.addEventListener("click", function () {
      if (!compareManageMode || compareBulkDeleting) return;
      var d = getCompareBulkToolbarDerived();
      if (!d.hasItems) return;
      if (d.isAllSelected) {
        compareSelectedKeys = [];
      } else {
        compareSelectedKeys = compareVisibleFavoriteKeys(lastSelected).slice();
      }
      renderCards(lastSelected, null);
    });

    btnManage.addEventListener("click", function () {
      compareManageMode = !compareManageMode;
      if (compareManageMode) closeCompareDetail();
      if (!compareManageMode) {
        compareSelectedKeys = [];
        compareBulkMoreMenuOpen = false;
      }
      loadCompareFromServer().catch(function () {});
    });

    btnDel.addEventListener("click", function () {
      if (!compareSelectedKeys.length) return;
      if (!window.confirm("删除选中的 " + compareSelectedKeys.length + " 条收藏？")) return;
      var api = window.RentalAIServerFavoritesApi;
      if (!api || typeof api.removeFavorite !== "function") return;
      compareBulkDeleting = true;
      btnDel.disabled = true;
      updateCompareBulkToolbar();
      var keys = compareSelectedKeys.slice();
      var chain = Promise.resolve();
      keys.forEach(function (fk) {
        chain = chain.then(function () {
          var rec = findRecoByFavoriteKey(fk);
          var sid = rec ? getServerFavoriteIdForReco(rec) : "";
          if (!sid) return Promise.resolve();
          return api.removeFavorite(sid).catch(function () {});
        });
      });
      chain
        .then(function () {
          compareBulkDeleting = false;
          compareSelectedKeys = [];
          compareBulkMoreMenuOpen = false;
          compareManageMode = false;
          return loadCompareFromServer();
        })
        .then(function () {
          btnDel.disabled = false;
          updateCompareBulkToolbar();
        })
        .catch(function () {
          compareBulkDeleting = false;
          btnDel.disabled = false;
          updateCompareBulkToolbar();
          loadCompareFromServer().catch(function () {});
        });
    });
  })();

  loadCompareFromServer().catch(function (err) {
    console.error(err);
    renderCards(
      selectedFromLocalIds(),
      "Could not load favorites. Showing offline snapshot if available."
    );
    syncCompareDetailAfterFavoritesChange([]);
  });
})();
