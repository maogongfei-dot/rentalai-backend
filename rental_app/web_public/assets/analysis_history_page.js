/**
 * Phase 4 Round6 Step2：/analysis-history 页 — 读取 RentalAIAnalysisHistoryStore 并渲染最近摘要列表
 */
(function () {
  var S = window.RentalAIAnalysisHistoryStore;
  if (!S || typeof S.listByType !== "function") return;

  function escapeHtml(s) {
    var d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  function fmtTime(iso) {
    if (!iso) return "—";
    try {
      var d = new Date(iso);
      if (isNaN(d.getTime())) return String(iso);
      return d.toLocaleString();
    } catch (e) {
      return String(iso);
    }
  }

  function renderList(container, items, emptyHint) {
    if (!container) return;
    if (!items || !items.length) {
      container.innerHTML =
        '<p class="hint muted unified-history-empty">' + escapeHtml(emptyHint) + "</p>";
      return;
    }
    var html = '<ul class="unified-history-list">';
    for (var i = 0; i < items.length; i++) {
      var it = items[i];
      html += '<li class="unified-history-item card card-muted">';
      html += '<div class="unified-history-item-head">';
      html +=
        '<span class="unified-history-title">' + escapeHtml(it.title || "—") + "</span>";
      html +=
        '<span class="unified-history-time hint muted">' +
        escapeHtml(fmtTime(it.created_at)) +
        "</span>";
      html += "</div>";
      if (it.summary_snippet) {
        html +=
          '<p class="unified-history-snippet hint">' +
          escapeHtml(it.summary_snippet) +
          "</p>";
      }
      if (it.result_preview) {
        html +=
          '<p class="unified-history-preview">' + escapeHtml(it.result_preview) + "</p>";
      }
      html += "</li>";
    }
    html += "</ul>";
    container.innerHTML = html;
  }

  function run() {
    var propEl = document.getElementById("unified-history-property-list");
    var contractEl = document.getElementById("unified-history-contract-list");
    renderList(
      propEl,
      S.listByType("property"),
      "暂无最近房源分析记录。完成一次需求分析后，将自动出现在此。"
    );
    renderList(
      contractEl,
      S.listByType("contract"),
      "暂无最近合同分析记录。在合同分析页提交成功后，将自动出现在此。"
    );
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run);
  } else {
    run();
  }
})();
