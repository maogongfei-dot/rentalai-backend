/**
 * 服务端收藏 API（POST/GET/DELETE /favorites）。
 *
 * 收藏用户作用域：与后端 _get_favorite_scope_user_id 对齐 — Bearer 为真实用户，否则 X-Guest-Session → guest:<session>。
 * 游客会话隔离：未登录用户通过 X-Guest-Session 绑定到 guest:<session>（与 api_server 一致）。
 * 登录用户与游客收藏不合并：有 Bearer 时后端以用户 id 为准，仍附带 X-Guest-Session 供对齐/调试。
 */
(function (global) {
  function mergeFavoritesHeaders(headers) {
    headers = headers && typeof headers === "object" ? headers : {};
    if (global.rentalaiMergeAuthHeaders) {
      headers = global.rentalaiMergeAuthHeaders(headers);
    } else {
      var tok = global.rentalaiGetBearerToken && global.rentalaiGetBearerToken();
      if (tok && !headers["Authorization"] && !headers["authorization"]) {
        headers["Authorization"] = "Bearer " + tok;
      }
    }
    /* 游客收藏隔离：未登录用户通过 X-Guest-Session 绑定到 guest:<session> */
    try {
      var S = global.RentalAIUserStore;
      if (S && typeof S.getOrCreateGuestSessionId === "function") {
        headers["X-Guest-Session"] = S.getOrCreateGuestSessionId();
      }
    } catch (e) {}
    if (!headers["X-Guest-Session"] && !headers["x-guest-session"]) {
      if (global.rentalaiGetOrCreateGuestSessionId) {
        headers["X-Guest-Session"] = global.rentalaiGetOrCreateGuestSessionId();
      }
    }
    return headers;
  }

  function favoritesFetch(path, init) {
    init = init || {};
    var url = global.rentalaiApiUrl ? global.rentalaiApiUrl(path) : path;
    var h = init.headers;
    if (h instanceof Headers) {
      var o = {};
      h.forEach(function (v, k) {
        o[k] = v;
      });
      h = o;
    }
    h = mergeFavoritesHeaders(h && typeof h === "object" ? h : {});
    var m = (init.method || "GET").toUpperCase();
    if (m === "POST" || m === "PUT" || m === "PATCH") {
      h["Content-Type"] = h["Content-Type"] || "application/json";
    }
    var cred =
      init.credentials != null
        ? init.credentials
        : global.rentalaiDefaultFetchCredentials
          ? global.rentalaiDefaultFetchCredentials()
          : "same-origin";
    return fetch(url, {
      method: init.method || "GET",
      headers: h,
      body: init.body,
      credentials: cred,
      signal: init.signal,
      cache: init.cache,
    });
  }

  /** ---------- Step7：全站统一 favoriteKey（写入 property_id / 匹配 / 去重） ---------- */

  function pickListingUrl(o) {
    o = o || {};
    var cand = [o.listing_url, o.source_url, o.url, o.link];
    for (var i = 0; i < cand.length; i++) {
      var v = cand[i];
      if (v == null) continue;
      var s = String(v).trim();
      if (s && /^https?:\/\//i.test(s)) return s;
    }
    return "";
  }

  function canonicalListingUrl(u) {
    var s = String(u || "").trim();
    if (!s) return "";
    try {
      var x = new URL(s);
      var path = x.pathname.replace(/\/+$/, "") || "/";
      return String(x.origin + path + x.search).toLowerCase();
    } catch (e0) {
      return s.toLowerCase().replace(/\/+$/, "");
    }
  }

  /**
   * 任意可收藏对象 → 稳定字符串（优先 URL，其次 listing_id/property_id/rank 等）。
   * 与 SQLite 中 property_id、list 匹配、去重共用同一规则。
   */
  function buildFavoriteKey(o) {
    o = o || {};
    var pidRaw = o.property_id != null ? String(o.property_id).trim() : "";
    if (pidRaw.indexOf("u:") === 0) return normalizeFavoriteKey(pidRaw);
    if (pidRaw.indexOf("p:") === 0) return pidRaw;
    var urlFirst = pickListingUrl(o);
    if (urlFirst) return "u:" + canonicalListingUrl(urlFirst);
    var cand = [o.property_id, o.listing_id, o.rank, o.record_id, o.external_id];
    for (var i = 0; i < cand.length; i++) {
      var c = cand[i];
      if (c !== undefined && c !== null && String(c).trim() !== "") {
        return "p:" + String(c).trim();
      }
    }
    return "p:empty";
  }

  function normalizeFavoriteKey(k) {
    var s = String(k || "").trim();
    if (!s) return "";
    if (s.indexOf("u:") === 0) return "u:" + canonicalListingUrl(s.slice(2));
    if (s.indexOf("p:") === 0 || s.indexOf("x:") === 0) return s;
    if (/^https?:\/\//i.test(s)) return "u:" + canonicalListingUrl(s);
    return "p:" + s;
  }

  function favoriteKeysEqual(a, b) {
    return normalizeFavoriteKey(a) === normalizeFavoriteKey(b);
  }

  function dedupeFavoriteRows(rows) {
    rows = rows || [];
    var seen = {};
    var out = [];
    for (var i = 0; i < rows.length; i++) {
      var r = rows[i];
      var k = normalizeFavoriteKey(
        buildFavoriteKey({ listing_url: r.listing_url, property_id: r.property_id })
      );
      if (!k || k === "p:empty") {
        out.push(r);
        continue;
      }
      if (seen[k]) continue;
      seen[k] = true;
      out.push(r);
    }
    return out;
  }

  /** 收藏行 f 与推荐行 r（结果页 / 对比页）是否同一房源 */
  function favoriteRowMatchesReco(f, r) {
    r = r || {};
    var kf = buildFavoriteKey({ listing_url: f.listing_url, property_id: f.property_id });
    var kr = buildFavoriteKey({
      listing_url: r.listing_url || r.source_url || r.url,
      source_url: r.source_url,
      url: r.url,
      property_id: r.listing_id != null ? r.listing_id : r.rank,
      listing_id: r.listing_id,
      rank: r.rank,
    });
    return favoriteKeysEqual(kf, kr);
  }

  /* ---------- Step11：客户端收藏详情元数据（localStorage，不按 favoriteKey 改规则，仅增补存储） ---------- */

  var META_STR_MAX = 9000;

  function getFavoriteDetailMetaLsKey() {
    var bucket = "default";
    try {
      if (global.RentalAILocalAuth && typeof global.RentalAILocalAuth.favStorageKey === "function") {
        bucket = String(global.RentalAILocalAuth.favStorageKey() || "default").replace(/[^a-zA-Z0-9:_-]/g, "_");
      }
    } catch (eB) {}
    if (bucket.length > 96) bucket = bucket.slice(0, 96);
    return "rentalai_favorite_detail_meta_v1__" + bucket;
  }

  function loadFavoriteDetailMetaMap() {
    try {
      var raw = localStorage.getItem(getFavoriteDetailMetaLsKey());
      var o = raw ? JSON.parse(raw) : {};
      return o && typeof o === "object" ? o : {};
    } catch (e0) {
      return {};
    }
  }

  function saveFavoriteDetailMetaMap(map) {
    try {
      localStorage.setItem(getFavoriteDetailMetaLsKey(), JSON.stringify(map));
    } catch (e1) {}
  }

  function clipStr(s, n) {
    s = s == null ? "" : String(s);
    n = n || 800;
    if (s.length <= n) return s;
    return s.slice(0, n - 1) + "…";
  }

  function clipStrArray(arr, maxItems, eachMax) {
    if (!Array.isArray(arr)) return [];
    var out = [];
    var i;
    var lim = Math.min(maxItems || 12, arr.length);
    for (i = 0; i < lim; i++) {
      out.push(clipStr(arr[i], eachMax || 400));
    }
    return out;
  }

  function minimizeDetailSnapshot(snap) {
    if (!snap || typeof snap !== "object") return null;
    var out;
    try {
      out = JSON.parse(JSON.stringify(snap));
    } catch (eJ) {
      return null;
    }
    if (out.variant === "legacy") {
      if (Array.isArray(out.recommendations_top) && out.recommendations_top.length > 10) {
        out.recommendations_top = out.recommendations_top.slice(0, 10);
      }
    }
    if (out.variant === "housing") {
      if (Array.isArray(out.top_deals) && out.top_deals.length > 10) {
        out.top_deals = out.top_deals.slice(0, 10);
      }
      if (out.market_snapshot_zh) out.market_snapshot_zh = clipStr(out.market_snapshot_zh, 6000);
    }
    try {
      if (JSON.stringify(out).length > META_STR_MAX) {
        return {
          variant: out.variant || "legacy",
          summary: out.summary || {},
          recommendations_top: Array.isArray(out.recommendations_top) ? out.recommendations_top.slice(0, 3) : [],
        };
      }
    } catch (eSz) {}
    return out;
  }

  function buildRecoMinDetailSnapshot(payload) {
    payload = payload || {};
    var risks = payload.risks;
    if (typeof risks === "string") {
      try {
        risks = JSON.parse(risks);
      } catch (eR) {
        risks = [];
      }
    }
    return {
      variant: "reco_min",
      title: clipStr(payload.title, 400),
      rent: payload.rent != null ? payload.rent : payload.price,
      bedrooms: payload.bedrooms,
      postcode: payload.postcode != null ? String(payload.postcode) : null,
      listing_url: pickListingUrl(payload),
      explain: clipStr(payload.explain, 2500),
      decision: payload.decision,
      decision_reason: clipStr(payload.decision_reason, 1500),
      risks: clipStrArray(risks, 12, 400),
      final_score: payload.final_score,
      listing_id: payload.listing_id != null ? payload.listing_id : payload.listingId,
      rank: payload.rank != null ? payload.rank : null,
    };
  }

  function historyEntryMatchesFavoritePayload(entry, payload) {
    if (!entry || entry.type !== "property") return false;
    var snap = entry.detail_snapshot;
    if (!snap) return false;
    var pid = String(payload.propertyId != null ? payload.propertyId : payload.property_id || "").trim();
    var purl = pickListingUrl(payload);
    var pcanonical = purl ? canonicalListingUrl(purl) : "";
    var pt = (payload.title || "").trim();
    if (snap.variant === "legacy") {
      var tops = snap.recommendations_top || [];
      var j;
      for (j = 0; j < tops.length; j++) {
        var row = tops[j] || {};
        var ru = String(row.source_url || "").trim();
        if (pcanonical && ru && canonicalListingUrl(ru) === pcanonical) return true;
        if (pid && row.listing_id != null && String(row.listing_id) === pid) return true;
        if (pid && row.rank != null && String(row.rank) === pid) return true;
        var rt = String(row.title || "").trim();
        if (pt && rt && pt === rt) return true;
      }
    }
    if (snap.variant === "housing") {
      var deals = snap.top_deals || [];
      var k;
      for (k = 0; k < deals.length; k++) {
        var d = deals[k] || {};
        var du = String(d.listing_url || d.url || "").trim();
        if (pcanonical && du && canonicalListingUrl(du) === pcanonical) return true;
        var dt = String(d.title || d.address || "").trim();
        if (pt && dt && pt === dt) return true;
      }
    }
    return false;
  }

  function findMatchingPropertyHistoryEntry(payload) {
    try {
      var S = global.RentalAIAnalysisHistoryStore;
      if (!S) return null;
      var hintId =
        payload.historyEntryId ||
        payload.history_id ||
        payload.recordId ||
        payload.record_id ||
        payload.analysisId ||
        payload.analysis_id;
      if (hintId && typeof S.listForUser === "function") {
        var all = S.listForUser() || [];
        var a;
        for (a = 0; a < all.length; a++) {
          if (all[a] && String(all[a].id) === String(hintId)) return all[a];
        }
      }
      if (typeof S.listByType !== "function") return null;
      var props = S.listByType("property") || [];
      var i;
      for (i = 0; i < props.length; i++) {
        var entry = props[i];
        if (historyEntryMatchesFavoritePayload(entry, payload)) return entry;
      }
    } catch (eH) {}
    return null;
  }

  function buildFavoriteClientMeta(fkNorm, payload, histEntry) {
    payload = payload || {};
    var meta = {
      favoriteKey: fkNorm,
      savedAt: new Date().toISOString(),
      historyId: null,
      recordId: null,
      analysisId: null,
      source: payload.source || null,
      sourceType: payload.sourceType || payload.source_type || null,
      serverFavoriteId: null,
      titleHint: clipStr(payload.title, 200),
      detailSnapshot: null,
    };
    if (histEntry && histEntry.id) {
      meta.historyId = histEntry.id;
      meta.recordId = histEntry.id;
      meta.analysisId = histEntry.id;
      meta.detailSnapshot = minimizeDetailSnapshot(histEntry.detail_snapshot);
    }
    if (!meta.detailSnapshot) {
      meta.detailSnapshot = buildRecoMinDetailSnapshot(payload);
    }
    if (!meta.source) meta.source = histEntry ? "unified_history" : "favorite";
    if (!meta.sourceType) meta.sourceType = histEntry ? "unified_property" : "legacy_recommendation";
    try {
      if (JSON.stringify(meta).length > META_STR_MAX + 2000) {
        meta.detailSnapshot = buildRecoMinDetailSnapshot(payload);
      }
    } catch (eM) {}
    return meta;
  }

  function mergeFavoriteDetailMeta(fkNorm, patch) {
    var kNorm = normalizeFavoriteKey(fkNorm);
    if (!kNorm || kNorm === "p:empty") return;
    var map = loadFavoriteDetailMetaMap();
    var prev = map[kNorm] || {};
    var next = {};
    var k;
    for (k in prev) {
      if (Object.prototype.hasOwnProperty.call(prev, k)) next[k] = prev[k];
    }
    for (k in patch) {
      if (Object.prototype.hasOwnProperty.call(patch, k)) next[k] = patch[k];
    }
    next.favoriteKey = kNorm;
    if (!next.savedAt) next.savedAt = new Date().toISOString();
    map[kNorm] = next;
    saveFavoriteDetailMetaMap(map);
  }

  function removeFavoriteDetailMetaByServerId(serverFavoriteId) {
    var sid = String(serverFavoriteId || "").trim();
    if (!sid) return;
    var map = loadFavoriteDetailMetaMap();
    var changed = false;
    Object.keys(map).forEach(function (k) {
      var m = map[k];
      if (m && String(m.serverFavoriteId || "") === sid) {
        delete map[k];
        changed = true;
      }
    });
    if (changed) saveFavoriteDetailMetaMap(map);
  }

  function getFavoriteDetailMetaByKey(favoriteKey) {
    var kNorm = normalizeFavoriteKey(favoriteKey);
    var map = loadFavoriteDetailMetaMap();
    return map[kNorm] || null;
  }

  function getFavoriteDetailMetaForFavoriteRow(row) {
    row = row || {};
    var fk = buildFavoriteKey({ listing_url: row.listing_url, property_id: row.property_id });
    return getFavoriteDetailMetaByKey(fk);
  }

  function postAddFavorite(payload) {
    var body = payload && typeof payload === "object" ? payload : {};
    var fk = buildFavoriteKey({
      listing_url: body.listing_url,
      source_url: body.source_url,
      url: body.url,
      property_id: body.propertyId != null ? body.propertyId : body.property_id,
      listing_id: body.listing_id,
      rank: body.rank,
      record_id: body.record_id,
      external_id: body.external_id,
    });
    var listingOut =
      body.listing_url != null && String(body.listing_url).trim()
        ? body.listing_url
        : body.source_url != null && String(body.source_url).trim()
          ? body.source_url
          : null;
    if (fk.indexOf("u:") === 0 && !listingOut) {
      listingOut = fk.slice(2);
    }
    return favoritesFetch("/favorites", {
      method: "POST",
      body: JSON.stringify({
        listing_url: listingOut != null ? listingOut : null,
        property_id: fk,
        title: body.title != null ? body.title : null,
        price: body.price != null ? body.price : null,
        postcode: body.postcode != null ? body.postcode : null,
      }),
    }).then(function (res) {
      return res.json().then(function (data) {
        if (!res.ok) {
          var err = new Error((data && data.message) || res.statusText || "add_favorite_failed");
          err.status = res.status;
          err.body = data;
          throw err;
        }
        return data;
      });
    });
  }

  function deleteFavoriteById(favoriteId) {
    var id = String(favoriteId || "").trim();
    if (!id) {
      return Promise.reject(new Error("missing_favorite_id"));
    }
    return favoritesFetch("/favorites/" + encodeURIComponent(id), {
      method: "DELETE",
    }).then(function (res) {
      return res.json().then(function (data) {
        if (!res.ok) {
          var err = new Error((data && data.message) || res.statusText || "remove_favorite_failed");
          err.status = res.status;
          err.body = data;
          throw err;
        }
        return data;
      });
    });
  }

  function listFavorites(limit) {
    var q = typeof limit === "number" && limit > 0 ? "?limit=" + encodeURIComponent(String(limit)) : "";
    return favoritesFetch("/favorites" + q, { method: "GET" }).then(function (res) {
      return res.json().then(function (data) {
        if (!res.ok) {
          var err = new Error((data && data.message) || res.statusText || "list_favorites_failed");
          err.status = res.status;
          err.body = data;
          throw err;
        }
        return data;
      });
    });
  }

  /**
   * 读取当前收藏作用域下的 favorites（GET /favorites）。
   * 已登录：Bearer → 账号收藏；未登录：X-Guest-Session → guest session 桶；登录与游客不合并。
   * 复用 mergeFavoritesHeaders（Authorization + X-Guest-Session）；失败时不抛错，便于列表页降级。
   */
  function fetchFavorites(limit) {
    var q = typeof limit === "number" && limit > 0 ? "?limit=" + encodeURIComponent(String(limit)) : "";
    return favoritesFetch("/favorites" + q, { method: "GET" }).then(function (res) {
      return res
        .json()
        .catch(function () {
          return {};
        })
        .then(function (body) {
          body = body || {};
          if (!res.ok) {
            body.success = false;
            return body;
          }
          body.success = true;
          if (!body.favorites) body.favorites = [];
          return body;
        });
    });
  }

  /** 全站统一收藏快照（当前作用域 GET /favorites）；跨页以本缓存 + 事件为准，避免各页各读一份。 */
  var _favoritesCacheRows = null;

  function emitFavoritesUpdated(rows) {
    try {
      window.dispatchEvent(
        new CustomEvent("rentalai-favorites-updated", { detail: { favorites: rows || [] } })
      );
    } catch (eEmit) {}
  }

  function invalidateFavoritesCache() {
    _favoritesCacheRows = null;
  }

  /**
   * 拉取并写入缓存，广播 rentalai-favorites-updated。
   * @returns {Promise<Array|null>} 成功返回行数组，失败返回 null
   */
  function refreshFavoritesCache(limit) {
    return fetchFavorites(limit != null ? limit : 200).then(function (body) {
      if (!body || body.success === false) {
        invalidateFavoritesCache();
        return null;
      }
      var rows = dedupeFavoriteRows(body.favorites || []);
      _favoritesCacheRows = rows.slice();
      emitFavoritesUpdated(_favoritesCacheRows);
      return _favoritesCacheRows;
    });
  }

  function getCachedFavoritesRows() {
    return _favoritesCacheRows ? _favoritesCacheRows.slice() : null;
  }

  /** Step15：与 GET /favorites 缓存一致的数量（当前作用域）；未拉取过缓存时为 0。 */
  function getFavoriteCountForCurrentScope() {
    var rows = getCachedFavoritesRows();
    return rows ? rows.length : 0;
  }

  /** 服务端行 ↔ 按钮上的 propertyId / listingUrl（均已纳入 buildFavoriteKey）。 */
  function favoriteMatchesIdentifiers(f, propertyId, listingUrl) {
    var kf = buildFavoriteKey({ listing_url: f.listing_url, property_id: f.property_id });
    var kb = buildFavoriteKey({ property_id: propertyId, listing_url: listingUrl });
    if (favoriteKeysEqual(kf, kb)) return true;
    /* 兼容旧库：裸数字 id 与当时写入的 listing_id/rank */
    var fp = f.property_id != null ? String(f.property_id).trim() : "";
    var pid = propertyId != null ? String(propertyId).trim() : "";
    var url = (listingUrl || "").trim();
    var fu = (f.listing_url || "").trim();
    if (pid && fp && fp === pid) return true;
    if (url && fu && canonicalListingUrl(fu) === canonicalListingUrl(url)) return true;
    return false;
  }

  function addFavoriteThenRefresh(payload) {
    payload = payload && typeof payload === "object" ? payload : {};
    var fkNorm = buildFavoriteKey({
      listing_url: payload.listing_url,
      source_url: payload.source_url,
      url: payload.url,
      property_id: payload.propertyId != null ? payload.propertyId : payload.property_id,
      listing_id: payload.listing_id,
      rank: payload.rank,
      record_id: payload.record_id,
      external_id: payload.external_id,
    });
    var histEntry = findMatchingPropertyHistoryEntry(payload);
    var meta = buildFavoriteClientMeta(fkNorm, payload, histEntry);
    mergeFavoriteDetailMeta(fkNorm, meta);
    return postAddFavorite(payload).then(function (data) {
      var fav = data && data.favorite;
      if (fav && fav.id) {
        mergeFavoriteDetailMeta(fkNorm, { serverFavoriteId: fav.id });
      }
      return refreshFavoritesCache(500).then(function () {
        return data;
      });
    });
  }

  function removeFavoriteThenRefresh(favoriteId) {
    return deleteFavoriteById(favoriteId).then(function (data) {
      removeFavoriteDetailMetaByServerId(favoriteId);
      return refreshFavoritesCache(500).then(function () {
        return data;
      });
    });
  }

  /** Step14：清空当前作用域收藏 — 仅影响当前 Bearer / guest session 对应的服务端桶；并清空本机 fav_list_* 与 detail meta，再单次 refresh（供跨标签 storage 同步）。 */
  function clearLocalFavoriteKeysForCurrentScope() {
    try {
      if (global.RentalAILocalAuth && typeof global.RentalAILocalAuth.favStorageKey === "function") {
        global.localStorage.setItem(global.RentalAILocalAuth.favStorageKey(), "[]");
      }
    } catch (eLoc) {}
    try {
      saveFavoriteDetailMetaMap({});
    } catch (eMeta) {}
  }

  function clearAllFavoritesForCurrentScope() {
    return fetchFavorites(500)
      .then(function (body) {
        if (!body || body.success === false) {
          clearLocalFavoriteKeysForCurrentScope();
          invalidateFavoritesCache();
          emitFavoritesUpdated([]);
          return { success: false, clearedLocalOnly: true };
        }
        var rows = Array.isArray(body.favorites) ? body.favorites : [];
        var chain = Promise.resolve();
        rows.forEach(function (row) {
          if (!row || !row.id) return;
          chain = chain.then(function () {
            return deleteFavoriteById(row.id).catch(function () {});
          });
        });
        return chain.then(function () {
          return refreshFavoritesCache(500).then(function (cachedRows) {
            if (!cachedRows || cachedRows.length === 0) {
              clearLocalFavoriteKeysForCurrentScope();
            }
            return { success: true, removed: rows.length };
          });
        });
      })
      .catch(function () {
        clearLocalFavoriteKeysForCurrentScope();
        invalidateFavoritesCache();
        emitFavoritesUpdated([]);
        return { success: false, clearedLocalOnly: true };
      });
  }

  try {
    window.addEventListener("rentalai-favorite-scope-change", function () {
      invalidateFavoritesCache();
    });
  } catch (eScope) {}

  /** Step13：跨标签页同步 — 仅当其它标签页改了当前作用域相关的 localStorage 时，GET /favorites 重载缓存并派发 rentalai-favorites-updated（本标签页自身写入不会触发 storage）。 */
  function currentScopeFavoriteStorageWatchKeys() {
    var keys = [];
    try {
      if (global.RentalAILocalAuth && typeof global.RentalAILocalAuth.favStorageKey === "function") {
        keys.push(global.RentalAILocalAuth.favStorageKey());
      }
    } catch (eW1) {}
    keys.push(getFavoriteDetailMetaLsKey());
    return keys;
  }

  function storageKeyMatchesCurrentFavoriteScope(storageKey) {
    if (storageKey == null || storageKey === "") return false;
    var watch = currentScopeFavoriteStorageWatchKeys();
    var i;
    for (i = 0; i < watch.length; i++) {
      if (storageKey === watch[i]) return true;
    }
    return false;
  }

  function onCrossTabFavoriteStorage(ev) {
    try {
      if (!ev || ev.storageArea !== global.localStorage) return;
      if (!storageKeyMatchesCurrentFavoriteScope(ev.key)) return;
      refreshFavoritesCache(200).catch(function () {});
    } catch (eSt) {}
  }

  var _crossTabFavoriteStorageBound = false;

  function bindCrossTabFavoriteStorageOnce() {
    if (_crossTabFavoriteStorageBound) return;
    _crossTabFavoriteStorageBound = true;
    global.addEventListener("storage", onCrossTabFavoriteStorage);
  }

  function unbindCrossTabFavoriteStorage() {
    if (!_crossTabFavoriteStorageBound) return;
    global.removeEventListener("storage", onCrossTabFavoriteStorage);
    _crossTabFavoriteStorageBound = false;
  }

  function rehydrateFavoritesForCurrentScope() {
    return refreshFavoritesCache(200);
  }

  bindCrossTabFavoriteStorageOnce();

  global.RentalAIServerFavoritesApi = {
    mergeFavoritesHeaders: mergeFavoritesHeaders,
    addFavorite: addFavoriteThenRefresh,
    removeFavorite: removeFavoriteThenRefresh,
    listFavorites: listFavorites,
    fetchFavorites: fetchFavorites,
    refreshFavoritesCache: refreshFavoritesCache,
    getCachedFavoritesRows: getCachedFavoritesRows,
    getFavoriteCountForCurrentScope: getFavoriteCountForCurrentScope,
    favoriteMatchesIdentifiers: favoriteMatchesIdentifiers,
    buildFavoriteKey: buildFavoriteKey,
    normalizeFavoriteKey: normalizeFavoriteKey,
    favoriteKeysEqual: favoriteKeysEqual,
    favoriteRowMatchesReco: favoriteRowMatchesReco,
    _internalPostAddFavorite: postAddFavorite,
    _internalDeleteFavoriteById: deleteFavoriteById,
    getFavoriteDetailMetaByKey: getFavoriteDetailMetaByKey,
    getFavoriteDetailMetaForFavoriteRow: getFavoriteDetailMetaForFavoriteRow,
    rehydrateFavoritesForCurrentScope: rehydrateFavoritesForCurrentScope,
    unbindCrossTabFavoriteStorage: unbindCrossTabFavoriteStorage,
    clearAllFavoritesForCurrentScope: clearAllFavoritesForCurrentScope,
  };
})(window);
