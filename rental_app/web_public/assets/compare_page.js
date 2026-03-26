(function () {
  // 收藏：按当前用户读取 fav_list_{user_id}
  var favKey =
    window.RentalAILocalAuth && window.RentalAILocalAuth.favStorageKey
      ? window.RentalAILocalAuth.favStorageKey()
      : "fav_list";
  var favs = JSON.parse(localStorage.getItem(favKey) || "[]");

  var raw = sessionStorage.getItem("ai_analyze_last");
  var data;
  try {
    data = raw ? JSON.parse(raw) : null;
  } catch (e) {
    data = null;
  }

  var recos = (data && data.recommendations) || [];

  var selected = recos.filter(function (r) {
    return favs.includes(String(r.listing_id || r.rank));
  });

  var container = document.getElementById("compare-list");
  if (!container) return;

  if (!selected.length) {
    container.innerHTML = "<p>暂无收藏房源</p>";
  } else {
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
})();
