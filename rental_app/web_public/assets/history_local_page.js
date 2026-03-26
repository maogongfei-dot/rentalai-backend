/**
 * History v1：从 localStorage 读取 analysis_history，倒序渲染列表。
 */
(function () {
  var container = document.getElementById("history-list");
  if (!container) return;

  // 仅展示当前登录用户的记录（user_id 与 current_user 一致）
  var uid =
    window.RentalAILocalAuth && window.RentalAILocalAuth.getUser
      ? (window.RentalAILocalAuth.getUser() || {}).user_id
      : null;

  var raw = localStorage.getItem("analysis_history");
  var items = [];
  try {
    items = raw ? JSON.parse(raw) : [];
  } catch (e) {
    items = [];
  }
  if (!Array.isArray(items)) items = [];
  if (uid) {
    items = items.filter(function (x) {
      return x && x.user_id === uid;
    });
  } else {
    items = [];
  }

  // 最新在前
  var ordered = items.slice().reverse();

  if (!ordered.length) {
    container.innerHTML = "<p class='hint'>暂无历史记录</p>";
    return;
  }

  ordered.forEach(function (item) {
    var card = document.createElement("div");
    card.className = "history-card card";
    var recos = item.recommendations || [];
    var n = recos.length;
    var when = item.saved_at || "—";
    var query = item.raw_user_query || "—";
    card.innerHTML =
      "<p><strong>保存时间</strong>：" +
      escapeHtml(String(when)) +
      "</p>" +
      "<p><strong>需求</strong>：" +
      escapeHtml(String(query)) +
      "</p>" +
      "<p><strong>推荐数量</strong>：" +
      n +
      "</p>" +
      "<div class='history-actions'>" +
      "<button type='button' class='history-detail-btn' data-id='" +
      escapeAttr(item.id || "") +
      "'>查看详情</button>" +
      "</div>";
    container.appendChild(card);
  });

  container.addEventListener("click", function (e) {
    if (!e.target || !e.target.classList.contains("history-detail-btn")) return;
    var id = e.target.getAttribute("data-id");
    if (!id) return;
    var rawList = localStorage.getItem("analysis_history");
    var list = [];
    try {
      list = rawList ? JSON.parse(rawList) : [];
    } catch (err) {
      list = [];
    }
    if (!Array.isArray(list)) list = [];
    var found = null;
    for (var i = 0; i < list.length; i++) {
      if (
        String(list[i].id) === String(id) &&
        uid &&
        list[i].user_id === uid
      ) {
        found = list[i];
        break;
      }
    }
    if (!found) {
      alert("记录不存在或已损坏");
      return;
    }
    try {
      sessionStorage.setItem("history_current", JSON.stringify(found));
    } catch (err) {
      alert("无法打开详情");
      return;
    }
    window.location.href = "/history-detail";
  });

  function escapeHtml(s) {
    var d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  function escapeAttr(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }
})();
