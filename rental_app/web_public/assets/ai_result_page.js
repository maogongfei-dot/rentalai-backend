/**
 * Phase1 AI 结果页：从 sessionStorage 读取 /api/ai-analyze 响应并渲染
 */
(function () {
  function favStorageKey() {
    if (window.RentalAILocalAuth && window.RentalAILocalAuth.favStorageKey) {
      return window.RentalAILocalAuth.favStorageKey();
    }
    return "fav_list";
  }

  var KEY = "ai_analyze_last";
  var LABELS = {
    raw_user_query: "原始输入",
    city: "城市",
    area: "区域",
    postcode: "邮编",
    budget_max: "预算上限",
    budget_min: "预算下限",
    bedrooms: "卧室数",
    bills_included: "是否包 bill",
    furnished: "家具",
    commute_preference: "通勤偏好",
    near_station: "近车站",
    couple_friendly: "适合情侣",
    safety_priority: "安全/安静优先",
    property_type: "房型",
    notes: "备注",
  };

  function fmt(v) {
    if (v === null || v === undefined) return "—";
    if (typeof v === "boolean") return v ? "是" : "否";
    return String(v);
  }

  var raw = sessionStorage.getItem(KEY);
  var data;
  try {
    data = raw ? JSON.parse(raw) : null;
  } catch (e) {
    data = null;
  }

  var rawEl = document.getElementById("raw-display");
  var dl = document.getElementById("structured-dl");
  var recoList = document.getElementById("reco-list");
  var recoEmpty = document.getElementById("reco-empty");
  var summaryLine = document.getElementById("summary-line");

  // History v1：保存本次分析 → analysis_history，并写入 user_id / display_name（尽早注册点击）
  (function registerAnalysisHistorySave() {
    var saveBtn = document.querySelector(".save-analysis-btn");
    if (!saveBtn) return;
    saveBtn.addEventListener("click", function () {
      var rawSave = sessionStorage.getItem(KEY);
      if (!rawSave) {
        alert("暂无分析数据");
        return;
      }
      var parsed;
      try {
        parsed = JSON.parse(rawSave);
      } catch (err) {
        alert("暂无分析数据");
        return;
      }
      if (!parsed || !parsed.success) {
        alert("暂无分析数据");
        return;
      }
      var cu =
        window.RentalAILocalAuth && window.RentalAILocalAuth.getUser
          ? window.RentalAILocalAuth.getUser()
          : null;
      if (!cu || !cu.user_id) {
        alert("请先登录");
        return;
      }
      var list = [];
      try {
        list = JSON.parse(localStorage.getItem("analysis_history") || "[]");
      } catch (e) {
        list = [];
      }
      if (!Array.isArray(list)) list = [];
      var entry = {
        id: String(Date.now()),
        user_id: cu.user_id,
        display_name: cu.display_name || "",
        saved_at: new Date().toISOString(),
        raw_user_query: parsed.raw_user_query,
        structured_query: parsed.structured_query || {},
        recommendations: parsed.recommendations || [],
      };
      list.push(entry);
      localStorage.setItem("analysis_history", JSON.stringify(list));
      alert("已保存到历史记录");
    });
  })();

  if (!data || !data.success) {
    if (rawEl) rawEl.textContent = "未找到分析结果，请从首页重新提交。";
    if (recoEmpty) {
      recoEmpty.classList.remove("hidden");
      recoEmpty.textContent = "没有可展示的数据，请返回首页重试。";
    }
    return;
  }

  if (rawEl) rawEl.textContent = data.raw_user_query || "—";

  var sq = data.structured_query || {};
  if (dl) {
    Object.keys(LABELS).forEach(function (k) {
      if (k === "raw_user_query") return;
      var dt = document.createElement("dt");
      dt.textContent = LABELS[k];
      var dd = document.createElement("dd");
      dd.textContent = fmt(sq[k]);
      dl.appendChild(dt);
      dl.appendChild(dd);
    });
  }

  var recos = data.recommendations || [];
  var sum = data.summary || {};
  if (summaryLine) {
    summaryLine.textContent =
      "候选 " +
      (sum.total_candidates != null ? sum.total_candidates : "—") +
      " 套 · 展示 Top " +
      (sum.top_count != null ? sum.top_count : recos.length);
  }

  if (!recos.length) {
    if (recoEmpty) recoEmpty.classList.remove("hidden");
    return;
  }
  if (recoEmpty) recoEmpty.classList.add("hidden");

  recos.forEach(function (r) {
    var favs = JSON.parse(localStorage.getItem(favStorageKey()) || "[]");
    var isFav = favs.includes(String(r.listing_id || r.rank));
    var btnText = isFav ? "✅ 已收藏" : "⭐ 收藏";
    var li = document.createElement("li");
    li.className = "reco-item card";
    var title = r.title || r.house_label || "房源";
    var rent = r.rent != null ? "£" + r.rent + " /月" : "租金 —";
    var beds = r.bedrooms != null ? r.bedrooms + " 卧" : "卧室 —";
    var loc = [r.postcode, r.area].filter(Boolean).join(" · ") || "地区 —";
    var score =
      r.final_score != null ? "总分 " + Number(r.final_score).toFixed(1) : "";
    var explainHtml = "";
    if (r.explain) {
      explainHtml += "<div class='explain-main'>" + escapeHtml(r.explain) + "</div>";
    }
    if (r.why_good && r.why_good.length) {
      explainHtml += "<div class='explain-good'>👍 " + r.why_good.join("，") + "</div>";
    }
    if (r.why_not && r.why_not.length) {
      explainHtml += "<div class='explain-bad'>❌ " + r.why_not.join("，") + "</div>";
    }
    if (r.risks && r.risks.length) {
      explainHtml += "<div class='explain-risk'>⚠️ " + r.risks.join("，") + "</div>";
    }
    if (r.decision) {
      var label = "";
      if (r.decision === "RECOMMENDED") label = "✅ 建议租";
      else if (r.decision === "CAUTION") label = "⚠️ 谨慎";
      else label = "❌ 不建议";

      explainHtml +=
        "<div class='decision'>" +
        label +
        "：" +
        escapeHtml(r.decision_reason || "") +
        "</div>";
    }
    li.innerHTML =
      "<strong>" +
      escapeHtml(title) +
      "</strong><br />" +
      escapeHtml(rent) +
      " · " +
      escapeHtml(beds) +
      " · " +
      escapeHtml(loc) +
      (score ? "<br />" + escapeHtml(score) : "") +
      explainHtml +
      "<br/><button class='fav-btn' data-id='" +
      (r.listing_id || r.rank) +
      "'>" +
      btnText +
      "</button>";
    if (r.source_url) {
      var a = document.createElement("a");
      a.href = r.source_url;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      a.textContent = "查看链接";
      li.appendChild(document.createElement("br"));
      li.appendChild(a);
    }
    recoList.appendChild(li);
  });

  document.addEventListener("click", function (e) {
    if (e.target && e.target.classList.contains("fav-btn")) {
      var id = e.target.getAttribute("data-id");

      var favs = JSON.parse(localStorage.getItem(favStorageKey()) || "[]");

      if (!favs.includes(id)) {
        favs.push(id);
        localStorage.setItem(favStorageKey(), JSON.stringify(favs));
        e.target.innerText = "✅ 已收藏";
      }
    }
  });

  function escapeHtml(s) {
    var d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }
})();
