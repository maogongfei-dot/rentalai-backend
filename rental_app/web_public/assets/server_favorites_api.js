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

  function addFavorite(payload) {
    var body = payload && typeof payload === "object" ? payload : {};
    return favoritesFetch("/favorites", {
      method: "POST",
      body: JSON.stringify({
        listing_url: body.listing_url != null ? body.listing_url : null,
        property_id: body.propertyId != null ? body.propertyId : body.property_id,
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

  function removeFavorite(favoriteId) {
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

  global.RentalAIServerFavoritesApi = {
    mergeFavoritesHeaders: mergeFavoritesHeaders,
    addFavorite: addFavorite,
    removeFavorite: removeFavorite,
    listFavorites: listFavorites,
  };
})(window);
