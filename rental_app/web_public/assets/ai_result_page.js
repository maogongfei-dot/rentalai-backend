/**
 * P10-4：ai_housing_query_last（POST /api/ai/query）+ 旧版 ai_analyze_last
 */
(function () {
  var HOUSING_KEY = "ai_housing_query_last";
  var LEGACY_KEY = "ai_analyze_last";

  function favStorageKey() {
    if (window.RentalAILocalAuth && window.RentalAILocalAuth.favStorageKey) {
      return window.RentalAILocalAuth.favStorageKey();
    }
    return "fav_list";
  }

  function escapeHtml(s) {
    var d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  function fmt(v) {
    if (v === null || v === undefined) return "—";
    if (typeof v === "boolean") return v ? "是" : "否";
    if (typeof v === "object") return JSON.stringify(v);
    return String(v);
  }

  function fmtMoney(v) {
    if (v === null || v === undefined) return "—";
    var n = Number(v);
    if (isNaN(n)) return String(v);
    return "£" + n + " /月";
  }

  function safeListingUrl(u) {
    if (!u || typeof u !== "string") return "";
    u = u.trim();
    return /^https?:\/\//i.test(u) ? u : "";
  }

  function tagBadgeHtml(tag) {
    var t = String(tag || "").toLowerCase();
    var cls = "tag-badge ";
    var label;
    if (t === "excellent" || t === "good") {
      cls += "tag-badge--good";
      label = "good";
    } else if (t === "average") {
      cls += "tag-badge--average";
      label = "average";
    } else if (t === "poor") {
      cls += "tag-badge--avoid";
      label = "avoid";
    } else {
      cls += "tag-badge--neutral";
      label = t || "—";
    }
    return "<span class=\"" + cls + "\">" + escapeHtml(label) + "</span>";
  }

  function starScoreLine(score) {
    var n = Number(score);
    if (isNaN(n)) {
      return "<span class=\"deal-score-line\"><span class=\"deal-score-star\" aria-hidden=\"true\">⭐</span> <span class=\"deal-score-value\">—</span></span>";
    }
    var s = n % 1 === 0 ? String(Math.round(n)) : (Math.round(n * 10) / 10).toFixed(1);
    return (
      "<span class=\"deal-score-line\"><span class=\"deal-score-star\" aria-hidden=\"true\">⭐</span> <span class=\"deal-score-value\">" +
      escapeHtml(s) +
      "</span></span>"
    );
  }

  function decisionRowHtml(decision) {
    var d = String(decision || "").trim().toUpperCase();
    if (!d) {
      return "";
    }
    var icon;
    var rowCls;
    var label;
    if (d === "DO" || d === "RECOMMENDED") {
      icon = "✅";
      rowCls = "deal-decision-row deal-decision-row--good";
      label = "GOOD";
    } else if (d === "CAUTION") {
      icon = "⚠️";
      rowCls = "deal-decision-row deal-decision-row--caution";
      label = "CAUTION";
    } else if (d === "AVOID") {
      icon = "⚠️";
      rowCls = "deal-decision-row deal-decision-row--avoid";
      label = "AVOID";
    } else {
      icon = "⚠️";
      rowCls = "deal-decision-row deal-decision-row--caution";
      label = d;
    }
    return (
      "<div class=\"" +
      rowCls +
      "\" role=\"note\"><span class=\"deal-decision-icon\" aria-hidden=\"true\">" +
      icon +
      "</span> <span class=\"deal-decision-text\">" +
      escapeHtml(label) +
      "</span></div>"
    );
  }

  function computeFinalVerdict(rep) {
    var s =
      ((rep.summary_sentence || "") +
        " " +
        (rep.overall_recommendation || "") +
        " " +
        ((rep.readable_sections && rep.readable_sections.worth_continuing) || ""))
        .toLowerCase();
    if (/worth continuing|several strong|promising leads|justify deeper|enough promising/.test(s)) {
      return { label: "推荐", cls: "verdict-banner--positive" };
    }
    if (/several top-ranked rows still carry high|proceed carefully - many top rows|high listing risk/.test(s)) {
      return { label: "不推荐", cls: "verdict-banner--negative" };
    }
    if (/no listings in sample|inconclusive yet|expand search|sample is very small|sample exists but no top deals/.test(s)) {
      return { label: "谨慎", cls: "verdict-banner--caution" };
    }
    if (/mixed quality|moderately promising/.test(s)) {
      return { label: "谨慎", cls: "verdict-banner--caution" };
    }
    return { label: "谨慎", cls: "verdict-banner--caution" };
  }

  function verdictBannerHtml(rep) {
    var v = computeFinalVerdict(rep);
    return (
      "<div class=\"verdict-banner " +
      escapeHtml(v.cls) +
      "\" role=\"status\">" +
      "<div class=\"verdict-banner-kicker\">最终结论</div>" +
      "<div class=\"verdict-banner-text\">" +
      escapeHtml(v.label) +
      "</div>" +
      "</div>"
    );
  }

  function hasSearchableGeo(data) {
    var nf = data.normalized_filters || {};
    var pq = data.parsed_query || {};
    if (nf.postcode && String(nf.postcode).trim()) return true;
    if (nf.area && String(nf.area).trim()) return true;
    var loc = nf.location || pq.location;
    if (loc && String(loc).trim() && /[A-Za-z]/.test(String(loc))) return true;
    return false;
  }

  /* ---------- P10-4 housing ---------- */
  function renderHousing(data) {
    var housingEl = document.getElementById("housing-mode");
    var legacyEl = document.getElementById("legacy-mode");
    if (housingEl) housingEl.classList.remove("hidden");
    if (legacyEl) legacyEl.classList.add("hidden");

    var geoOk = hasSearchableGeo(data);

    var missEl = document.getElementById("housing-missing-location");
    if (missEl) {
      if (!geoOk) {
        missEl.classList.remove("hidden");
        missEl.innerHTML =
          "<p><strong>Please add a location or postcode.</strong></p>" +
          "<p class='hint'>请补充城市/地区或英国邮编后再搜索。</p>" +
          (data.message
            ? "<p class='hint'>" + escapeHtml(data.message) + "</p>"
            : "");
      } else {
        missEl.classList.add("hidden");
        missEl.innerHTML = "";
      }
    }

    var ms0 = data.market_stats || {};
    var td0 = data.top_deals || {};
    var rows0 = td0.top_deals || [];
    var emptyEl = document.getElementById("housing-empty-hint");
    if (emptyEl) {
      var noListings =
        ms0.total_listings === 0 ||
        ms0.total_listings === null ||
        ms0.total_listings === undefined;
      var noDeals = !rows0.length;
      if (geoOk && data.success !== false && (noListings || noDeals)) {
        emptyEl.classList.remove("hidden");
        emptyEl.innerHTML =
          "<p><strong>当前条件下未找到足够房源</strong></p>" +
          "<p class='hint'>建议：扩大搜索区域、放宽预算、或放宽卧室/居室条件。</p>" +
          "<p><a href='/'>返回首页重新输入</a></p>";
      } else {
        emptyEl.classList.add("hidden");
        emptyEl.innerHTML = "";
      }
    }

    var banner = document.getElementById("housing-banner");
    if (banner) {
      if (geoOk && data.message) {
        banner.textContent = data.message;
        banner.style.display = "block";
      } else {
        banner.textContent = "";
        banner.style.display = "none";
      }
    }

    var errBox = document.getElementById("housing-errors");
    if (errBox) {
      var errs = data.errors || {};
      var keys = Object.keys(errs);
      if (keys.length) {
        errBox.classList.remove("hidden");
        errBox.innerHTML =
          "<strong>部分步骤异常</strong><ul>" +
          keys
            .map(function (k) {
              return "<li>" + escapeHtml(k) + ": " + escapeHtml(errs[k]) + "</li>";
            })
            .join("") +
          "</ul>";
      } else {
        errBox.classList.add("hidden");
        errBox.innerHTML = "";
      }
    }

    var pq = data.parsed_query || {};
    var nf = data.normalized_filters || {};
    var fl = nf.filters || {};
    var minP = nf.min_price;
    var maxP = nf.max_price;
    var budgetStr = "—";
    if (minP != null && maxP != null) budgetStr = fmtMoney(minP) + " – " + fmtMoney(maxP);
    else if (maxP != null) budgetStr = "≤ " + fmtMoney(maxP);
    else if (minP != null) budgetStr = "≥ " + fmtMoney(minP);

    var qEl = document.getElementById("housing-query-summary");
    if (qEl) {
      var bedMin =
        pq.min_bedrooms != null
          ? pq.min_bedrooms
          : nf.min_bedrooms != null
            ? nf.min_bedrooms
            : null;
      var bedMax =
        pq.max_bedrooms != null
          ? pq.max_bedrooms
          : nf.max_bedrooms != null
            ? nf.max_bedrooms
            : null;
      var bedStr =
        bedMin != null || bedMax != null
          ? (bedMin != null ? bedMin : "—") + " – " + (bedMax != null ? bedMax : "—")
          : "—";
      var pmin = pq.min_price != null ? pq.min_price : nf.min_price;
      var pmax = pq.max_price != null ? pq.max_price : nf.max_price;
      var budgetParsed =
        pmin != null || pmax != null
          ? (pmin != null ? fmtMoney(pmin) : "—") + " – " + (pmax != null ? fmtMoney(pmax) : "—")
          : budgetStr;
      qEl.innerHTML =
        "<dl class='kv-list'>" +
        "<dt>原始输入</dt><dd>" +
        escapeHtml(data.user_text || pq.raw_text || "") +
        "</dd>" +
        "<dt>Location</dt><dd>" +
        escapeHtml(pq.location || nf.location || "—") +
        "</dd>" +
        "<dt>Postcode</dt><dd>" +
        escapeHtml(pq.postcode || nf.postcode || "—") +
        "</dd>" +
        "<dt>预算区间（解析）</dt><dd>" +
        escapeHtml(budgetParsed) +
        "</dd>" +
        "<dt>卧室数（解析）</dt><dd>" +
        escapeHtml(bedStr) +
        "</dd>" +
        "</dl>";
    }

    var ms = data.market_stats || {};
    var msum = data.market_summary || {};
    var mEl = document.getElementById("housing-market-summary");
    if (mEl) {
      mEl.innerHTML =
        "<dl class='kv-list'>" +
        "<dt>total_listings</dt><dd>" +
        fmt(ms.total_listings) +
        "</dd>" +
        "<dt>average_price_pcm</dt><dd>" +
        fmt(ms.average_price_pcm) +
        "</dd>" +
        "<dt>median_price_pcm</dt><dd>" +
        fmt(ms.median_price_pcm) +
        "</dd>" +
        "<dt>dominant_price_band</dt><dd>" +
        fmt(ms.dominant_price_band) +
        "</dd>" +
        "<dt>market_price_level</dt><dd>" +
        fmt(ms.market_price_level) +
        "</dd>" +
        "<dt>supply_level</dt><dd>" +
        fmt(ms.supply_level) +
        "</dd>" +
        "<dt>bedroom_focus</dt><dd>" +
        fmt(ms.bedroom_focus) +
        "</dd>" +
        "</dl>" +
        "<p class='hint small-print'>" +
        escapeHtml(msum.price_summary || "") +
        "</p>" +
        "<p class='hint small-print'>" +
        escapeHtml(msum.supply_summary || "") +
        "</p>";
    }

    var expl = data.explanations || {};
    var items = Array.isArray(expl.items) ? expl.items : [];
    var top5 = items.slice(0, 5);
    var td = data.top_deals || {};
    var meta = document.getElementById("housing-deals-meta");
    if (meta) {
      meta.textContent =
        "average_score: " +
        fmt(td.average_score) +
        " · items: " +
        (expl.count != null ? expl.count : top5.length);
    }

    var dealsEl = document.getElementById("housing-top-deals");
    if (dealsEl) {
      if (!top5.length) {
        if (!geoOk) {
          dealsEl.innerHTML =
            "<p class='hint'>请先补充 <strong>location</strong> 或 <strong>postcode</strong> 后再检索。</p>";
        } else {
          dealsEl.innerHTML =
            "<p class='hint'>暂无 Top deals。若上方已提示空结果，请放宽条件后重试。</p>";
        }
      } else {
        dealsEl.innerHTML = top5
          .map(function (it) {
            var src = it.source || "";
            var href = safeListingUrl(it.listing_url || "");
            var btn = href
              ? "<a class=\"btn-deal-view\" href=\"" +
                href.replace(/"/g, "&quot;") +
                "\" target=\"_blank\" rel=\"noopener noreferrer\">查看房源</a>"
              : "<span class=\"btn-deal-view btn-deal-view--disabled\" aria-disabled=\"true\">暂无链接</span>";
            var decHtml = decisionRowHtml(it.decision);
            return (
              "<article class=\"deal-card-modern\">" +
              "<h3 class=\"deal-card-title\">" +
              escapeHtml(it.title || "—") +
              "</h3>" +
              "<p class=\"deal-card-location\">" +
              escapeHtml(it.address || "—") +
              "</p>" +
              "<div class=\"deal-card-price\">" +
              fmtMoney(it.price_pcm) +
              "</div>" +
              "<div class=\"deal-card-score-row\">" +
              starScoreLine(it.deal_score) +
              "</div>" +
              "<div class=\"deal-card-tags\">" +
              tagBadgeHtml(it.deal_tag) +
              "</div>" +
              decHtml +
              "<div class=\"deal-card-meta\">" +
              "<span class=\"deal-card-source\">" +
              escapeHtml(src) +
              "</span>" +
              "</div>" +
              "<div class=\"deal-card-actions\">" +
              btn +
              "</div>" +
              "</article>"
            );
          })
          .join("");
      }
    }

    var rep = data.recommendation_report || {};
    var rEl = document.getElementById("housing-report");
    if (rEl) {
      function ul(arr) {
        if (!Array.isArray(arr) || !arr.length) return "<p class='hint'>—</p>";
        return "<ul class='bullet-list'>" + arr.map(function (x) { return "<li>" + escapeHtml(x) + "</li>"; }).join("") + "</ul>";
      }
      function section(title, bodyHtml) {
        return (
          "<section class='report-block card-inner'>" +
          "<h3 class='subsection-title'>" +
          escapeHtml(title) +
          "</h3>" +
          bodyHtml +
          "</section>"
        );
      }
      var rs = rep.readable_sections || {};
      var banner = verdictBannerHtml(rep);
      if (rs.market_situation != null && String(rs.market_situation).trim() !== "") {
        rEl.innerHTML =
          banner +
          section("市场情况", "<p>" + escapeHtml(rs.market_situation || "—") + "</p>") +
          section("是否值得继续看", "<p>" + escapeHtml(rs.worth_continuing || "—") + "</p>") +
          section("最值得关注的机会", ul(rs.top_opportunities || [])) +
          section("主要风险", ul(rs.main_risks || [])) +
          section("下一步建议", ul(rs.next_steps || [])) +
          "<p class='hint muted small-print report-summary-line'>" +
          escapeHtml(rep.summary_sentence || "") +
          "</p>";
      } else {
        rEl.innerHTML =
          banner +
          section("市场情况", "<p>" + escapeHtml(rep.market_positioning || "—") + "</p>") +
          section("是否值得继续看", "<p>" + escapeHtml(rep.overall_recommendation || "—") + "</p>") +
          section("最值得关注的机会", ul(rep.best_opportunities)) +
          section("主要风险", ul(rep.main_risks)) +
          section("下一步建议", ul(rep.what_to_do_next)) +
          "<p class='hint muted small-print report-summary-line'>" +
          escapeHtml(rep.summary_sentence || "—") +
          "</p>";
      }
    }
  }

  /* ---------- Legacy ai-analyze ---------- */
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

  function renderLegacy(data) {
    var housingEl = document.getElementById("housing-mode");
    var legacyEl = document.getElementById("legacy-mode");
    if (housingEl) housingEl.classList.add("hidden");
    if (legacyEl) legacyEl.classList.remove("hidden");

    var rawEl = document.getElementById("raw-display");
    var dl = document.getElementById("structured-dl");
    var recoList = document.getElementById("reco-list");
    var recoEmpty = document.getElementById("reco-empty");
    var summaryLine = document.getElementById("summary-line");

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
      dl.innerHTML = "";
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
    if (recoList) recoList.innerHTML = "";

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
  }

  /* ---------- Load ---------- */
  var rawH = sessionStorage.getItem(HOUSING_KEY);
  var dataH = null;
  try {
    dataH = rawH ? JSON.parse(rawH) : null;
  } catch (e) {
    dataH = null;
  }

  if (dataH && dataH.success === false) {
    var housingEl0 = document.getElementById("housing-mode");
    var legacyEl0 = document.getElementById("legacy-mode");
    if (housingEl0) housingEl0.classList.remove("hidden");
    if (legacyEl0) legacyEl0.classList.add("hidden");
    var errBox0 = document.getElementById("housing-errors");
    if (errBox0) {
      errBox0.classList.remove("hidden");
      errBox0.innerHTML =
        "<strong>分析未完成</strong><p>" +
        escapeHtml(dataH.message || dataH.error || "请返回首页重试") +
        "</p><p><a href='/'>返回首页</a></p>";
    }
    var miss0 = document.getElementById("housing-missing-location");
    if (miss0) miss0.classList.add("hidden");
    var empty0 = document.getElementById("housing-empty-hint");
    if (empty0) empty0.classList.add("hidden");
  } else if (
    dataH &&
    dataH.success !== false &&
    typeof dataH.user_text === "string" &&
    dataH.normalized_filters !== undefined
  ) {
    renderHousing(dataH);
  } else {
    var rawL = sessionStorage.getItem(LEGACY_KEY);
    var dataL = null;
    try {
      dataL = rawL ? JSON.parse(rawL) : null;
    } catch (e2) {
      dataL = null;
    }
    renderLegacy(dataL);
  }

  /* ---------- Save ---------- */
  (function registerAnalysisHistorySave() {
    var saveBtn = document.querySelector(".save-analysis-btn");
    if (!saveBtn) return;
    saveBtn.addEventListener("click", function () {
      var rawSave = sessionStorage.getItem(HOUSING_KEY);
      var mode = "housing";
      if (!rawSave) {
        rawSave = sessionStorage.getItem(LEGACY_KEY);
        mode = "legacy";
      }
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
      if (!parsed || parsed.success === false) {
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
        mode: mode,
      };
      if (mode === "housing") {
        entry.user_text = parsed.user_text;
        entry.parsed_query = parsed.parsed_query || {};
        entry.normalized_filters = parsed.normalized_filters || {};
        entry.market_summary = parsed.market_summary || {};
        entry.market_stats = parsed.market_stats || {};
        entry.top_deals = parsed.top_deals || {};
        entry.explanations = parsed.explanations || {};
        entry.recommendation_report = parsed.recommendation_report || {};
        entry.errors = parsed.errors || {};
      } else {
        entry.raw_user_query = parsed.raw_user_query;
        entry.structured_query = parsed.structured_query || {};
        entry.recommendations = parsed.recommendations || [];
      }
      list.push(entry);
      localStorage.setItem("analysis_history", JSON.stringify(list));
      alert("已保存到历史记录");
    });
  })();
})();
