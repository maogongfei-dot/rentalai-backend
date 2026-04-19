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

  /** 本地 fav 列表：仅作服务端失败或未加载 API 时的 fallback（与 favStorageKey 作用域一致）。 */
  var favKey =
    window.RentalAILocalAuth && window.RentalAILocalAuth.favStorageKey
      ? window.RentalAILocalAuth.favStorageKey()
      : "fav_list";
  var favsLocal = [];
  try {
    favsLocal = JSON.parse(localStorage.getItem(favKey) || "[]");
    if (!Array.isArray(favsLocal)) favsLocal = [];
  } catch (e1) {
    favsLocal = [];
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

  function rowMatchesFavorite(r, f) {
    var pid = String(r.listing_id != null ? r.listing_id : r.rank);
    var fp = f.property_id != null ? String(f.property_id).trim() : "";
    var url = (r.source_url || r.listing_url || r.url || "").trim();
    var fu = (f.listing_url || "").trim();
    if (fp && fp === pid) return true;
    if (fu && url && fu === url) return true;
    return false;
  }

  /** 收藏列表读取逻辑：服务端 favorites 为主（当前收藏作用域由请求头决定）。 */
  function selectedFromServerRows(rows) {
    return recos.filter(function (r) {
      return rows.some(function (f) {
        return rowMatchesFavorite(r, f);
      });
    });
  }

  /** 降级：仅用本地 property id 列表与推荐行对齐。 */
  function selectedFromLocalIds() {
    return recos.filter(function (r) {
      return favsLocal.includes(String(r.listing_id || r.rank));
    });
  }

  /**
   * 列表与「是否已收藏」对齐 server rows：卡片集合即当前作用域内收藏与本次 session 推荐的交集。
   */
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

  var api = window.RentalAIServerFavoritesApi;

  /*
   * 收藏列表按当前收藏作用域加载：已登录读账号收藏，未登录读 guest session 收藏；登录与游客不合并。
   * 主数据源优先 server favorites；本地 fav_list 仅失败时 fallback。
   */
  if (api && typeof api.fetchFavorites === "function") {
    api
      .fetchFavorites(200)
      .then(function (payload) {
        if (!payload || payload.success === false) {
          renderCards(
            selectedFromLocalIds(),
            "Could not load favorites. Showing offline snapshot if available."
          );
          return;
        }
        var rows = payload.favorites || [];
        var selected = selectedFromServerRows(rows);
        renderCards(selected);
      })
      .catch(function (err) {
        console.error(err);
        renderCards(
          selectedFromLocalIds(),
          "Could not load favorites. Showing offline snapshot if available."
        );
      });
  } else {
    renderCards(selectedFromLocalIds());
  }
})();
