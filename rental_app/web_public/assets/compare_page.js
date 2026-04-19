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
    return recos.filter(function (r) {
      return rows.some(function (f) {
        return rowMatchesFavorite(r, f);
      });
    });
  }

  function selectedFromLocalIds() {
    var favsLocal = readLocalFavIds();
    var api = window.RentalAIServerFavoritesApi;
    return recos.filter(function (r) {
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
    });
  }

  function renderCards(selected, bannerText) {
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
        "</p>";

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
          return;
        }
        renderCards(selectedFromServerRows(rows || []));
      });
    }
    if (api && typeof api.fetchFavorites === "function") {
      return api.fetchFavorites(200).then(function (payload) {
        if (!payload || payload.success === false) {
          renderCards(
            selectedFromLocalIds(),
            "Could not load favorites. Showing offline snapshot if available."
          );
          return;
        }
        renderCards(selectedFromServerRows(payload.favorites || []));
      });
    }
    renderCards(selectedFromLocalIds());
    return Promise.resolve();
  }

  try {
    window.addEventListener("rentalai-favorites-updated", function (ev) {
      var rows = ev && ev.detail && ev.detail.favorites;
      if (!rows) return;
      renderCards(selectedFromServerRows(rows));
    });
  } catch (eEv) {}

  loadCompareFromServer().catch(function (err) {
    console.error(err);
    renderCards(
      selectedFromLocalIds(),
      "Could not load favorites. Showing offline snapshot if available."
    );
  });
})();
