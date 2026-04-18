/**
 * 分析历史：按 Phase5 分桶键 analysis_history__{bucketId}（guest | userId），卡片列表 + 详情 + 删除。
 */
(function () {
  var container = document.getElementById("history-list");
  if (!container) return;

  if (
    window.RentalAIHistoryAccess &&
    typeof window.RentalAIHistoryAccess.applyBannerById === "function"
  ) {
    window.RentalAIHistoryAccess.applyBannerById("history-access-banner");
  }

  function manualHistoryKey() {
    if (window.RentalAIUserStore && window.RentalAIUserStore.getManualHistoryStorageKey) {
      return window.RentalAIUserStore.getManualHistoryStorageKey();
    }
    return "analysis_history";
  }

  /**
   * 游客历史：guest、guest:<session> 或 sanitize 后 guest_…；别再只用 === "guest"。
   * 登录用户与游客历史不合并。
   */
  function isGuestBucket(bucketId) {
    var s = String(bucketId || "").trim();
    return (
      !s ||
      s === "guest" ||
      s.indexOf("guest:") === 0 ||
      s.indexOf("guest_") === 0
    );
  }

  /**
   * 游客历史隔离兼容：
   * 现在游客桶可能为 guest:<session>，因此不能只判断 !== "guest"。
   * 只有游客作用域才执行旧键迁移。
   */
  function migrateLegacyManualIfNeeded() {
    try {
      if (
        window.RentalAIUserStore &&
        window.RentalAIUserStore.getHistoryBucketId &&
        !isGuestBucket(window.RentalAIUserStore.getHistoryBucketId())
      ) {
        return;
      }
    } catch (e) {
      return;
    }
    var newKey = manualHistoryKey();
    if (localStorage.getItem(newKey)) return;
    var legacy = localStorage.getItem("analysis_history");
    if (!legacy) return;
    try {
      localStorage.setItem(newKey, legacy);
      localStorage.removeItem("analysis_history");
    } catch (e2) {}
  }

  function loadList() {
    migrateLegacyManualIfNeeded();
    var raw = localStorage.getItem(manualHistoryKey());
    var items = [];
    try {
      items = raw ? JSON.parse(raw) : [];
    } catch (e) {
      items = [];
    }
    if (!Array.isArray(items)) items = [];
    return items;
  }

  function isHousingEntry(item) {
    return (
      item &&
      (item.mode === "housing" ||
        (item.explanations && item.explanations.items) ||
        (item.normalized_filters !== undefined && item.user_text !== undefined))
    );
  }

  function summarizeSearch(item) {
    if (isHousingEntry(item)) {
      var pq = item.parsed_query || {};
      var nf = item.normalized_filters || {};
      var loc =
        nf.location ||
        pq.location ||
        nf.area ||
        pq.area ||
        nf.postcode ||
        pq.postcode ||
        "—";
      var minP = nf.min_price != null ? nf.min_price : pq.min_price;
      var maxP = nf.max_price != null ? nf.max_price : pq.max_price;
      var budget = "—";
      if (minP != null && maxP != null) {
        budget = "£" + minP + " – £" + maxP + " /月";
      } else if (maxP != null) {
        budget = "≤ £" + maxP + " /月";
      } else if (minP != null) {
        budget = "≥ £" + minP + " /月";
      }
      var bedMin = nf.min_bedrooms != null ? nf.min_bedrooms : pq.min_bedrooms;
      var bedMax = nf.max_bedrooms != null ? nf.max_bedrooms : pq.max_bedrooms;
      var rooms = "—";
      if (bedMin != null || bedMax != null) {
        rooms =
          (bedMin != null ? bedMin : "—") +
          " – " +
          (bedMax != null ? bedMax : "—") +
          " 间";
      }
      return { location: String(loc), budget: budget, rooms: rooms };
    }
    var q = item.raw_user_query || item.user_text || "—";
    return { location: String(q), budget: "—", rooms: "—" };
  }

  function topRecoTitle(item) {
    if (isHousingEntry(item)) {
      var expl = item.explanations || {};
      var arr = Array.isArray(expl.items) ? expl.items : [];
      if (arr.length && arr[0].title) {
        return String(arr[0].title);
      }
      return "暂无推荐标题";
    }
    var recos = item.recommendations || [];
    if (recos.length && (recos[0].title || recos[0].house_label)) {
      return String(recos[0].title || recos[0].house_label);
    }
    return "暂无推荐";
  }

  function avgStarOverall(item) {
    if (!isHousingEntry(item)) return null;
    var expl = item.explanations || {};
    var arr = Array.isArray(expl.items) ? expl.items : [];
    if (!arr.length) return null;
    var sum = 0;
    var n = 0;
    for (var i = 0; i < arr.length; i++) {
      var sr = Number(arr[i].star_rating);
      if (!isNaN(sr)) {
        sum += sr;
        n += 1;
      }
    }
    if (!n) return null;
    return Math.round((sum / n) * 10) / 10;
  }

  function timeAgoZh(iso) {
    if (!iso) return "—";
    var t = new Date(iso).getTime();
    if (isNaN(t)) return String(iso);
    var sec = Math.floor((Date.now() - t) / 1000);
    if (sec < 10) return "刚刚";
    if (sec < 60) return sec + " 秒前";
    if (sec < 3600) return Math.floor(sec / 60) + " 分钟前";
    if (sec < 86400) return Math.floor(sec / 3600) + " 小时前";
    if (sec < 86400 * 7) return Math.floor(sec / 86400) + " 天前";
    try {
      return new Date(iso).toLocaleString("zh-CN", {
        month: "numeric",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch (e) {
      return String(iso);
    }
  }

  function starsRowHtml(rating) {
    var r = Number(rating);
    if (isNaN(r) || r < 1) r = 1;
    if (r > 5) r = 5;
    r = Math.round(r * 2) / 2;
    var full = Math.floor(r);
    var half = r - full >= 0.5 ? 1 : 0;
    var empty = 5 - full - half;
    var html =
      '<span class="star-rating-row history-star-row" aria-label="' +
      escapeAttr(String(r)) +
      ' 星">';
    var i;
    for (i = 0; i < full; i++) {
      html += '<span class="star-unit star-unit--full">★</span>';
    }
    if (half) {
      html += '<span class="star-unit star-unit--half" aria-hidden="true"></span>';
    }
    for (i = 0; i < empty; i++) {
      html += '<span class="star-unit star-unit--empty">☆</span>';
    }
    html +=
      '<span class="star-rating-caption">' +
      escapeHtml(String(r)) +
      " / 5</span></span>";
    return html;
  }

  function render() {
    var items = loadList();
    var ordered = items.slice().reverse();

    if (!ordered.length) {
      container.className = "history-page-grid";
      container.innerHTML =
        "<p class='hint history-empty-hint'>暂无历史记录（未登录时为 guest 桶）。</p>";
      return;
    }

    container.className = "history-page-grid";
    container.innerHTML = ordered
      .map(function (item) {
        var sum = summarizeSearch(item);
        var topT = topRecoTitle(item);
        var avg = avgStarOverall(item);
        var starBlock =
          avg != null
            ? '<div class="history-record-stars"><span class="history-record-label">整体星级</span>' +
              starsRowHtml(avg) +
              "</div>"
            : '<div class="history-record-stars history-record-stars--na"><span class="history-record-label">整体星级</span><span class="hint">—</span></div>';

        return (
          '<article class="history-record-card">' +
          '<div class="history-record-time">' +
          escapeHtml(timeAgoZh(item.saved_at)) +
          "</div>" +
          '<div class="history-record-conditions">' +
          '<div class="history-cond-row"><span class="history-cond-k">地点</span><span class="history-cond-v">' +
          escapeHtml(sum.location) +
          "</span></div>" +
          '<div class="history-cond-row"><span class="history-cond-k">预算</span><span class="history-cond-v">' +
          escapeHtml(sum.budget) +
          "</span></div>" +
          '<div class="history-cond-row"><span class="history-cond-k">房型</span><span class="history-cond-v">' +
          escapeHtml(sum.rooms) +
          "</span></div>" +
          "</div>" +
          '<div class="history-record-top">' +
          '<span class="history-record-label">Top 推荐</span>' +
          '<p class="history-record-top-title">' +
          escapeHtml(topT) +
          "</p>" +
          "</div>" +
          starBlock +
          '<div class="history-record-actions">' +
          '<button type="button" class="btn-history-primary history-detail-btn" data-id="' +
          escapeAttr(String(item.id || "")) +
          '">查看详情</button>' +
          '<button type="button" class="btn-history-danger history-delete-btn" data-id="' +
          escapeAttr(String(item.id || "")) +
          '">删除</button>' +
          "</div>" +
          "</article>"
        );
      })
      .join("");
  }

  render();

  container.addEventListener("click", function (e) {
    var t = e.target;
    if (!t || !t.getAttribute) return;
    var id = t.getAttribute("data-id");
    if (!id) return;

    if (t.classList.contains("history-delete-btn")) {
      if (!confirm("确定删除这条记录？")) return;
      migrateLegacyManualIfNeeded();
      var list = [];
      try {
        list = JSON.parse(localStorage.getItem(manualHistoryKey()) || "[]");
      } catch (err) {
        list = [];
      }
      if (!Array.isArray(list)) list = [];
      list = list.filter(function (x) {
        return !x || String(x.id) !== String(id);
      });
      try {
        localStorage.setItem(manualHistoryKey(), JSON.stringify(list));
      } catch (err2) {
        alert("删除失败");
        return;
      }
      render();
      return;
    }

    if (!t.classList.contains("history-detail-btn")) return;

    migrateLegacyManualIfNeeded();
    var rawList = localStorage.getItem(manualHistoryKey());
    var list = [];
    try {
      list = rawList ? JSON.parse(rawList) : [];
    } catch (err) {
      list = [];
    }
    if (!Array.isArray(list)) list = [];
    var found = null;
    for (var i = 0; i < list.length; i++) {
      if (String(list[i].id) === String(id)) {
        found = list[i];
        break;
      }
    }
    if (!found) {
      alert("记录不存在或已删除");
      return;
    }

    if (isHousingEntry(found)) {
      var payload = {
        success: true,
        user_text: found.user_text,
        parsed_query: found.parsed_query || {},
        normalized_filters: found.normalized_filters || {},
        market_summary: found.market_summary || {},
        market_stats: found.market_stats || {},
        top_deals: found.top_deals || {},
        explanations: found.explanations || {},
        recommendation_report: found.recommendation_report || {},
        errors: found.errors || {},
      };
      try {
        sessionStorage.setItem("ai_housing_query_last", JSON.stringify(payload));
      } catch (err) {
        alert("无法打开详情");
        return;
      }
      window.location.href = "/ai-result";
      return;
    }

    try {
      sessionStorage.setItem(
        "ai_analyze_last",
        JSON.stringify({
          success: true,
          raw_user_query: found.raw_user_query,
          structured_query: found.structured_query || {},
          recommendations: found.recommendations || [],
          summary: found.summary || {},
        })
      );
    } catch (e2) {
      try {
        sessionStorage.setItem("history_current", JSON.stringify(found));
      } catch (e3) {
        alert("无法打开详情");
        return;
      }
      window.location.href = "/history-detail";
      return;
    }
    window.location.href = "/ai-result";
  });

  function escapeHtml(s) {
    var d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
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
