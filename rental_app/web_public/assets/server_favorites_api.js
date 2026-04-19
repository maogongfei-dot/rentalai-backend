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
    return postAddFavorite(payload).then(function (data) {
      return refreshFavoritesCache(500).then(function () {
        return data;
      });
    });
  }

  function removeFavoriteThenRefresh(favoriteId) {
    return deleteFavoriteById(favoriteId).then(function (data) {
      return refreshFavoritesCache(500).then(function () {
        return data;
      });
    });
  }

  try {
    window.addEventListener("rentalai-favorite-scope-change", function () {
      invalidateFavoritesCache();
    });
  } catch (eScope) {}

  global.RentalAIServerFavoritesApi = {
    mergeFavoritesHeaders: mergeFavoritesHeaders,
    addFavorite: addFavoriteThenRefresh,
    removeFavorite: removeFavoriteThenRefresh,
    listFavorites: listFavorites,
    fetchFavorites: fetchFavorites,
    refreshFavoritesCache: refreshFavoritesCache,
    getCachedFavoritesRows: getCachedFavoritesRows,
    favoriteMatchesIdentifiers: favoriteMatchesIdentifiers,
    buildFavoriteKey: buildFavoriteKey,
    normalizeFavoriteKey: normalizeFavoriteKey,
    favoriteKeysEqual: favoriteKeysEqual,
    favoriteRowMatchesReco: favoriteRowMatchesReco,
    _internalPostAddFavorite: postAddFavorite,
    _internalDeleteFavoriteById: deleteFavoriteById,
  };
})(window);
