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
      inner.innerHTML = ui.renderDetailBodyHtml(entry);
      if (typeof ui.hydrateFavoriteButtons === "function") ui.hydrateFavoriteButtons();
    } else {
      inner.innerHTML =
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
      var btn = ev.target && ev.target.closest && ev.target.closest(".compare-detail-btn");
      if (!btn) return;
      ev.preventDefault();
      var r = findRecoFromButton(btn);
      if (!r) return;
      openCompareDetail(r);
    });
  }
  bindCompareDetailOnce();

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

  function emptyStateHtml() {
    return (
      "<p>" +
      (isGuestViewer()
        ? "No saved houses for this guest session yet."
        : "No saved houses for this account yet.") +
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

  function renderCards(selected, bannerText) {
    lastSelected = selected || [];
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
      var first = empWrap.firstChild;
      if (first) container.appendChild(first);
      return;
    }
    selected.forEach(function (r) {
      var div = document.createElement("div");
      div.className = "compare-card";
      var url = recoUrl(r);
      var pid = recoPid(r);

      div.innerHTML =
        "<h3>" +
        (r.title || "房源") +
        "</h3>" +
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
        '<p class="compare-card-actions">' +
        '<button type="button" class="btn-history-primary compare-detail-btn" data-listing-url="' +
        escapeAttr(url) +
        '" data-pid="' +
        escapeAttr(pid) +
        '" data-title="' +
        escapeAttr(r.title || "") +
        '">' +
        "查看详情" +
        "</button></p>";

      container.appendChild(div);
    });
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
    window.addEventListener("rentalai-favorites-updated", function (ev) {
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

  loadCompareFromServer().catch(function (err) {
    console.error(err);
    renderCards(
      selectedFromLocalIds(),
      "Could not load favorites. Showing offline snapshot if available."
    );
    syncCompareDetailAfterFavoritesChange([]);
  });
})();
