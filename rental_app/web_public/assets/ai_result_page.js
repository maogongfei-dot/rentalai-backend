/**
 * RentAI「需求解析结果」页（/ai_result.html）主结果渲染脚本。
 *
 * 主结果展示链路（当前产品）：上游在完成主分析请求后，将 JSON 写入 sessionStorage，
 * 本脚本在页面加载时读取并渲染；不负责发起 API 或改写响应结构。
 *
 * 关联：P10-4（key：ai_housing_query_last，对应 POST /api/ai/query）；
 * 兼容旧版 key：ai_analyze_last（/api/ai-analyze 形态）。
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

  function escapeAttr(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  /** Phase 6：persistAnalysisResult 返回的轻量提示（云端已同步 / 回退本机 / 访客本机）。 */
  function setPersistHintBar(elId, msg, variant) {
    var el = document.getElementById(elId);
    if (!el) return;
    el.classList.remove("save-banner-ok", "save-banner-warn", "save-banner-local", "hidden");
    if (!msg) {
      el.classList.add("hidden");
      el.textContent = "";
      return;
    }
    el.textContent = msg;
    if (variant === "warn") el.classList.add("save-banner-warn");
    else if (variant === "local") el.classList.add("save-banner-local");
    else el.classList.add("save-banner-ok");
  }

  function persistHintVariant(pr) {
    if (!pr || !pr.hint) return null;
    if (pr.hintIsLocal) return "local";
    if (pr.fallbackLocal) return "warn";
    return "ok";
  }

  var DEAL_CARD_PLACEHOLDER_SVG =
    "data:image/svg+xml," +
    encodeURIComponent(
      '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="400" viewBox="0 0 640 400"><rect fill="#f1f5f9" width="640" height="400"/><path fill="#cbd5e1" d="M280 140h80v80h-80z"/><text x="320" y="280" text-anchor="middle" fill="#94a3b8" font-family="system-ui,sans-serif" font-size="15">暂无图片</text></svg>'
    );

  function dealCardMediaHtml(it) {
    var href = safeListingUrl(it.listing_url || "");
    var raw = it.image_url != null ? String(it.image_url).trim() : "";
    var validImg = /^https?:\/\//i.test(raw);
    var src = validImg ? raw : DEAL_CARD_PLACEHOLDER_SVG;
    var img =
      "<img class=\"deal-card-media-img\" src=\"" +
      escapeAttr(src) +
      "\" alt=\"\" loading=\"lazy\" decoding=\"async\" />";
    if (href) {
      return (
        "<a class=\"deal-card-media deal-card-media--link\" href=\"" +
        escapeAttr(href) +
        "\" target=\"_blank\" rel=\"noopener noreferrer\" title=\"打开原房源\">" +
        img +
        "</a>"
      );
    }
    return "<div class=\"deal-card-media deal-card-media--static\">" + img + "</div>";
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

  function fmtBedrooms(b) {
    if (b === null || b === undefined || b === "") {
      return "—";
    }
    return String(b) + " 间";
  }

  function starsHalfHtml(rating) {
    var r = Number(rating);
    if (isNaN(r) || r < 1) {
      r = 1;
    }
    if (r > 5) {
      r = 5;
    }
    r = Math.round(r * 2) / 2;
    var full = Math.floor(r);
    var half = r - full >= 0.5 ? 1 : 0;
    var empty = 5 - full - half;
    var html =
      "<div class=\"star-rating-row\" aria-label=\"" +
      escapeHtml(String(r)) +
      " 星，满分 5 星\">";
    var i;
    for (i = 0; i < full; i++) {
      html += "<span class=\"star-unit star-unit--full\">★</span>";
    }
    if (half) {
      html +=
        "<span class=\"star-unit star-unit--half\" title=\"半星\" aria-hidden=\"true\"></span>";
    }
    for (i = 0; i < empty; i++) {
      html += "<span class=\"star-unit star-unit--empty\">☆</span>";
    }
    html +=
      "<span class=\"star-rating-caption\">" +
      escapeHtml(String(r)) +
      " / 5 星</span></div>";
    return html;
  }

  function starReasonsHtml(reasons) {
    if (!Array.isArray(reasons) || !reasons.length) {
      return "<p class=\"deal-card-whisper\">暂无说明。</p>";
    }
    return (
      "<ul class=\"reasons-list\">" +
      reasons
        .slice(0, 3)
        .map(function (line) {
          return "<li>" + escapeHtml(line) + "</li>";
        })
        .join("") +
      "</ul>"
    );
  }

  function verdictPickBlock(label, pick) {
    if (!pick || !pick.title) {
      return (
        "<div class=\"verdict-pick\">" +
        "<div class=\"verdict-pick-label\">" +
        escapeHtml(label) +
        "</div>" +
        "<p class=\"verdict-pick-body hint\">暂无对应候选，可先完成一次有结果的搜索再回来看这里。</p>" +
        "</div>"
      );
    }
    return (
      "<div class=\"verdict-pick\">" +
      "<div class=\"verdict-pick-label\">" +
      escapeHtml(label) +
      "</div>" +
      "<p class=\"verdict-pick-title\"><strong>" +
      escapeHtml(pick.title) +
      "</strong></p>" +
      "<p class=\"verdict-pick-body\">" +
      escapeHtml(pick.line || "") +
      "</p>" +
      "</div>"
    );
  }

  /** 综合结论区 HTML：star_final_verdict（与 #housing-star-verdict 对应）。 */
  function renderStarFinalVerdictHtml(v) {
    if (!v || typeof v !== "object") {
      return "<p class=\"hint\">暂无结论。</p>";
    }
    return (
      "<div class=\"star-final-verdict\">" +
      verdictPickBlock("最推荐的一套（星数高、租价也相对划算）", v.best_overall) +
      verdictPickBlock("价格最友好的一套", v.best_for_price) +
      verdictPickBlock("更稳妥的一套（资料更齐、更让人放心）", v.best_for_environment_safety) +
      "<div class=\"verdict-overall\">" +
      "<div class=\"verdict-pick-label\">一句话：还要不要继续看下去？</div>" +
      "<p class=\"verdict-overall-text\">" +
      escapeHtml(v.overall_advice || "—") +
      "</p>" +
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

  /* ---------- P10-4 housing：当前主结果渲染（POST /api/ai/query 负载） ---------- */

  /**
   * Future expansion（结果层扩展位，产品规划说明）
   *
   * 未来可在本结果层承接 ShortRentAI 等独立结果块，与现有 housing 区块并列渲染；
   * 可扩展维度包括但不限于：房东信息、房屋质量、信任评分、维修频率、人工核实标签；
   * 可扩展合同风险摘要，并与平台信用信息联动展示。
   * 上述能力优先在本页结果层增量承接，而非另起完全独立的结果页，以保持用户动线一致。
   */

  /** 将主分析 API 返回的 housing 负载渲染至 #housing-mode 各区块。 */
  function renderHousing(data) {
    var housingEl = document.getElementById("housing-mode");
    var legacyEl = document.getElementById("legacy-mode");
    if (housingEl) housingEl.classList.remove("hidden");
    if (legacyEl) legacyEl.classList.add("hidden");

    var geoOk = hasSearchableGeo(data);

    /* 地理/检索前置条件与空结果：异常提示与空状态（含部分风险提示语义）。 */
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

    /* 风险提示：pipeline 分步骤异常（errors 键值列表）。 */
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

    /* 需求解析摘要：用户输入与规范化条件（解释说明 · 查询侧）。 */
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
      var pf = pq.flags && typeof pq.flags === "object" ? pq.flags : {};
      var prefParts = [];
      if (pf.cheap_preference || fl.cheap_preference) prefParts.push("偏便宜");
      if (pf.safety_preference || fl.safety_preference) prefParts.push("安全稳妥");
      if (pf.commute_preference || fl.commute_preference) prefParts.push("通勤");
      if (pf.lifestyle_preference || fl.lifestyle_preference) prefParts.push("生活便利");
      var prefStr = prefParts.length ? prefParts.join("、") : "—";
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
        "<dt>偏好（解析）</dt><dd>" +
        escapeHtml(prefStr) +
        "</dd>" +
        "</dl>";
    }

    /* 市场统计与市场摘要：解释说明 · 数据侧。 */
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

    /* 核心推荐结果：选房推荐（星级房源卡片 + 单行建议，属主结论/推荐展示主区）。 */
    var expl = data.explanations || {};
    var items = Array.isArray(expl.items) ? expl.items : [];
    var top5 = items.slice(0, 5);
    var meta = document.getElementById("housing-deals-meta");
    if (meta) {
      meta.textContent =
        "以下为结合你本次搜索条件的选房建议，星级表示「有多值得优先看」，5 星最高；先看结论再看细节即可。";
    }

    var dealsEl = document.getElementById("housing-top-deals");
    if (dealsEl) {
      if (!top5.length) {
        if (!geoOk) {
          dealsEl.innerHTML =
            "<p class='hint'>请先补充 <strong>location</strong> 或 <strong>postcode</strong> 后再检索。</p>";
        } else {
          dealsEl.innerHTML =
            "<p class='hint'>暂无推荐房源。若上方已提示空结果，请放宽条件后重试。</p>";
        }
      } else {
        dealsEl.innerHTML = top5
          .map(function (it) {
            /* 建议动作：每套房源 deal-card-tip（one_line_suggestion）。 */
            var href = safeListingUrl(it.listing_url || "");
            var btn = href
              ? "<a class=\"btn-deal-view\" href=\"" +
                href.replace(/"/g, "&quot;") +
                "\" target=\"_blank\" rel=\"noopener noreferrer\">查看房源</a>"
              : "<span class=\"btn-deal-view btn-deal-view--disabled\" aria-disabled=\"true\">暂无链接</span>";
            return (
              "<article class=\"deal-card-modern deal-card-star\">" +
              dealCardMediaHtml(it) +
              "<h3 class=\"deal-card-title\">" +
              escapeHtml(it.title || "—") +
              "</h3>" +
              "<p class=\"deal-card-location\">" +
              escapeHtml(it.address || "—") +
              "</p>" +
              "<div class=\"deal-card-price\">" +
              fmtMoney(it.price_pcm) +
              "</div>" +
              "<p class=\"deal-card-beds\">卧室：" +
              escapeHtml(fmtBedrooms(it.bedrooms)) +
              "</p>" +
              "<div class=\"deal-card-stars\">" +
              starsHalfHtml(it.star_rating) +
              "</div>" +
              "<div class=\"deal-card-why-title\">为什么是这个星级</div>" +
              starReasonsHtml(it.star_reasons) +
              "<div class=\"deal-card-tip\">" +
              "<span class=\"deal-card-tip-label\">建议</span>" +
              "<span class=\"deal-card-tip-text\">" +
              escapeHtml(it.one_line_suggestion || "—") +
              "</span></div>" +
              "<div class=\"deal-card-actions\">" +
              btn +
              "</div>" +
              "</article>"
            );
          })
          .join("");
      }
    }

    /* 核心结论：综合结论（星标终局 verdict，含「最推荐/价优/稳妥」与总体建议）。 */
    var rep = data.recommendation_report || {};
    var vEl = document.getElementById("housing-star-verdict");
    if (vEl) {
      vEl.innerHTML = renderStarFinalVerdictHtml(rep.star_final_verdict);
    }

    /* 解释说明：市场印象（叙事摘要 market_snapshot_zh）。 */
    var rEl = document.getElementById("housing-report");
    if (rEl) {
      var snap = rep.market_snapshot_zh;
      if (snap && String(snap).trim()) {
        rEl.innerHTML =
          "<div class=\"market-snapshot-narrative\"><p>" +
          escapeHtml(String(snap).trim()) +
          "</p></div>";
      } else {
        rEl.innerHTML = "<p class=\"hint\">暂无市场摘要。</p>";
      }
    }

    /* 历史记录写入后的展示回流：持久化结果提示条（云端同步 / 本机回退等）。 */
    try {
      if (
        window.RentalAIAnalysisHistoryPersist &&
        typeof window.RentalAIAnalysisHistoryPersist.persistAnalysisResult === "function"
      ) {
        var prH = window.RentalAIAnalysisHistoryPersist.persistAnalysisResult({
          kind: "housing",
          data: data,
        });
        if (prH && prH.hint) {
          setPersistHintBar("housing-history-hint", prH.hint, persistHintVariant(prH));
        } else {
          setPersistHintBar("housing-history-hint", null, null);
        }
      } else if (
        window.RentalAIAnalysisHistoryStore &&
        typeof window.RentalAIAnalysisHistoryStore.pushPropertyFromHousingData === "function"
      ) {
        window.RentalAIAnalysisHistoryStore.pushPropertyFromHousingData(data);
        setPersistHintBar("housing-history-hint", null, null);
      }
    } catch (eHist) {}
  }

  /* ---------- Legacy：旧版 /api/ai-analyze 形态；辅助兼容，非当前主结果渲染主线 ---------- */
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

  /** 旧版分析负载渲染：structured_query + recommendations 列表（非 POST /api/ai/query 主链路）。 */
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
      try {
        if (
          window.RentalAIAnalysisHistoryPersist &&
          typeof window.RentalAIAnalysisHistoryPersist.persistAnalysisResult === "function"
        ) {
          var prL0 = window.RentalAIAnalysisHistoryPersist.persistAnalysisResult({
            kind: "legacy",
            data: data,
          });
          if (prL0 && prL0.hint) {
            setPersistHintBar("legacy-history-hint", prL0.hint, persistHintVariant(prL0));
          } else {
            setPersistHintBar("legacy-history-hint", null, null);
          }
        } else if (
          window.RentalAIAnalysisHistoryStore &&
          typeof window.RentalAIAnalysisHistoryStore.pushPropertyFromLegacyData === "function"
        ) {
          window.RentalAIAnalysisHistoryStore.pushPropertyFromLegacyData(data);
          setPersistHintBar("legacy-history-hint", null, null);
        }
      } catch (eHistL) {}
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
      /* 旧版推荐卡片：解释说明 / 风险提示 / 决策标签（非 housing 主链路）。 */
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

    try {
      if (
        window.RentalAIAnalysisHistoryPersist &&
        typeof window.RentalAIAnalysisHistoryPersist.persistAnalysisResult === "function"
      ) {
        var prL = window.RentalAIAnalysisHistoryPersist.persistAnalysisResult({
          kind: "legacy",
          data: data,
        });
        if (prL && prL.hint) {
          setPersistHintBar("legacy-history-hint", prL.hint, persistHintVariant(prL));
        } else {
          setPersistHintBar("legacy-history-hint", null, null);
        }
      } else if (
        window.RentalAIAnalysisHistoryStore &&
        typeof window.RentalAIAnalysisHistoryStore.pushPropertyFromLegacyData === "function"
      ) {
        window.RentalAIAnalysisHistoryStore.pushPropertyFromLegacyData(data);
        setPersistHintBar("legacy-history-hint", null, null);
      }
    } catch (eHistL2) {}
  }

  /* ---------- Load：结果数据进入本页（sessionStorage → 渲染） ---------- */

  /*
   * 此处接收当前主分析 API 返回结果：上游已将 POST /api/ai/query 的响应 JSON 存入
   * sessionStorage（key：ai_housing_query_last）。此为 RentAI 主结果展示链路的一部分
   * （结果页消费侧）；本脚本仅读取并渲染，不修改接口契约。
   */
  var rawH = sessionStorage.getItem(HOUSING_KEY);
  var dataH = null;
  try {
    dataH = rawH ? JSON.parse(rawH) : null;
  } catch (e) {
    dataH = null;
  }

  /* 主链路失败态：主分析未成功时的结果区展示（仍属 housing 容器内）。 */
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
    /* 无主分析负载时回退：读取旧版 key（非当前主结果主线）。 */
    var rawL = sessionStorage.getItem(LEGACY_KEY);
    var dataL = null;
    try {
      dataL = rawL ? JSON.parse(rawL) : null;
    } catch (e2) {
      dataL = null;
    }
    renderLegacy(dataL);
  }

  /* ---------- Save：用户手动「保存本次分析」至本机历史（辅助能力，非 API 结果解析） ---------- */
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
      function migrateLegacyManualIfNeeded() {
        try {
          if (
            window.RentalAIUserStore &&
            window.RentalAIUserStore.getHistoryBucketId &&
            !isGuestBucket(window.RentalAIUserStore.getHistoryBucketId())
          ) {
            return;
          }
        } catch (e0) {}
        var nk = manualHistoryKey();
        if (localStorage.getItem(nk)) return;
        var legacy = localStorage.getItem("analysis_history");
        if (!legacy) return;
        try {
          localStorage.setItem(nk, legacy);
          localStorage.removeItem("analysis_history");
        } catch (e1) {}
      }
      var cu =
        window.RentalAILocalAuth && window.RentalAILocalAuth.getUser
          ? window.RentalAILocalAuth.getUser()
          : null;
      migrateLegacyManualIfNeeded();
      var list = [];
      try {
        list = JSON.parse(localStorage.getItem(manualHistoryKey()) || "[]");
      } catch (e) {
        list = [];
      }
      if (!Array.isArray(list)) list = [];
      var entry = {
        id: String(Date.now()),
        user_id: cu && cu.user_id ? cu.user_id : "guest",
        display_name: (cu && cu.display_name) || "",
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
      localStorage.setItem(manualHistoryKey(), JSON.stringify(list));
      alert("已保存到历史记录（当前分桶）");
    });
  })();
})();
