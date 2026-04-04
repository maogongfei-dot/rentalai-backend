/**
 * Phase 4 合同分析页：表单 UI + summary_view 分段展示（逻辑见 contract_analysis_api.js）。
 * 主流程：粘贴文本 | 上传 .txt/.pdf/.docx；服务端 file_path 为开发项（localStorage +「开发者」开关或 ?dev=1）。
 */
(function () {
  var CA = window.RentalAIContractAnalysis;
  if (
    !CA ||
    typeof CA.analyzeContractText !== "function" ||
    typeof CA.analyzeContractUpload !== "function"
  ) {
    if (typeof console !== "undefined" && console.error) {
      console.error("contract_analysis_api.js must load before contract_analysis_page.js");
    }
    return;
  }

  var modeText = document.getElementById("contract-mode-text");
  var modeFile = document.getElementById("contract-mode-file");
  var panelText = document.getElementById("contract-panel-text");
  var panelFile = document.getElementById("contract-panel-file");
  var ta = document.getElementById("contract-text");
  var filePathInput = document.getElementById("contract-file-path");
  var uploadFile = document.getElementById("contract-upload-file");
  var uploadHint = document.getElementById("contract-upload-file-hint");
  var btn = document.getElementById("contract-submit");
  var loadingEl = document.getElementById("contract-loading");
  var loadingText = document.getElementById("contract-loading-text");
  var errEl = document.getElementById("contract-error");
  var emptyEl = document.getElementById("contract-state-empty");
  var resultSection = document.getElementById("contract-state-result");
  var resultSourceEl = document.getElementById("contract-result-source");
  var resultBody = document.getElementById("contract-result-body");
  var persistHintEl = document.getElementById("contract-history-persist-hint");
  var devBundle = document.getElementById("contract-dev-bundle");
  var devToggle = document.getElementById("contract-dev-toggle");
  var demoPathWrap = document.getElementById("contract-demo-path-wrap");
  var DEV_LS_KEY = "rentalai_contract_analysis_dev";

  if (!btn || !ta) return;

  /** 与 ``contract_analysis_upload_handler.contract_upload_max_bytes`` 默认一致（15 MiB）。 */
  var CONTRACT_UPLOAD_MAX_BYTES = 15 * 1024 * 1024;

  function fileExtLower(name) {
    var n = (name || "").trim();
    var i = n.lastIndexOf(".");
    return i >= 0 ? n.slice(i).toLowerCase() : "";
  }

  var ALLOWED_UPLOAD_EXT = new Set([".txt", ".pdf", ".docx"]);

  function formatUploadSize(bytes) {
    if (bytes == null || bytes < 0) return "";
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(2) + " MB";
  }

  function validateUploadFile(file) {
    if (!file || !file.name) {
      return "请选择要上传的合同文件。";
    }
    var ext = fileExtLower(file.name);
    if (!ALLOWED_UPLOAD_EXT.has(ext)) {
      return "不支持的文件类型：仅支持 .txt、.pdf、.docx（当前：" + (ext || "无扩展名") + "）。";
    }
    if (file.size === 0) {
      return "所选文件为空（0 字节），请换一份有效合同文件。";
    }
    if (file.size > CONTRACT_UPLOAD_MAX_BYTES) {
      return (
        "文件过大（" +
        formatUploadSize(file.size) +
        "），单文件上限为 " +
        formatUploadSize(CONTRACT_UPLOAD_MAX_BYTES) +
        "。请选择较小的文件或联系管理员调整上限。"
      );
    }
    return "";
  }

  function setContractPersistHint(msg, variant) {
    if (!persistHintEl) return;
    persistHintEl.classList.remove("save-banner-ok", "save-banner-warn", "save-banner-local", "hidden");
    if (!msg) {
      persistHintEl.classList.add("hidden");
      persistHintEl.textContent = "";
      return;
    }
    persistHintEl.textContent = msg;
    if (variant === "warn") persistHintEl.classList.add("save-banner-warn");
    else if (variant === "local") persistHintEl.classList.add("save-banner-local");
    else persistHintEl.classList.add("save-banner-ok");
  }

  function contractPersistHintVariant(pr) {
    if (!pr || !pr.hint) return null;
    if (pr.hintIsLocal) return "local";
    if (pr.fallbackLocal) return "warn";
    return "ok";
  }

  function renderSourceHint(meta) {
    if (!resultSourceEl) return;
    if (!meta || !meta.kind) {
      resultSourceEl.classList.add("hidden");
      resultSourceEl.textContent = "";
      return;
    }
    var label = meta.label != null ? String(meta.label) : "";
    var line = "";
    if (meta.kind === "text") {
      line = "当前来源：粘贴文本（pasted text）";
    } else if (meta.kind === "upload") {
      line =
        "当前来源：上传文件（uploaded file）" +
        (label ? " — " + label : "");
    } else if (meta.kind === "path") {
      line =
        "当前来源：服务端路径（server file path）" +
        (label ? " — " + label : "");
    } else {
      line = "当前来源：未知";
    }
    resultSourceEl.textContent = line;
    resultSourceEl.classList.remove("hidden");
  }

  function syncDevBundleVisible() {
    if (!devBundle) return;
    var dev = false;
    try {
      dev = window.localStorage.getItem(DEV_LS_KEY) === "1";
    } catch (e) {}
    var fileMode = modeFile && modeFile.checked;
    devBundle.classList.toggle("hidden", !(dev && fileMode));
  }

  function applyContractDevUi(show) {
    if (demoPathWrap) {
      demoPathWrap.classList.toggle("hidden", !show);
      demoPathWrap.setAttribute("aria-hidden", show ? "false" : "true");
    }
    if (devToggle) {
      devToggle.textContent = show
        ? "开发者：隐藏服务端路径"
        : "开发者：显示服务端路径（file_path）";
    }
    if (!show && filePathInput) filePathInput.value = "";
    syncDevBundleVisible();
  }

  function initContractDevUi() {
    try {
      var q = new URLSearchParams(window.location.search || "");
      if (q.get("dev") === "1") {
        try {
          window.localStorage.setItem(DEV_LS_KEY, "1");
        } catch (e) {}
        try {
          var u = new URL(window.location.href);
          u.searchParams.delete("dev");
          window.history.replaceState({}, "", u.pathname + u.search + u.hash);
        } catch (e2) {}
      }
    } catch (e3) {}
    var show = false;
    try {
      show = window.localStorage.getItem(DEV_LS_KEY) === "1";
    } catch (e4) {}
    applyContractDevUi(show);
  }

  initContractDevUi();

  if (devToggle) {
    devToggle.addEventListener("click", function () {
      var cur = false;
      try {
        cur = window.localStorage.getItem(DEV_LS_KEY) === "1";
      } catch (e) {}
      var next = !cur;
      try {
        if (next) window.localStorage.setItem(DEV_LS_KEY, "1");
        else window.localStorage.removeItem(DEV_LS_KEY);
      } catch (e2) {}
      applyContractDevUi(next);
    });
  }

  function setModePanels() {
    var file = modeFile && modeFile.checked;
    if (panelText) panelText.classList.toggle("hidden", file);
    if (panelFile) panelFile.classList.toggle("hidden", !file);
    syncDevBundleVisible();
  }

  if (modeText)
    modeText.addEventListener("change", function () {
      if (modeText.checked) setModePanels();
    });
  if (modeFile)
    modeFile.addEventListener("change", function () {
      if (modeFile.checked) setModePanels();
    });
  setModePanels();

  /** Phase 4 Round7：智能入口一次性预填 #contract-text（见 assistant_prefill.js） */
  (function applyAssistantPrefillContract() {
    try {
      var P = window.RentalAIAssistantPrefill;
      if (!P || typeof P.consumeAssistantHandoff !== "function") return;
      var handoff = P.consumeAssistantHandoff("contract");
      if (!handoff) return;
      if (modeText) {
        modeText.checked = true;
        if (modeFile) modeFile.checked = false;
        setModePanels();
      }
      var raw = handoff.draft;
      var text = raw != null ? String(raw).trim() : "";
      if (text && ta) {
        ta.value = raw;
        ta.focus();
      }
      var hintEl = document.getElementById("assistant-prefill-hint");
      if (hintEl && text) {
        hintEl.textContent =
          "已从「智能入口」带入描述，可编辑后点击「提交分析」（不会自动提交）。";
        hintEl.classList.remove("hidden");
      }
    } catch (e) {}
  })();

  var Demo = window.RentalAIContractAnalysisDemo;
  var btnDemoText = document.getElementById("contract-demo-fill-text");
  var btnDemoPath = document.getElementById("contract-demo-fill-path");

  function fillSampleText() {
    if (!Demo) return;
    if (modeText) modeText.checked = true;
    setModePanels();
    if (ta) ta.value = Demo.SAMPLE_CONTRACT_TEXT;
    if (filePathInput) filePathInput.value = "";
    if (uploadFile) uploadFile.value = "";
    if (uploadHint) uploadHint.textContent = "";
    setError("");
  }

  function fillSamplePath() {
    if (!Demo) return;
    if (modeFile) modeFile.checked = true;
    setModePanels();
    if (filePathInput) filePathInput.value = Demo.SAMPLE_FILE_PATH;
    if (uploadFile) uploadFile.value = "";
    if (uploadHint) uploadHint.textContent = "";
    setError("");
  }

  if (btnDemoText && Demo) btnDemoText.addEventListener("click", fillSampleText);
  if (btnDemoPath && Demo) btnDemoPath.addEventListener("click", fillSamplePath);

  if (uploadFile && uploadHint) {
    uploadFile.addEventListener("change", function () {
      var f = uploadFile.files && uploadFile.files[0];
      if (!f) {
        uploadHint.textContent = "";
        return;
      }
      var sizePart = f.size != null ? "，大小 " + formatUploadSize(f.size) : "";
      var bad = validateUploadFile(f);
      uploadHint.textContent = bad
        ? "已选择：" + f.name + sizePart + " — " + bad
        : "已选择：" + f.name + sizePart + "（" + (f.type || "未知类型") + "）";
    });
  }

  function setLoading(on, message) {
    if (btn) btn.disabled = !!on;
    if (loadingEl) {
      loadingEl.classList.toggle("hidden", !on);
      loadingEl.setAttribute("aria-busy", on ? "true" : "false");
    }
    if (loadingText) loadingText.textContent = on ? message || "分析中…" : "";
    if (on) {
      if (emptyEl) emptyEl.classList.add("hidden");
      if (resultSection) resultSection.classList.add("hidden");
    }
  }

  function setError(msg) {
    if (!errEl) return;
    if (msg) {
      errEl.textContent = msg;
      errEl.classList.remove("hidden");
    } else {
      errEl.textContent = "";
      errEl.classList.add("hidden");
    }
  }

  function escapeHtml(s) {
    var d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  function safeStr(v) {
    if (v == null || v === undefined) return "";
    return String(v);
  }

  function isEmptyText(v) {
    return safeStr(v).trim() === "";
  }

  function safeArray(v) {
    return Array.isArray(v) ? v : [];
  }

  function safeObject(v) {
    return v && typeof v === "object" && !Array.isArray(v) ? v : {};
  }

  /** 条款卡片默认露出条数；超出部分用「显示其余」展开（与 upload/text 无关，仅结果 DOM）。 */
  var CONTRACT_RESULT_CLAUSE_BATCH = 3;
  /** 每条内 <details> 默认展开前几条（便于扫读）。 */
  var CONTRACT_RESULT_DETAILS_OPEN_FIRST = 2;
  /** 完整性清单默认条数上限，超出折叠。 */
  var CONTRACT_RESULT_COMPLETE_LIST_CAP = 6;

  function truncatePreview(s, max) {
    var t = safeStr(s).trim();
    if (!t) return "";
    if (t.length <= max) return t;
    return t.slice(0, max) + "…";
  }

  /**
   * 将 API / 文案中的严重度归一为 high | medium | low | ""（无法识别则空，安全回退）。
   */
  function normalizeSeverityTier(raw) {
    var s = safeStr(raw).trim().toLowerCase();
    if (!s) return "";
    if (/高风险|严重|较高/.test(s) || /^高$/.test(s.trim())) return "high";
    if (/中等|中风险|中度/.test(s) || /^中$/.test(s.trim())) return "medium";
    if (/低风险|轻微|^低$/.test(s)) return "low";
    if (/\b(high|critical|severe|major)\b/.test(s)) return "high";
    if (/\b(medium|moderate|mid)\b/.test(s)) return "medium";
    if (/\b(low|minor)\b/.test(s)) return "low";
    return "";
  }

  function severityLabelZh(tier) {
    if (tier === "high") return "高";
    if (tier === "medium") return "中";
    if (tier === "low") return "低";
    return "";
  }

  /** 供 pill 使用的 class（无 tier 时用通用 severity 样式）。 */
  function severityPillClass(tier) {
    if (tier === "high") return "contract-result-pill contract-result-pill--sev-high";
    if (tier === "medium") return "contract-result-pill contract-result-pill--sev-medium";
    if (tier === "low") return "contract-result-pill contract-result-pill--sev-low";
    return "contract-result-pill contract-result-pill--severity";
  }

  /** 总体结论文本中的风险倾向（无独立字段时的轻量启发，识别失败则空）。 */
  function inferOverallConclusionTier(text) {
    if (isEmptyText(text)) return "";
    var s = safeStr(text);
    var low = s.toLowerCase();
    if (
      /\b(high|critical|severe)\b/i.test(low) ||
      /高风险|严重风险|较高风险|重大风险|风险较高|严重关切|风险严重/i.test(s)
    ) {
      return "high";
    }
    if (
      /\b(medium|moderate)\b/i.test(low) ||
      /中等风险|中风险|中度|风险中等/i.test(s)
    ) {
      return "medium";
    }
    if (
      /\b(low|minor)\b/i.test(low) ||
      /低风险|较低|轻微|风险较低|风险可控/i.test(s)
    ) {
      return "low";
    }
    return "";
  }

  function severitySortKey(raw) {
    var t = normalizeSeverityTier(raw);
    if (t === "high") return 0;
    if (t === "medium") return 1;
    if (t === "low") return 2;
    return 3;
  }

  function blockTitle(en, zh) {
    return (
      '<h3 class="contract-result-block-title">' +
      '<span class="contract-result-block-en">' +
      escapeHtml(en) +
      "</span>" +
      ' <span class="contract-result-block-sub">' +
      escapeHtml(zh) +
      "</span></h3>"
    );
  }

  /**
   * 单块结果卡片：外层 article + 标题区 + 内层 body（便于样式与后续扩展）。
   * @param {string} slug data-contract-block 标识（英文 kebab）
   * @param {object} [options] 可选：tier（high|medium|low）用于整卡左边框强调
   */
  function wrapBlock(slug, en, zh, inner, options) {
    options = options || {};
    var tier = options.tier || "";
    var tierClass = tier ? " contract-result-card-block--tier-" + tier : "";
    var tierAttr = tier ? ' data-severity-tier="' + escapeHtml(tier) + '"' : "";
    return (
      '<article class="contract-result-card-block' +
      tierClass +
      '" data-contract-block="' +
      escapeHtml(slug) +
      '"' +
      tierAttr +
      ">" +
      '<header class="contract-result-card-head">' +
      blockTitle(en, zh) +
      "</header>" +
      '<div class="contract-result-card-body">' +
      inner +
      "</div>" +
      "</article>"
    );
  }

  function renderOverallConclusionHtml(text, tierHint) {
    var tier = tierHint != null ? tierHint : inferOverallConclusionTier(text);
    if (isEmptyText(text)) {
      return paragraphOrMuted("", "暂无总体结论");
    }
    var inner = "";
    if (tier) {
      inner += '<div class="contract-result-overall-badge-row">';
      inner +=
        '<span class="' +
        severityPillClass(tier) +
        '">' +
        "风险倾向：" +
        escapeHtml(severityLabelZh(tier)) +
        "</span></div>";
    }
    inner +=
      '<p class="contract-result-text">' +
      escapeHtml(safeStr(text)).replace(/\n/g, "<br/>") +
      "</p>";
    return inner;
  }

  function paragraphOrMuted(text, mutedMsg) {
    if (isEmptyText(text)) {
      return '<p class="contract-result-muted">' + escapeHtml(mutedMsg || "暂无") + "</p>";
    }
    return (
      '<p class="contract-result-text">' +
      escapeHtml(safeStr(text)).replace(/\n/g, "<br/>") +
      "</p>"
    );
  }

  function renderRiskCategorySummary(items) {
    var arr = safeArray(items).slice();
    if (arr.length === 0) {
      return paragraphOrMuted("", "暂无分类汇总");
    }
    arr.sort(function (a, b) {
      return (
        severitySortKey(safeStr(a.highest_severity)) -
        severitySortKey(safeStr(b.highest_severity))
      );
    });
    var html = '<ul class="contract-result-rich-list contract-result-risk-cat-list">';
    for (var i = 0; i < arr.length; i++) {
      var it = arr[i] && typeof arr[i] === "object" ? arr[i] : {};
      var cat = safeStr(it.category) || "（未命名类别）";
      var cnt = it.count != null ? safeStr(it.count) : "—";
      var hi = safeStr(it.highest_severity);
      var sum = safeStr(it.short_summary);
      var hiTier = normalizeSeverityTier(hi);
      var liExtra = hiTier ? " contract-result-rich-item--sev-" + hiTier : "";
      html += '<li class="contract-result-rich-item' + liExtra + '">';
      html += '<div class="contract-result-rich-row">';
      html += '<span class="contract-result-rich-title">' + escapeHtml(cat) + "</span>";
      html += '<span class="contract-result-rich-meta">';
      html +=
        '<span class="contract-result-pill contract-result-pill--muted">条数 ' +
        escapeHtml(cnt) +
        "</span>";
      if (hi) {
        html +=
          '<span class="' +
          (hiTier ? severityPillClass(hiTier) : severityPillClass("")) +
          '" title="' +
          escapeHtml(hi) +
          '">' +
          escapeHtml(hi) +
          "</span>";
      }
      html += "</span></div>";
      if (!isEmptyText(sum)) {
        html +=
          '<p class="contract-result-rich-note">' + escapeHtml(sum) + "</p>";
      }
      html += "</li>";
    }
    html += "</ul>";
    return html;
  }

  function buildHighlightedArticle(it, idx) {
    var title = safeStr(it.risk_title) || "（无标题）";
    var sev = safeStr(it.severity);
    var cat = safeStr(it.risk_category);
    var mt = safeStr(it.matched_text);
    var adv = safeStr(it.short_advice);
    var loc = safeStr(it.location_hint);
    var sevTier = normalizeSeverityTier(sev);
    var subCls =
      "contract-result-subcard" +
      (sevTier ? " contract-result-subcard--sev-" + sevTier : "");
    var html =
      '<article class="' +
      subCls +
      '"' +
      (sevTier ? ' data-severity-tier="' + escapeHtml(sevTier) + '"' : "") +
      ">";
    html += '<div class="contract-result-subcard-head">';
    html += "<strong>" + escapeHtml(title) + "</strong>";
    if (sev || cat) {
      html += '<div class="contract-result-subcard-badges">';
      if (sev) {
        html +=
          '<span class="' +
          severityPillClass(sevTier) +
          '">' +
          escapeHtml(sev) +
          "</span>";
      }
      if (cat) {
        html +=
          '<span class="contract-result-pill contract-result-pill--muted">' +
          escapeHtml(cat) +
          "</span>";
      }
      html += "</div>";
    }
    html += "</div>";
    var hasQuick = !isEmptyText(mt) || !isEmptyText(loc);
    var hasDetail = !isEmptyText(mt) || !isEmptyText(adv) || !isEmptyText(loc);
    if (hasQuick) {
      html += '<div class="contract-result-subcard-quick">';
      if (!isEmptyText(mt)) {
        html +=
          '<p class="contract-result-quick-line"><span class="contract-result-quick-label">摘录</span>';
        html += escapeHtml(truncatePreview(mt, 140)) + "</p>";
      }
      if (!isEmptyText(loc)) {
        html +=
          '<p class="contract-result-quick-line"><span class="contract-result-quick-label">位置</span>';
        html += escapeHtml(truncatePreview(loc, 100)) + "</p>";
      }
      html += "</div>";
    }
    if (hasDetail) {
      var openAttr =
        idx < CONTRACT_RESULT_DETAILS_OPEN_FIRST ? " open" : "";
      html +=
        '<details class="contract-result-item-details"' +
        openAttr +
        ">";
      html +=
        '<summary class="contract-result-expand-summary">完整摘录、建议与位置</summary>';
      html += '<div class="contract-result-expand-body">';
      if (!isEmptyText(mt)) {
        html +=
          '<p class="contract-result-kv"><span class="contract-result-kv-label">摘录（全文）</span>' +
          escapeHtml(mt).replace(/\n/g, "<br/>") +
          "</p>";
      }
      if (!isEmptyText(adv)) {
        html +=
          '<p class="contract-result-kv"><span class="contract-result-kv-label">建议</span>' +
          escapeHtml(adv) +
          "</p>";
      }
      if (!isEmptyText(loc)) {
        html +=
          '<p class="contract-result-kv"><span class="contract-result-kv-label">位置（全文）</span>' +
          escapeHtml(loc) +
          "</p>";
      }
      html += "</div></details>";
    }
    html += "</article>";
    return html;
  }

  function renderHighlightedClauses(items) {
    var arr = safeArray(items).slice();
    if (arr.length === 0) {
      return paragraphOrMuted("", "暂无高亮风险条款");
    }
    arr.sort(function (a, b) {
      return severitySortKey(safeStr(a.severity)) - severitySortKey(safeStr(b.severity));
    });
    var n = arr.length;
    var batch = CONTRACT_RESULT_CLAUSE_BATCH;
    if (n <= batch) {
      var html0 = '<div class="contract-result-subcard-stack">';
      for (var i = 0; i < n; i++) {
        html0 += buildHighlightedArticle(
          arr[i] && typeof arr[i] === "object" ? arr[i] : {},
          i
        );
      }
      html0 += "</div>";
      return html0;
    }
    var html =
      '<div class="contract-result-more-host"><div class="contract-result-subcard-stack">';
    for (var j = 0; j < batch; j++) {
      html += buildHighlightedArticle(
        arr[j] && typeof arr[j] === "object" ? arr[j] : {},
        j
      );
    }
    html += '</div><div class="contract-result-more-wrap hidden">';
    for (var k = batch; k < n; k++) {
      html += buildHighlightedArticle(
        arr[k] && typeof arr[k] === "object" ? arr[k] : {},
        k
      );
    }
    html += "</div>";
    html +=
      '<button type="button" class="contract-result-more-btn">显示其余 ' +
      (n - batch) +
      " 条</button></div>";
    return html;
  }

  function buildClauseSeverityArticle(it, idx) {
    var cid = safeStr(it.clause_id);
    var ctype = safeStr(it.clause_type);
    var score = it.severity_score != null ? safeStr(it.severity_score) : "—";
    var hi = safeStr(it.highest_severity);
    var cnt = it.linked_risk_count != null ? safeStr(it.linked_risk_count) : "—";
    var prev = safeStr(it.short_clause_preview);
    var titles = safeArray(it.linked_risk_titles);
    var titleLine = titles.length ? titles.join("；") : "";
    var hiTier = normalizeSeverityTier(hi);
    var subCls =
      "contract-result-subcard" +
      (hiTier ? " contract-result-subcard--sev-" + hiTier : "");
    var html =
      '<article class="' +
      subCls +
      '"' +
      (hiTier ? ' data-severity-tier="' + escapeHtml(hiTier) + '"' : "") +
      ">";
    html += '<div class="contract-result-subcard-head">';
    html +=
      "<strong>" +
      escapeHtml((cid || "条款") + (ctype ? " · " + ctype : "")) +
      "</strong>";
    html += "</div>";
    html += '<dl class="contract-result-dl">';
    html += "<dt>强度分</dt><dd>" + escapeHtml(score) + "</dd>";
    html += "<dt>最高严重度</dt><dd>";
    if (hi) {
      html +=
        '<span class="' +
        (hiTier ? severityPillClass(hiTier) : severityPillClass("")) +
        '">' +
        escapeHtml(hi) +
        "</span>";
    } else {
      html += escapeHtml("—");
    }
    html += "</dd>";
    html += "<dt>关联风险数</dt><dd>" + escapeHtml(cnt) + "</dd>";
    html += "</dl>";
    var hasQuick = !isEmptyText(prev) || titles.length > 0;
    var hasExpand =
      !isEmptyText(prev) || titles.length > 0 || !isEmptyText(titleLine);
    if (hasQuick) {
      html += '<div class="contract-result-subcard-quick">';
      if (!isEmptyText(prev)) {
        html +=
          '<p class="contract-result-quick-line"><span class="contract-result-quick-label">条款预览</span>';
        html += escapeHtml(truncatePreview(prev, 120)) + "</p>";
      }
      if (titles.length) {
        html +=
          '<p class="contract-result-quick-line"><span class="contract-result-quick-label">关联风险</span>';
        html += escapeHtml(truncatePreview(titleLine, 100)) + "</p>";
      }
      html += "</div>";
    }
    if (hasExpand) {
      var openAttr2 =
        idx < CONTRACT_RESULT_DETAILS_OPEN_FIRST ? " open" : "";
      html +=
        '<details class="contract-result-item-details"' +
        openAttr2 +
        ">";
      html +=
        '<summary class="contract-result-expand-summary">完整预览与关联风险标题</summary>';
      html += '<div class="contract-result-expand-body">';
      if (!isEmptyText(prev)) {
        html +=
          '<p class="contract-result-kv contract-result-kv--preview">' +
          escapeHtml(prev).replace(/\n/g, "<br/>") +
          "</p>";
      }
      if (titles.length) {
        html += '<p class="contract-result-kv-label">关联风险标题</p><ul class="contract-result-tiny-list">';
        for (var t = 0; t < titles.length; t++) {
          html += "<li>" + escapeHtml(safeStr(titles[t])) + "</li>";
        }
        html += "</ul>";
      } else if (!isEmptyText(titleLine)) {
        html +=
          '<p class="contract-result-kv"><span class="contract-result-kv-label">关联风险</span>' +
          escapeHtml(titleLine) +
          "</p>";
      }
      html += "</div></details>";
    }
    html += "</article>";
    return html;
  }

  function renderClauseSeverityOverview(items) {
    var arr = safeArray(items).slice();
    if (arr.length === 0) {
      return paragraphOrMuted("", "暂无条款严重度条目");
    }
    arr.sort(function (a, b) {
      var ka = severitySortKey(safeStr(a.highest_severity));
      var kb = severitySortKey(safeStr(b.highest_severity));
      if (ka !== kb) return ka - kb;
      var sa = parseFloat(a.severity_score);
      var sb = parseFloat(b.severity_score);
      if (!isNaN(sa) && !isNaN(sb) && sa !== sb) return sb - sa;
      return 0;
    });
    var n2 = arr.length;
    var batch2 = CONTRACT_RESULT_CLAUSE_BATCH;
    if (n2 <= batch2) {
      var h = '<div class="contract-result-subcard-stack">';
      for (var i = 0; i < n2; i++) {
        h += buildClauseSeverityArticle(
          arr[i] && typeof arr[i] === "object" ? arr[i] : {},
          i
        );
      }
      h += "</div>";
      return h;
    }
    var html2 =
      '<div class="contract-result-more-host"><div class="contract-result-subcard-stack">';
    for (var j = 0; j < batch2; j++) {
      html2 += buildClauseSeverityArticle(
        arr[j] && typeof arr[j] === "object" ? arr[j] : {},
        j
      );
    }
    html2 += '</div><div class="contract-result-more-wrap hidden">';
    for (var k = batch2; k < n2; k++) {
      html2 += buildClauseSeverityArticle(
        arr[k] && typeof arr[k] === "object" ? arr[k] : {},
        k
      );
    }
    html2 += "</div>";
    html2 +=
      '<button type="button" class="contract-result-more-btn">显示其余 ' +
      (n2 - batch2) +
      " 条</button></div>";
    return html2;
  }

  function renderCompleteListSection(items, headingZh) {
    var list = safeArray(items);
    var cap = CONTRACT_RESULT_COMPLETE_LIST_CAP;
    if (list.length === 0) return "";
    var sec =
      '<section class="contract-result-nested-section"><h4 class="contract-result-h4">' +
      escapeHtml(headingZh) +
      "</h4>";
    if (list.length <= cap) {
      sec += '<ul class="contract-result-list contract-result-list--spaced">';
      for (var i = 0; i < list.length; i++) {
        sec += "<li>" + escapeHtml(safeStr(list[i])) + "</li>";
      }
      sec += "</ul></section>";
      return sec;
    }
    sec += '<ul class="contract-result-list contract-result-list--spaced">';
    for (var j = 0; j < cap; j++) {
      sec += "<li>" + escapeHtml(safeStr(list[j])) + "</li>";
    }
    sec += "</ul>";
    sec += '<div class="contract-result-more-host">';
    sec += '<div class="contract-result-more-wrap hidden"><ul class="contract-result-list contract-result-list--spaced">';
    for (var k = cap; k < list.length; k++) {
      sec += "<li>" + escapeHtml(safeStr(list[k])) + "</li>";
    }
    sec += "</ul></div>";
    sec +=
      '<button type="button" class="contract-result-more-btn">显示其余 ' +
      (list.length - cap) +
      " 项</button>";
    sec += "</div></section>";
    return sec;
  }

  function renderCompletenessOverview(o) {
    o = safeObject(o);
    var status = safeStr(o.overall_status);
    var score = o.completeness_score;
    var shortSum = safeStr(o.short_summary);
    var miss = safeArray(o.missing_core_items);
    var unclear = safeArray(o.unclear_items);
    var hasAny =
      !isEmptyText(status) ||
      score != null ||
      !isEmptyText(shortSum) ||
      miss.length ||
      unclear.length;
    if (!hasAny) {
      return paragraphOrMuted("", "暂无完整性评估数据");
    }
    var html = '<div class="contract-result-complete">';
    if (!isEmptyText(status) || score != null) {
      html += '<div class="contract-result-complete-top">';
      if (!isEmptyText(status)) {
        html +=
          '<span class="contract-result-pill contract-result-pill--status">' +
          escapeHtml(status) +
          "</span>";
      }
      if (score != null) {
        html +=
          '<span class="contract-result-pill contract-result-pill--muted">完整性分 ' +
          escapeHtml(safeStr(score)) +
          "</span>";
      }
      html += "</div>";
    }
    if (!isEmptyText(shortSum)) {
      html +=
        '<p class="contract-result-text contract-result-complete-summary">' +
        escapeHtml(shortSum) +
        "</p>";
    }
    if (miss.length) {
      html += renderCompleteListSection(miss, "缺失核心项");
    }
    if (unclear.length) {
      html += renderCompleteListSection(unclear, "不明确项");
    }
    html += "</div>";
    return html;
  }

  function renderActionAdvice(items) {
    var arr = safeArray(items);
    if (arr.length === 0) {
      return paragraphOrMuted("", "暂无行动建议");
    }
    var html = '<ol class="contract-result-action-list">';
    for (var i = 0; i < arr.length; i++) {
      html +=
        '<li><span class="contract-result-action-index">' +
        (i + 1) +
        "</span>" +
        '<span class="contract-result-action-text">' +
        escapeHtml(safeStr(arr[i])) +
        "</span></li>";
    }
    html += "</ol>";
    return html;
  }

  /** Phase 0 legal_compliance: read from API result (tolerates nesting). */
  function getLegalCompliance(data) {
    if (!data || typeof data !== "object") return null;
    var r = data.result;
    if (r && typeof r === "object" && r.legal_compliance != null) {
      return r.legal_compliance;
    }
    if (data.data && typeof data.data === "object" && data.data.legal_compliance != null) {
      return data.data.legal_compliance;
    }
    return null;
  }

  function normalizeRulesList(v) {
    return Array.isArray(v) ? v : [];
  }

  function normalizeStringArray(v) {
    if (!Array.isArray(v)) return [];
    var out = [];
    for (var i = 0; i < v.length; i++) {
      var s = safeStr(v[i]).trim();
      if (s) out.push(s);
    }
    return out;
  }

  function formatConfidence(value) {
    if (value == null || value === "") return "";
    var n = Number(value);
    if (isNaN(n)) return "";
    if (n >= 0 && n <= 1) return Math.round(n * 100) + "%";
    return safeStr(n);
  }

  function safeLegalObject(v) {
    return v && typeof v === "object" && !Array.isArray(v) ? v : {};
  }

  function renderLegalRuleArticle(rule) {
    var r = rule && typeof rule === "object" ? rule : {};
    var title = safeStr(r.title).trim() || "—";
    var ls = safeStr(r.legal_status).trim();
    var rl = safeStr(r.risk_level).trim();
    var exp = safeStr(r.explanation_plain).trim();
    var reds = normalizeStringArray(r.matched_red_flags);
    var kps = normalizeStringArray(r.matched_key_points);
    var conf = formatConfidence(r.confidence);
    var html =
      '<article class="contract-result-subcard legal-rule-card">' +
      '<div class="contract-result-subcard-head">' +
      "<strong>" +
      escapeHtml(title) +
      "</strong>";
    html += '<div class="contract-result-subcard-badges">';
    if (ls) {
      html +=
        '<span class="contract-result-pill contract-result-pill--muted">' +
        escapeHtml(ls) +
        "</span>";
    }
    if (rl) {
      html +=
        '<span class="contract-result-pill contract-result-pill--severity">' +
        escapeHtml(rl) +
        "</span>";
    }
    html += "</div></div>";
    if (exp) {
      html +=
        '<p class="contract-result-text">' +
        escapeHtml(exp).replace(/\n/g, "<br/>") +
        "</p>";
    }
    if (reds.length) {
      html +=
        '<section class="legal-rule-card__section" aria-label="Red flags">' +
        '<h4 class="legal-rule-card__section-title">Red flags</h4>' +
        '<ul class="contract-result-list contract-result-list--spaced">';
      for (var ri = 0; ri < reds.length; ri++) {
        html += "<li>" + escapeHtml(reds[ri]) + "</li>";
      }
      html += "</ul></section>";
    }
    if (kps.length) {
      html +=
        '<section class="legal-rule-card__section" aria-label="Key points">' +
        '<h4 class="legal-rule-card__section-title">Key points</h4>' +
        '<ul class="contract-result-list contract-result-list--spaced">';
      for (var ki = 0; ki < kps.length; ki++) {
        html += "<li>" + escapeHtml(kps[ki]) + "</li>";
      }
      html += "</ul></section>";
    }
    if (conf) {
      html +=
        '<p class="contract-result-muted">' +
        '<span class="contract-result-quick-label">Confidence</span> ' +
        escapeHtml(conf) +
        "</p>";
    }
    html += "</article>";
    return html;
  }

  function renderLegalComplianceInner(lc) {
    if (lc == null || typeof lc !== "object") {
      return (
        '<p class="contract-result-muted">' +
        escapeHtml("No detailed legal compliance result is available yet.") +
        "</p>"
      );
    }
    var ov = safeLegalObject(lc.overall);
    var rules = normalizeRulesList(lc.rules);
    var status = safeStr(ov.overall_legal_status).trim();
    var risk = safeStr(ov.overall_risk_level).trim();
    var summary = safeStr(ov.summary_plain).trim();
    var disclaimer = safeStr(ov.disclaimer).trim();
    var showOverall = !!(status || risk || summary);
    var html = "";
    if (showOverall) {
      html += '<div class="legal-compliance-overall">';
      if (status) {
        html +=
          '<p class="contract-result-kv"><span class="contract-result-kv-label">Overall legal status</span>' +
          escapeHtml(status) +
          "</p>";
      }
      if (risk) {
        html +=
          '<p class="contract-result-kv"><span class="contract-result-kv-label">Overall risk level</span>' +
          escapeHtml(risk) +
          "</p>";
      }
      if (summary) {
        html +=
          '<p class="contract-result-text">' +
          escapeHtml(summary).replace(/\n/g, "<br/>") +
          "</p>";
      }
      html += "</div>";
    }
    if (disclaimer) {
      html +=
        '<div class="legal-compliance-disclaimer" role="note">' +
        escapeHtml(disclaimer).replace(/\n/g, "<br/>") +
        "</div>";
    }
    if (rules.length === 0) {
      html +=
        '<p class="contract-result-muted legal-compliance-empty-hint">' +
        escapeHtml("No detailed legal compliance result is available yet.") +
        "</p>";
    } else {
      html += '<div class="contract-result-subcard-stack legal-compliance-rules">';
      for (var i = 0; i < rules.length; i++) {
        html += renderLegalRuleArticle(rules[i] && typeof rules[i] === "object" ? rules[i] : {});
      }
      html += "</div>";
    }
    return html;
  }

  function renderSummary(data) {
    if (!resultBody) return;
    var res = (data && data.result) || {};
    var sv = safeObject(res.summary_view);
    var parts = [];

    var ocTier = inferOverallConclusionTier(sv.overall_conclusion);
    parts.push(
      wrapBlock(
        "overall-conclusion",
        "Overall Conclusion",
        "总体结论",
        renderOverallConclusionHtml(sv.overall_conclusion, ocTier),
        { tier: ocTier }
      )
    );
    parts.push(
      wrapBlock(
        "key-risk-summary",
        "Key Risk Summary",
        "核心风险摘要",
        paragraphOrMuted(sv.key_risk_summary, "暂无核心风险摘要")
      )
    );
    parts.push(
      wrapBlock(
        "risk-category-summary",
        "Risk Category Summary",
        "风险分类汇总",
        renderRiskCategorySummary(sv.risk_category_summary)
      )
    );
    parts.push(
      wrapBlock(
        "legal-compliance",
        "Legal Compliance Check",
        "法律合规检查",
        renderLegalComplianceInner(getLegalCompliance(data)),
        {}
      )
    );
    parts.push(
      wrapBlock(
        "highlighted-risk-clauses",
        "Highlighted Risk Clauses",
        "高亮风险条款",
        renderHighlightedClauses(sv.highlighted_risk_clauses)
      )
    );
    parts.push(
      wrapBlock(
        "top-risky-clauses",
        "Top Risky Clauses",
        "优先关注条款",
        renderClauseSeverityOverview(sv.clause_severity_overview)
      )
    );
    parts.push(
      wrapBlock(
        "contract-completeness",
        "Contract Completeness Check",
        "合同完整性",
        renderCompletenessOverview(sv.contract_completeness_overview)
      )
    );
    parts.push(
      wrapBlock(
        "action-advice",
        "Action Advice",
        "行动建议",
        renderActionAdvice(sv.action_advice)
      )
    );

    resultBody.innerHTML = parts.join("");
  }

  function tryRestoreLastResult() {
    if (!CA.readLastContractAnalysisResult) return;
    var data = CA.readLastContractAnalysisResult();
    if (!data || data.ok !== true) return;
    renderSummary(data);
    if (CA.readLastContractAnalysisSource) {
      renderSourceHint(CA.readLastContractAnalysisSource());
    }
    if (emptyEl) emptyEl.classList.add("hidden");
    if (resultSection) resultSection.classList.remove("hidden");
  }

  btn.addEventListener("click", function () {
    setError("");
    var isFile = modeFile && modeFile.checked;

    function run(apiPromise, loadingMessage, sourceMeta) {
      setLoading(true, loadingMessage);
      setError("");
      setContractPersistHint("", null);
      if (resultBody) resultBody.innerHTML = "";
      renderSourceHint(null);
      apiPromise
        .then(function (data) {
          try {
            CA.saveLastContractAnalysisResult(data, sourceMeta);
          } catch (e) {}
          try {
            if (
              window.RentalAIAnalysisHistoryPersist &&
              typeof window.RentalAIAnalysisHistoryPersist.persistAnalysisResult === "function"
            ) {
              var prC = window.RentalAIAnalysisHistoryPersist.persistAnalysisResult({
                kind: "contract",
                data: data,
                sourceMeta: sourceMeta,
              });
              if (prC && prC.hint) {
                setContractPersistHint(prC.hint, contractPersistHintVariant(prC));
              } else {
                setContractPersistHint("", null);
              }
            } else if (
              window.RentalAIAnalysisHistoryStore &&
              typeof window.RentalAIAnalysisHistoryStore.pushContractFromContractData === "function"
            ) {
              window.RentalAIAnalysisHistoryStore.pushContractFromContractData(data, sourceMeta);
              setContractPersistHint("", null);
            }
          } catch (eHist) {}
          renderSummary(data);
          renderSourceHint(sourceMeta);
          setLoading(false);
          if (emptyEl) emptyEl.classList.add("hidden");
          if (resultSection) resultSection.classList.remove("hidden");
        })
        .catch(function (e) {
          setLoading(false);
          if (emptyEl) emptyEl.classList.remove("hidden");
          setError(e && e.message ? e.message : String(e));
        });
    }

    if (!isFile) {
      var text = (ta && ta.value) ? ta.value.trim() : "";
      if (!text) {
        setError("请先粘贴 contract_text（合同正文不能为空）。");
        if (emptyEl) emptyEl.classList.remove("hidden");
        if (resultSection) resultSection.classList.add("hidden");
        return;
      }
      run(
        CA.analyzeContractText(text, {
          source_name: "contract-analysis-web",
          source_type: "text",
        }),
        "分析中…",
        { kind: "text", label: "" }
      );
      return;
    }

    var pathRaw = filePathInput ? filePathInput.value.trim() : "";
    var up = uploadFile && uploadFile.files && uploadFile.files[0];

    if (up) {
      var uploadErr = validateUploadFile(up);
      if (uploadErr) {
        setError(uploadErr);
        if (emptyEl) emptyEl.classList.remove("hidden");
        if (resultSection) resultSection.classList.add("hidden");
        return;
      }
      run(
        CA.analyzeContractUpload(up, {
          source_name: up.name || "upload",
        }),
        "上传并分析中…",
        { kind: "upload", label: up.name || "" }
      );
      return;
    }

    if (pathRaw) {
      run(
        CA.analyzeContractFile(pathRaw, {
          source_name: "contract-analysis-web-path",
        }),
        "分析中…",
        { kind: "path", label: pathRaw }
      );
      return;
    }

    setError("请先选择要上传的合同文件，或展开「开发：服务端路径」填写 file_path。");
  });

  function initContractResultMoreButtons() {
    if (!resultBody) return;
    if (resultBody.getAttribute("data-contract-more-bound") === "1") return;
    resultBody.setAttribute("data-contract-more-bound", "1");
    resultBody.addEventListener("click", function (ev) {
      var t = ev.target;
      if (!t || !t.closest) return;
      var btn = t.closest(".contract-result-more-btn");
      if (!btn) return;
      ev.preventDefault();
      var host = btn.closest(".contract-result-more-host");
      if (!host) return;
      var wrap = host.querySelector(".contract-result-more-wrap");
      if (wrap) wrap.classList.remove("hidden");
      btn.style.display = "none";
    });
  }

  initContractResultMoreButtons();

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", tryRestoreLastResult);
  } else {
    tryRestoreLastResult();
  }
})();
