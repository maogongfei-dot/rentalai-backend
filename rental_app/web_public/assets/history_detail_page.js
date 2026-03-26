/**
 * History v1 详情页：从 sessionStorage.history_current 渲染单条分析快照（列表页已按 user_id 过滤）。
 */
(function () {
  var root = document.getElementById("history-detail-root");
  if (!root) return;

  var raw = sessionStorage.getItem("history_current");
  var data = null;
  try {
    data = raw ? JSON.parse(raw) : null;
  } catch (e) {
    data = null;
  }

  if (!data || !data.id) {
    var err = document.createElement("p");
    err.className = "hint";
    err.textContent = "未找到历史记录，请从分析历史列表进入。";
    root.appendChild(err);
    return;
  }

  var h1 = document.createElement("h1");
  h1.className = "section-title";
  h1.textContent = "历史详情";
  root.appendChild(h1);

  var secQ = document.createElement("section");
  secQ.className = "card";
  secQ.innerHTML =
    "<h2 class='section-title'>原始需求</h2><p class='hint'>" +
    escapeHtml(String(data.raw_user_query || "—")) +
    "</p>";
  root.appendChild(secQ);

  var secS = document.createElement("section");
  secS.className = "card";
  secS.innerHTML = "<h2 class='section-title'>结构化解析</h2>";
  var dl = document.createElement("dl");
  dl.className = "kv-list";
  var sq = data.structured_query || {};
  var keys = Object.keys(sq);
  if (!keys.length) {
    var empty = document.createElement("p");
    empty.className = "hint";
    empty.textContent = "—";
    secS.appendChild(empty);
  } else {
    keys.forEach(function (k) {
      var dt = document.createElement("dt");
      dt.textContent = k;
      var dd = document.createElement("dd");
      dd.textContent = fmt(sq[k]);
      dl.appendChild(dt);
      dl.appendChild(dd);
    });
    secS.appendChild(dl);
  }
  root.appendChild(secS);

  var recos = data.recommendations || [];
  var secR = document.createElement("section");
  secR.className = "card";
  secR.innerHTML = "<h2 class='section-title'>推荐结果（" + recos.length + "）</h2>";
  if (!recos.length) {
    var p0 = document.createElement("p");
    p0.className = "hint";
    p0.textContent = "本条无推荐条目";
    secR.appendChild(p0);
  } else {
    var ul = document.createElement("ul");
    ul.className = "reco-list";
    recos.forEach(function (r) {
      var li = document.createElement("li");
      li.className = "reco-item card compare-card";
      var parts = [];
      parts.push("<strong>" + escapeHtml(String(r.title || r.house_label || "房源")) + "</strong>");
      if (r.rent != null) parts.push("租金: £" + escapeHtml(String(r.rent)));
      if (r.bedrooms != null) parts.push("卧室: " + escapeHtml(String(r.bedrooms)));
      if (r.final_score != null) parts.push("评分: " + escapeHtml(String(r.final_score)));
      if (r.explain) parts.push("解释: " + escapeHtml(String(r.explain)));
      if (r.risks && r.risks.length) {
        parts.push("风险: " + escapeHtml(r.risks.join("，")));
      }
      if (r.decision) {
        parts.push(
          "结论: " +
            escapeHtml(String(r.decision)) +
            (r.decision_reason
              ? "（" + escapeHtml(String(r.decision_reason)) + "）"
              : "")
        );
      }
      li.innerHTML = parts.join("<br />");
      ul.appendChild(li);
    });
    secR.appendChild(ul);
  }
  root.appendChild(secR);

  function fmt(v) {
    if (v === null || v === undefined) return "—";
    if (typeof v === "boolean") return v ? "是" : "否";
    return String(v);
  }

  function escapeHtml(s) {
    var d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }
})();
