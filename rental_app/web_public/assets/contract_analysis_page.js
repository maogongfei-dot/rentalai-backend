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
   */
  function wrapBlock(slug, en, zh, inner) {
    return (
      '<article class="contract-result-card-block" data-contract-block="' +
      escapeHtml(slug) +
      '">' +
      '<header class="contract-result-card-head">' +
      blockTitle(en, zh) +
      "</header>" +
      '<div class="contract-result-card-body">' +
      inner +
      "</div>" +
      "</article>"
    );
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
    var arr = safeArray(items);
    if (arr.length === 0) {
      return paragraphOrMuted("", "暂无分类汇总");
    }
    var html = '<ul class="contract-result-rich-list contract-result-risk-cat-list">';
    for (var i = 0; i < arr.length; i++) {
      var it = arr[i] && typeof arr[i] === "object" ? arr[i] : {};
      var cat = safeStr(it.category) || "（未命名类别）";
      var cnt = it.count != null ? safeStr(it.count) : "—";
      var hi = safeStr(it.highest_severity);
      var sum = safeStr(it.short_summary);
      html += '<li class="contract-result-rich-item">';
      html += '<div class="contract-result-rich-row">';
      html += '<span class="contract-result-rich-title">' + escapeHtml(cat) + "</span>";
      html += '<span class="contract-result-rich-meta">';
      html +=
        '<span class="contract-result-pill contract-result-pill--muted">条数 ' +
        escapeHtml(cnt) +
        "</span>";
      if (hi) {
        html +=
          '<span class="contract-result-pill contract-result-pill--severity">' +
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

  function renderHighlightedClauses(items) {
    var arr = safeArray(items);
    if (arr.length === 0) {
      return paragraphOrMuted("", "暂无高亮风险条款");
    }
    var html = '<div class="contract-result-subcard-stack">';
    for (var i = 0; i < arr.length; i++) {
      var it = arr[i] && typeof arr[i] === "object" ? arr[i] : {};
      var title = safeStr(it.risk_title) || "（无标题）";
      var sev = safeStr(it.severity);
      var cat = safeStr(it.risk_category);
      var mt = safeStr(it.matched_text);
      var adv = safeStr(it.short_advice);
      var loc = safeStr(it.location_hint);
      html += '<article class="contract-result-subcard">';
      html += '<div class="contract-result-subcard-head">';
      html += "<strong>" + escapeHtml(title) + "</strong>";
      if (sev || cat) {
        html += '<div class="contract-result-subcard-badges">';
        if (sev) {
          html +=
            '<span class="contract-result-pill contract-result-pill--severity">' +
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
      if (!isEmptyText(mt)) {
        html +=
          '<p class="contract-result-kv"><span class="contract-result-kv-label">摘录</span>' +
          escapeHtml(mt) +
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
          '<p class="contract-result-kv"><span class="contract-result-kv-label">位置</span>' +
          escapeHtml(loc) +
          "</p>";
      }
      html += "</article>";
    }
    html += "</div>";
    return html;
  }

  function renderClauseSeverityOverview(items) {
    var arr = safeArray(items);
    if (arr.length === 0) {
      return paragraphOrMuted("", "暂无条款严重度条目");
    }
    var html = '<div class="contract-result-subcard-stack">';
    for (var i = 0; i < arr.length; i++) {
      var it = arr[i] && typeof arr[i] === "object" ? arr[i] : {};
      var cid = safeStr(it.clause_id);
      var ctype = safeStr(it.clause_type);
      var score = it.severity_score != null ? safeStr(it.severity_score) : "—";
      var hi = safeStr(it.highest_severity);
      var cnt = it.linked_risk_count != null ? safeStr(it.linked_risk_count) : "—";
      var prev = safeStr(it.short_clause_preview);
      var titles = safeArray(it.linked_risk_titles);
      var titleLine = titles.length ? titles.join("；") : "";
      html += '<article class="contract-result-subcard">';
      html += '<div class="contract-result-subcard-head">';
      html +=
        "<strong>" +
        escapeHtml((cid || "条款") + (ctype ? " · " + ctype : "")) +
        "</strong>";
      html += "</div>";
      html += '<dl class="contract-result-dl">';
      html += "<dt>强度分</dt><dd>" + escapeHtml(score) + "</dd>";
      html += "<dt>最高严重度</dt><dd>" + escapeHtml(hi || "—") + "</dd>";
      html += "<dt>关联风险数</dt><dd>" + escapeHtml(cnt) + "</dd>";
      html += "</dl>";
      if (!isEmptyText(prev)) {
        html +=
          '<p class="contract-result-kv contract-result-kv--preview">' +
          escapeHtml(prev) +
          "</p>";
      }
      if (!isEmptyText(titleLine)) {
        html +=
          '<p class="contract-result-kv"><span class="contract-result-kv-label">关联风险</span>' +
          escapeHtml(titleLine) +
          "</p>";
      }
      html += "</article>";
    }
    html += "</div>";
    return html;
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
      html += '<section class="contract-result-nested-section">';
      html +=
        '<h4 class="contract-result-h4">缺失核心项</h4><ul class="contract-result-list contract-result-list--spaced">';
      for (var i = 0; i < miss.length; i++) {
        html += "<li>" + escapeHtml(safeStr(miss[i])) + "</li>";
      }
      html += "</ul></section>";
    }
    if (unclear.length) {
      html += '<section class="contract-result-nested-section">';
      html +=
        '<h4 class="contract-result-h4">不明确项</h4><ul class="contract-result-list contract-result-list--spaced">';
      for (var j = 0; j < unclear.length; j++) {
        html += "<li>" + escapeHtml(safeStr(unclear[j])) + "</li>";
      }
      html += "</ul></section>";
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

  function renderSummary(data) {
    if (!resultBody) return;
    var res = (data && data.result) || {};
    var sv = safeObject(res.summary_view);
    var parts = [];

    parts.push(
      wrapBlock(
        "overall-conclusion",
        "Overall Conclusion",
        "总体结论",
        paragraphOrMuted(sv.overall_conclusion, "暂无总体结论")
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
      if (resultBody) resultBody.innerHTML = "";
      renderSourceHint(null);
      apiPromise
        .then(function (data) {
          try {
            CA.saveLastContractAnalysisResult(data, sourceMeta);
          } catch (e) {}
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

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", tryRestoreLastResult);
  } else {
    tryRestoreLastResult();
  }
})();
