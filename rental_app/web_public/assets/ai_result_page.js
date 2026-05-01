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
  /* 同页加载 server_favorites_api.js（仅两文件改动、不增 HTML 时）；失败则收藏走降级逻辑。 */
  try {
    if (typeof window.RentalAIServerFavoritesApi === "undefined") {
      var xhr = new XMLHttpRequest();
      xhr.open("GET", "/assets/server_favorites_api.js", false);
      xhr.send(null);
      if (xhr.status === 200 && xhr.responseText) {
        (0, Function)(xhr.responseText)();
      }
    }
  } catch (eFavLoad) {}

  var HOUSING_KEY = "ai_housing_query_last";
  var LEGACY_KEY = "ai_analyze_last";
  var ANALYZE_RESULT_KEY = "rentalai_result";
  var DIRECT_SESSION_KEY = "rentalai_direct_analyze_result_v1";
  var DIRECT_LOCAL_KEY = "rentalai_latest_result_v1";

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

  function escapeHtmlMultiline(s) {
    return String(s == null ? "" : s)
      .split(/\r?\n/)
      .map(function (line) {
        return escapeHtml(line);
      })
      .join("<br />");
  }

  var rentalaiToastTimer = null;
  function showRentalaiToast(message) {
    var t = document.getElementById("rentalai-save-toast");
    if (!t) return;
    t.textContent = message == null ? "" : String(message);
    t.classList.remove("hidden");
    if (rentalaiToastTimer) clearTimeout(rentalaiToastTimer);
    rentalaiToastTimer = setTimeout(function () {
      t.classList.add("hidden");
      rentalaiToastTimer = null;
    }, 3200);
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
    if (typeof v === "object") return "—";
    return String(v);
  }

  function firstNonEmpty() {
    var i;
    for (i = 0; i < arguments.length; i++) {
      var val = arguments[i];
      if (val === null || val === undefined) continue;
      if (Array.isArray(val) && val.length === 0) continue;
      if (typeof val === "string" && !val.trim()) continue;
      return val;
    }
    return null;
  }

  function toDisplayText(v) {
    if (v === null || v === undefined) return "No data available yet.";
    if (Array.isArray(v)) {
      if (!v.length) return "No data available yet.";
      return v
        .map(function (it) {
          return String(it == null ? "" : it).trim();
        })
        .filter(Boolean)
        .join(" | ") || "No data available yet.";
    }
    if (typeof v === "object") {
      return "No data available yet.";
    }
    var s = String(v).trim();
    return s || "No data available yet.";
  }

  /**
   * Phase10 Step1-3：从 object 中尽量提取可读文本（不输出 JSON / [object Object]）。
   */
  function extractScalarFromObject(o, depth) {
    depth = depth || 0;
    if (depth > 5) return null;
    if (!o || typeof o !== "object" || Array.isArray(o)) return null;
    var preferKeys = ["summary", "message", "text", "value"];
    var i;
    for (i = 0; i < preferKeys.length; i++) {
      var key = preferKeys[i];
      if (!Object.prototype.hasOwnProperty.call(o, key)) continue;
      var val = o[key];
      if (val === null || val === undefined) continue;
      if (typeof val === "string") {
        var ts = val.trim();
        if (ts) return ts;
        continue;
      }
      if (typeof val === "number" && !isNaN(val)) return String(val);
      if (typeof val === "boolean") return val ? "true" : "false";
      if (typeof val === "object" && !Array.isArray(val)) {
        var inner = extractScalarFromObject(val, depth + 1);
        if (inner) return inner;
      }
    }
    return null;
  }

  /** Phase10：rentalai_result 区块展示（无 JSON 原始输出、无 null/undefined 泄露）。 */
  function formatAnalyzeField(v) {
    if (v === null || v === undefined) return "Not provided";
    if (typeof v === "string") {
      var st = v.trim();
      if (!st || st === "undefined" || st === "null") return "Not provided";
      return st;
    }
    if (typeof v === "number" && !isNaN(v)) return String(v);
    if (typeof v === "boolean") return v ? "true" : "false";
    if (Array.isArray(v)) {
      if (!v.length) return "Not provided";
      var parts = [];
      var j;
      for (j = 0; j < v.length; j++) {
        var p = formatAnalyzeField(v[j]);
        if (p && p !== "Not provided") parts.push(p);
      }
      return parts.length ? parts.join(", ") : "Not provided";
    }
    if (typeof v === "object") {
      var ex = extractScalarFromObject(v);
      return ex || "Not provided";
    }
    var out = String(v).trim();
    if (!out || out === "[object Object]" || out === "undefined" || out === "null") {
      return "Not provided";
    }
    return out;
  }

  function setAnalyzeField(elementId, raw) {
    var el = document.getElementById(elementId);
    if (el) el.textContent = formatAnalyzeField(raw);
  }

  /**
   * Phase15：区分合同入口（rentalai_analysis_type=contract）与默认房源分析页眉。
   */
  function setResultPageHeader(variant) {
    var h = document.getElementById("rentalai-result-page-title");
    var sub = document.getElementById("rentalai-result-page-sub");
    if (!h || !sub) return;
    if (variant === "contract") {
      h.textContent = "Rental Contract Analysis Result";
      sub.textContent =
        "Here is your contract risk summary based on the information provided.";
    } else {
      h.textContent = "RentalAI Analysis Result";
      sub.textContent =
        "Here is your rental decision summary based on the information provided.";
    }
    try {
      document.title =
        variant === "contract"
          ? "Rental Contract Analysis Result · RentalAI"
          : "RentalAI Analysis Result · RentalAI";
    } catch (eT) {}
  }

  /**
   * Phase15 Step2-3：五卡片标题 — contract 与 property 分流（仅文案，数据字段来源不变）。
   */
  function setDirectFiveCardTitles(variant) {
    var isContract = variant === "contract";
    var t1 = isContract ? "Contract Recommendation" : "Final Recommendation";
    var t2 = isContract ? "Contract Risk Score" : "Overall Score";
    var t3 = isContract ? "Why this contract result?" : "Why this result?";
    var t4 = isContract ? "Key Contract Risks" : "Main Risks";
    var t5 = isContract
      ? "What should you do before signing?"
      : "What should you do next?";
    var el;
    el = document.getElementById("rentalai-h-final");
    if (el) el.textContent = t1;
    el = document.getElementById("rentalai-h-score");
    if (el) el.textContent = t2;
    el = document.getElementById("rentalai-h-why");
    if (el) el.textContent = t3;
    el = document.getElementById("rentalai-h-risks");
    if (el) el.textContent = t4;
    el = document.getElementById("rentalai-h-next");
    if (el) el.textContent = t5;
  }

  /**
   * Phase10 Step2-1：从 data.score 解析数字（仅展示，不修改来源）。非纯数字字符串返回 null。
   */
  function parseNumericScore(raw) {
    if (raw === null || raw === undefined) return null;
    if (typeof raw === "number" && !isNaN(raw)) return raw;
    if (typeof raw === "string") {
      var t = raw.trim();
      if (!t) return null;
      if (/^-?\d+(\.\d+)?$/.test(t)) {
        var n = parseFloat(t);
        return isNaN(n) ? null : n;
      }
      return null;
    }
    if (typeof raw === "object" && raw !== null && !Array.isArray(raw)) {
      var ex = extractScalarFromObject(raw);
      if (ex != null && String(ex).trim() !== "") {
        var t2 = String(ex).trim();
        if (/^-?\d+(\.\d+)?$/.test(t2)) {
          var n2 = parseFloat(t2);
          return isNaN(n2) ? null : n2;
        }
      }
    }
    return null;
  }

  /** 数字 → 大号「n / 100」；否则沿用 formatAnalyzeField（绝不输出 undefined / null）。 */
  function renderScoreField(raw) {
    var el = document.getElementById("field-score");
    if (!el) return;
    var n = parseNumericScore(raw);
    if (n !== null && !isNaN(n)) {
      var displayNum = Number.isInteger(n) ? String(n) : String(Math.round(n * 100) / 100);
      el.className = "rentalai-field-body rentalai-score-body";
      el.setAttribute("aria-label", displayNum + " out of 100");
      el.innerHTML =
        "<span class=\"rentalai-score-value\">" +
        escapeHtml(displayNum) +
        "</span><span class=\"rentalai-score-denom\"> / 100</span>";
      return;
    }
    el.removeAttribute("aria-label");
    el.className = "rentalai-field-body rentalai-score-body rentalai-score-body--text";
    el.textContent = formatAnalyzeField(raw);
  }

  /**
   * Phase10 Step1-2：Final Recommendation 展示文案上的关键词着色（Not Recommended 优先于 Recommended）。
   */
  function verdictAccentClass(displayText) {
    var s = displayText == null ? "" : String(displayText);
    if (s.indexOf("Not Recommended") !== -1) return "rentalai-verdict--not-recommended";
    if (s.indexOf("Recommended") !== -1) return "rentalai-verdict--recommended";
    if (s.indexOf("Caution") !== -1) return "rentalai-verdict--caution";
    return "";
  }

  function applyVerdictCard(blockEl, displayText) {
    if (!blockEl) return;
    blockEl.classList.remove(
      "rentalai-verdict--recommended",
      "rentalai-verdict--caution",
      "rentalai-verdict--not-recommended"
    );
    var cls = verdictAccentClass(displayText);
    if (cls) blockEl.classList.add(cls);
  }

  function itemToListLine(item) {
    if (item === null || item === undefined) return "";
    if (typeof item === "object" && !Array.isArray(item)) {
      var ex = extractScalarFromObject(item);
      return ex || "";
    }
    if (Array.isArray(item)) {
      var fa = formatAnalyzeField(item);
      return fa === "Not provided" ? "" : fa;
    }
    var s = String(item).trim();
    if (!s || s === "[object Object]") return "";
    return s;
  }

  /**
   * Why / Risks / Next Step：数组 → 每条单独 bullet；可读 object 提取；空态 copy；保留 user_facing fallback。
   */
  function renderExplainCard(elementId, analysisVal, fallbackVal, emptyMessage) {
    var el = document.getElementById(elementId);
    if (!el) return;
    var emptyCopy =
      emptyMessage ||
      "Not provided";

    function renderIntoPrimary(val) {
      if (val === null || val === undefined) return false;
      if (Array.isArray(val)) {
        if (!val.length) return false;
        var lines = val.map(itemToListLine).filter(function (s) {
          return s && String(s).trim();
        });
        if (!lines.length) return false;
        el.className = "rentalai-field-body";
        el.innerHTML =
          "<ul class=\"rentalai-bullet-list rentalai-explain-list\">" +
          lines
            .map(function (line) {
              return "<li>" + escapeHtmlMultiline(line) + "</li>";
            })
            .join("") +
          "</ul>";
        return true;
      }
      if (typeof val === "string" && val.trim()) {
        el.className = "rentalai-field-body";
        el.innerHTML = escapeHtmlMultiline(val.trim());
        return true;
      }
      if (typeof val === "number" && !isNaN(val)) {
        el.className = "rentalai-field-body";
        el.textContent = String(val);
        return true;
      }
      if (typeof val === "boolean") {
        el.className = "rentalai-field-body";
        el.textContent = val ? "true" : "false";
        return true;
      }
      if (typeof val === "object") {
        var txt = formatAnalyzeField(val);
        if (txt !== "Not provided") {
          el.className = "rentalai-field-body";
          el.textContent = txt;
          return true;
        }
        return false;
      }
      return false;
    }

    if (renderIntoPrimary(analysisVal)) return;
    if (renderIntoPrimary(fallbackVal)) return;
    el.className = "rentalai-field-body rentalai-explain-empty";
    el.textContent = emptyCopy;
  }

  function renderDirectAnalyzeResult(payload) {
    var data =
      payload && payload.data && typeof payload.data === "object"
        ? payload.data
        : payload && typeof payload === "object"
          ? payload
          : {};

    var housingEl = document.getElementById("housing-mode");
    var legacyEl = document.getElementById("legacy-mode");
    var directBlocks = document.getElementById("rentalai-direct-blocks");
    var noDataMsg = document.getElementById("rentalai-no-data-msg");
    var fiveBlocks = document.getElementById("rentalai-five-blocks");

    if (housingEl) housingEl.classList.add("hidden");
    if (legacyEl) legacyEl.classList.add("hidden");
    if (directBlocks) directBlocks.classList.remove("hidden");
    if (noDataMsg) noDataMsg.classList.add("hidden");
    if (fiveBlocks) fiveBlocks.classList.remove("hidden");

    var analysis = data.analysis || {};
    var uf = data.user_facing || {};
    var decision = data.decision || {};

    var finalRaw = decision.final_summary;
    var finalDisplay = formatAnalyzeField(finalRaw);
    var finalEl = document.getElementById("field-final-recommendation");
    if (finalEl) finalEl.textContent = finalDisplay;
    applyVerdictCard(document.getElementById("block-final-recommendation"), finalDisplay);

    renderScoreField(data.score);

    renderExplainCard(
      "field-why",
      analysis.supporting_reasons,
      uf.reason,
      "No clear supporting reasons were provided."
    );
    renderExplainCard(
      "field-main-risks",
      analysis.primary_blockers,
      uf.risk_note,
      "No major risks were detected."
    );
    renderExplainCard(
      "field-next-step",
      analysis.required_actions_before_proceeding,
      uf.next_step,
      "No further action is required at this stage."
    );

    var at = sessionStorage.getItem("rentalai_analysis_type");
    var variant = at === "contract" ? "contract" : "property";
    setResultPageHeader(variant);
    setDirectFiveCardTitles(variant);
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
    setResultPageHeader("property");
    var housingEl = document.getElementById("housing-mode");
    var legacyEl = document.getElementById("legacy-mode");
    var directBlocks = document.getElementById("rentalai-direct-blocks");
    if (directBlocks) directBlocks.classList.add("hidden");
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
  function syncLocalFavList(propertyKey, add) {
    var key = propertyKey != null ? String(propertyKey) : "";
    if (!key) return;
    try {
      var favs = JSON.parse(localStorage.getItem(favStorageKey()) || "[]");
      if (!Array.isArray(favs)) favs = [];
      var ix = favs.indexOf(key);
      if (add) {
        if (ix < 0) favs.push(key);
      } else if (ix >= 0) {
        favs.splice(ix, 1);
      }
      localStorage.setItem(favStorageKey(), JSON.stringify(favs));
    } catch (e) {}
  }

  /**
   * 全站统一：用 RentalAIServerFavoritesApi 的快照行刷新 #reco-list 收藏按钮（与 compare 页同源）。
   */
  function applyServerRowsToRecoButtons(rows) {
    var api = window.RentalAIServerFavoritesApi;
    var matchFn = api && typeof api.favoriteMatchesIdentifiers === "function" ? api.favoriteMatchesIdentifiers : null;
    rows = rows || [];
    var buttons = document.querySelectorAll("#reco-list .fav-btn");
    for (var b = 0; b < buttons.length; b++) {
      var btn = buttons[b];
      var pid = (btn.getAttribute("data-property-id") || "").trim();
      var url = (btn.getAttribute("data-listing-url") || "").trim();
      var found = null;
      for (var i = 0; i < rows.length; i++) {
        var f = rows[i];
        if (matchFn) {
          if (matchFn(f, pid, url)) {
            found = f;
            break;
          }
        } else {
          var fp = f.property_id != null ? String(f.property_id).trim() : "";
          var fu = (f.listing_url || "").trim();
          if (fp && pid && fp === pid) {
            found = f;
            break;
          }
          if (fu && url && fu === url) {
            found = f;
            break;
          }
        }
      }
      if (found && found.id) {
        btn.setAttribute("data-server-favorite-id", found.id);
        btn.innerText = "✅ 已收藏";
      } else {
        btn.setAttribute("data-server-favorite-id", "");
            var idAttr = btn.getAttribute("data-id");
            var fkAttr = (btn.getAttribute("data-favorite-key") || "").trim();
            var favs = JSON.parse(localStorage.getItem(favStorageKey()) || "[]");
            var isFav =
              Array.isArray(favs) &&
              (favs.includes(String(idAttr)) || (fkAttr && favs.includes(fkAttr)));
            btn.innerText = isFav ? "✅ 已收藏" : "⭐ 收藏";
      }
    }
  }

  /**
   * 首次/拉取：与 server_favorites 缓存对齐；登录用户与游客收藏不合并。
   */
  function syncLegacyFavoriteButtonsFromServer() {
    var api = window.RentalAIServerFavoritesApi;
    if (!api) return;
    if (typeof api.refreshFavoritesCache === "function") {
      api
        .refreshFavoritesCache(200)
        .then(function (rows) {
          if (rows) applyServerRowsToRecoButtons(rows);
        })
        .catch(function (err) {
          console.error(err);
        });
      return;
    }
    if (typeof api.listFavorites !== "function") return;
    api
      .listFavorites(200)
      .then(function (data) {
        applyServerRowsToRecoButtons((data && data.favorites) || []);
      })
      .catch(function (err) {
        console.error(err);
      });
  }

  try {
    window.addEventListener("rentalai-favorites-updated", function (ev) {
      var d = ev && ev.detail;
      var rows = d && d.favorites;
      if (rows === undefined || rows === null) {
        var apiR = window.RentalAIServerFavoritesApi;
        if (apiR && typeof apiR.getCachedFavoritesRows === "function") {
          rows = apiR.getCachedFavoritesRows();
        }
      }
      if (!rows) rows = [];
      applyServerRowsToRecoButtons(rows);
    });
  } catch (eEv) {}

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
    setResultPageHeader("property");
    var housingEl = document.getElementById("housing-mode");
    var legacyEl = document.getElementById("legacy-mode");
    var directBlocks = document.getElementById("rentalai-direct-blocks");
    if (directBlocks) directBlocks.classList.add("hidden");
    if (housingEl) housingEl.classList.add("hidden");
    if (legacyEl) legacyEl.classList.remove("hidden");

    var rawEl = document.getElementById("raw-display");
    var dl = document.getElementById("structured-dl");
    var recoList = document.getElementById("reco-list");
    var recoEmpty = document.getElementById("reco-empty");
    var summaryLine = document.getElementById("summary-line");

    if (!data || !data.success) {
      if (rawEl) rawEl.textContent = "No analysis result available";
      if (recoEmpty) {
        recoEmpty.classList.remove("hidden");
        recoEmpty.textContent = "No analysis result available";
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
      if (!Array.isArray(favs)) favs = [];
      var apiK = window.RentalAIServerFavoritesApi;
      var fkBtn =
        apiK && typeof apiK.buildFavoriteKey === "function"
          ? apiK.buildFavoriteKey({
              listing_url: (r.source_url || r.listing_url || r.url || "").trim(),
              source_url: r.source_url,
              url: r.url,
              property_id: String(r.listing_id != null ? r.listing_id : r.rank),
              listing_id: r.listing_id,
              rank: r.rank,
            })
          : "";
      var isFav =
        (fkBtn && favs.includes(fkBtn)) || favs.includes(String(r.listing_id || r.rank));
      var btnText = isFav ? "✅ 已收藏" : "⭐ 收藏";
      var li = document.createElement("li");
      li.className = "reco-item card";
      var title = r.title || r.house_label || "房源";
      var propId = String(r.listing_id != null ? r.listing_id : r.rank);
      var listUrl = (r.source_url || r.listing_url || r.url || "").trim();
      var rentNum = r.rent != null ? Number(r.rent) : NaN;
      var priceAttr = !isNaN(rentNum) ? String(rentNum) : "";
      var pcAttr = r.postcode != null ? String(r.postcode) : "";
      var rent = r.rent != null ? "£" + r.rent + " /月" : "租金 —";
      var beds = r.bedrooms != null ? r.bedrooms + " 卧" : "卧室 —";
      var loc = [r.postcode, r.area].filter(Boolean).join(" · ") || "地区 —";
      var score =
        r.final_score != null ? "总分 " + Number(r.final_score).toFixed(1) : "";
      var explainClip = r.explain ? String(r.explain).slice(0, 900) : "";
      var risksJsonStr = "[]";
      try {
        risksJsonStr = JSON.stringify((r.risks || []).slice(0, 16));
      } catch (eRj0) {
        risksJsonStr = "[]";
      }
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
        "<br/><button type='button' class='fav-btn' data-id='" +
        escapeAttr(propId) +
        "' data-property-id='" +
        escapeAttr(propId) +
        "' data-listing-url='" +
        escapeAttr(listUrl) +
        "' data-title='" +
        escapeAttr(title) +
        "' data-postcode='" +
        escapeAttr(pcAttr) +
        "' data-price='" +
        escapeAttr(priceAttr) +
        "' data-favorite-key='" +
        escapeAttr(fkBtn || propId) +
        "' data-explain='" +
        escapeAttr(explainClip) +
        "' data-decision='" +
        escapeAttr(r.decision || "") +
        "' data-decision-reason='" +
        escapeAttr((r.decision_reason || "").slice(0, 600)) +
        "' data-final-score='" +
        escapeAttr(r.final_score != null ? String(r.final_score) : "") +
        "' data-listing-id='" +
        escapeAttr(r.listing_id != null ? String(r.listing_id) : "") +
        "' data-rank='" +
        escapeAttr(r.rank != null ? String(r.rank) : "") +
        "' data-risks-json='" +
        escapeAttr(risksJsonStr) +
        "' data-bedrooms='" +
        escapeAttr(r.bedrooms != null ? String(r.bedrooms) : "") +
        "' data-rent-num='" +
        escapeAttr(r.rent != null ? String(r.rent) : "") +
        "' data-server-favorite-id=''>" +
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

    syncLegacyFavoriteButtonsFromServer();

    if (!document.documentElement._rentalaiLegacyFavClickBound) {
      document.documentElement._rentalaiLegacyFavClickBound = true;
      document.addEventListener("click", function (e) {
        var btn = e.target && e.target.closest ? e.target.closest(".fav-btn") : null;
        if (!btn || !btn.classList.contains("fav-btn")) return;
        var api = window.RentalAIServerFavoritesApi;
        if (!api || typeof api.addFavorite !== "function") {
          console.error("RentalAIServerFavoritesApi unavailable");
          return;
        }
        var sid = (btn.getAttribute("data-server-favorite-id") || "").trim();
        var propKey = btn.getAttribute("data-id");
        var localFavKey = (btn.getAttribute("data-favorite-key") || "").trim() || propKey;
        if (sid) {
          api
            .removeFavorite(sid)
            .then(function () {
              btn.setAttribute("data-server-favorite-id", "");
              btn.innerText = "⭐ 收藏";
              syncLocalFavList(localFavKey, false);
            })
            .catch(function (err) {
              console.error(err);
            });
          return;
        }
        var payload = {
          propertyId: (btn.getAttribute("data-property-id") || "").trim(),
          listing_url: (btn.getAttribute("data-listing-url") || "").trim() || null,
          title: (btn.getAttribute("data-title") || "").trim() || "Listing",
          postcode: (btn.getAttribute("data-postcode") || "").trim() || null,
          source: "ai_result",
          sourceType: "legacy_recommendation",
        };
        var pr = (btn.getAttribute("data-price") || "").trim();
        if (pr) {
          var pn = parseFloat(pr);
          payload.price = isNaN(pn) ? null : pn;
        }
        try {
          var rEnt = (btn.getAttribute("data-explain") || "").trim();
          payload.explain = rEnt || null;
          payload.decision = (btn.getAttribute("data-decision") || "").trim() || null;
          payload.decision_reason = (btn.getAttribute("data-decision-reason") || "").trim() || null;
          var fs = (btn.getAttribute("data-final-score") || "").trim();
          if (fs) {
            var fsn = parseFloat(fs);
            payload.final_score = isNaN(fsn) ? null : fsn;
          }
          var li = (btn.getAttribute("data-listing-id") || "").trim();
          if (li) {
            var lin = parseInt(li, 10);
            payload.listing_id = isNaN(lin) ? li : lin;
          }
          var rk = (btn.getAttribute("data-rank") || "").trim();
          if (rk) {
            var rkn = parseInt(rk, 10);
            payload.rank = isNaN(rkn) ? null : rkn;
          }
          var rs = (btn.getAttribute("data-risks-json") || "").trim();
          if (rs) {
            try {
              payload.risks = JSON.parse(rs);
            } catch (eRJ) {
              payload.risks = [];
            }
          }
          var br = (btn.getAttribute("data-bedrooms") || "").trim();
          if (br) {
            var brn = parseFloat(br);
            payload.bedrooms = isNaN(brn) ? br : brn;
          }
          var rentA = (btn.getAttribute("data-rent-num") || "").trim();
          if (rentA) {
            var rentN = parseFloat(rentA);
            payload.rent = isNaN(rentN) ? null : rentN;
          }
        } catch (ePay) {}
        try {
          var SH = window.RentalAIAnalysisHistoryStore;
          if (SH && typeof SH.listByType === "function") {
            var props = SH.listByType("property") || [];
            if (props[0] && props[0].id) payload.historyEntryId = props[0].id;
          }
        } catch (eHi0) {}
        api
          .addFavorite(payload)
          .then(function (res) {
            var fav = res && res.favorite;
            if (fav && fav.id) btn.setAttribute("data-server-favorite-id", fav.id);
            btn.innerText = "✅ 已收藏";
            syncLocalFavList(localFavKey, true);
          })
          .catch(function (err) {
            if (err && err.status === 409 && typeof api.refreshFavoritesCache === "function") {
              api
                .refreshFavoritesCache(200)
                .then(function (rows) {
                  if (!rows) return;
                  for (var j = 0; j < rows.length; j++) {
                    var f = rows[j];
                    if (
                      f &&
                      f.id &&
                      typeof api.favoriteMatchesIdentifiers === "function" &&
                      api.favoriteMatchesIdentifiers(
                        f,
                        (payload.propertyId || "").trim(),
                        (payload.listing_url || "").trim()
                      )
                    ) {
                      btn.setAttribute("data-server-favorite-id", f.id);
                      btn.innerText = "✅ 已收藏";
                      syncLocalFavList(localFavKey, true);
                      return;
                    }
                  }
                })
                .catch(function (e2) {
                  console.error(e2);
                });
              return;
            }
            console.error(err);
          });
      });
    }

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
  var directRaw =
    sessionStorage.getItem(ANALYZE_RESULT_KEY) ||
    sessionStorage.getItem(DIRECT_SESSION_KEY) ||
    localStorage.getItem(DIRECT_LOCAL_KEY);
  var directPayload = null;
  try {
    directPayload = directRaw ? JSON.parse(directRaw) : null;
  } catch (e0) {
    directPayload = null;
  }

  if (directPayload && typeof directPayload === "object") {
    renderDirectAnalyzeResult(directPayload);
  } else {
    var rawH = sessionStorage.getItem(HOUSING_KEY);
    var dataH = null;
    try {
      dataH = rawH ? JSON.parse(rawH) : null;
    } catch (e) {
      dataH = null;
    }

    /* 主链路失败态：主分析未成功时的结果区展示（仍属 housing 容器内）。 */
    if (dataH && dataH.success === false) {
      setResultPageHeader("property");
      var housingEl0 = document.getElementById("housing-mode");
      var legacyEl0 = document.getElementById("legacy-mode");
      var directBlocks0 = document.getElementById("rentalai-direct-blocks");
      if (directBlocks0) directBlocks0.classList.add("hidden");
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
        showRentalaiToast("No analysis data available to save.");
        return;
      }
      var parsed;
      try {
        parsed = JSON.parse(rawSave);
      } catch (err) {
        showRentalaiToast("No analysis data available to save.");
        return;
      }
      if (!parsed || parsed.success === false) {
        showRentalaiToast("No analysis data available to save.");
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
      showRentalaiToast("Saved to your history.");
    });
  })();
})();
