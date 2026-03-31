/**
 * Phase 4 合同分析页：表单 UI + summary_view 分段展示（逻辑见 contract_analysis_api.js）。
 */
(function () {
  var CA = window.RentalAIContractAnalysis;
  if (!CA || typeof CA.analyzeContractText !== "function") {
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
  var localFile = document.getElementById("contract-local-file");
  var localHint = document.getElementById("contract-local-file-hint");
  var btn = document.getElementById("contract-submit");
  var loadingEl = document.getElementById("contract-loading");
  var loadingText = document.getElementById("contract-loading-text");
  var errEl = document.getElementById("contract-error");
  var emptyEl = document.getElementById("contract-state-empty");
  var resultSection = document.getElementById("contract-state-result");
  var resultBody = document.getElementById("contract-result-body");

  if (!btn || !ta) return;

  function setModePanels() {
    var file = modeFile && modeFile.checked;
    if (panelText) panelText.classList.toggle("hidden", file);
    if (panelFile) panelFile.classList.toggle("hidden", !file);
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
    if (localFile) localFile.value = "";
    if (localHint) localHint.textContent = "";
    setError("");
  }

  function fillSamplePath() {
    if (!Demo) return;
    if (modeFile) modeFile.checked = true;
    setModePanels();
    if (filePathInput) filePathInput.value = Demo.SAMPLE_FILE_PATH;
    if (localFile) localFile.value = "";
    if (localHint) localHint.textContent = "";
    setError("");
  }

  if (btnDemoText && Demo) btnDemoText.addEventListener("click", fillSampleText);
  if (btnDemoPath && Demo) btnDemoPath.addEventListener("click", fillSamplePath);

  if (localFile && localHint) {
    localFile.addEventListener("change", function () {
      var f = localFile.files && localFile.files[0];
      localHint.textContent = f ? "已选择：" + f.name + "（" + (f.type || "未知类型") + "）" : "";
    });
  }

  function setLoading(on) {
    if (btn) btn.disabled = !!on;
    if (loadingEl) {
      loadingEl.classList.toggle("hidden", !on);
      loadingEl.setAttribute("aria-busy", on ? "true" : "false");
    }
    if (loadingText) loadingText.textContent = on ? "分析中…" : "";
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
      escapeHtml(en) +
      ' <span class="contract-result-block-sub">' +
      escapeHtml(zh) +
      "</span></h3>"
    );
  }

  function wrapBlock(en, zh, inner) {
    return (
      '<section class="contract-result-block">' + blockTitle(en, zh) + inner + "</section>"
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
    var html = '<ul class="contract-result-list">';
    for (var i = 0; i < arr.length; i++) {
      var it = arr[i] && typeof arr[i] === "object" ? arr[i] : {};
      var cat = safeStr(it.category);
      var cnt = it.count != null ? safeStr(it.count) : "—";
      var hi = safeStr(it.highest_severity);
      var sum = safeStr(it.short_summary);
      var line =
        (cat || "（未命名类别）") +
        " · 条数 " +
        cnt +
        (hi ? " · 最高 " + hi : "") +
        (sum ? " — " + sum : "");
      html += "<li>" + escapeHtml(line) + "</li>";
    }
    html += "</ul>";
    return html;
  }

  function renderHighlightedClauses(items) {
    var arr = safeArray(items);
    if (arr.length === 0) {
      return paragraphOrMuted("", "暂无高亮风险条款");
    }
    var html = "";
    for (var i = 0; i < arr.length; i++) {
      var it = arr[i] && typeof arr[i] === "object" ? arr[i] : {};
      var title = safeStr(it.risk_title) || "（无标题）";
      var sev = safeStr(it.severity);
      var cat = safeStr(it.risk_category);
      var mt = safeStr(it.matched_text);
      var adv = safeStr(it.short_advice);
      var loc = safeStr(it.location_hint);
      html += '<div class="contract-result-card">';
      html += "<strong>" + escapeHtml(title) + "</strong>";
      if (sev || cat) {
        html +=
          '<p class="contract-result-kv">' +
          escapeHtml([sev && "严重度: " + sev, cat && "类别: " + cat].filter(Boolean).join(" · ")) +
          "</p>";
      }
      if (!isEmptyText(mt)) {
        html +=
          '<p class="contract-result-kv"><span class="hint">摘录：</span>' +
          escapeHtml(mt) +
          "</p>";
      }
      if (!isEmptyText(adv)) {
        html += '<p class="contract-result-kv">' + escapeHtml(adv) + "</p>";
      }
      if (!isEmptyText(loc)) {
        html +=
          '<p class="contract-result-kv"><span class="hint">位置：</span>' +
          escapeHtml(loc) +
          "</p>";
      }
      html += "</div>";
    }
    return html;
  }

  function renderClauseSeverityOverview(items) {
    var arr = safeArray(items);
    if (arr.length === 0) {
      return paragraphOrMuted("", "暂无条款严重度条目");
    }
    var html = "";
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
      html += '<div class="contract-result-card">';
      html +=
        "<strong>" +
        escapeHtml((cid || "条款") + (ctype ? " · " + ctype : "")) +
        "</strong>";
      html +=
        '<p class="contract-result-kv">' +
        escapeHtml(
          "强度分 " + score + " · 最高 " + (hi || "—") + " · 关联风险数 " + cnt
        ) +
        "</p>";
      if (!isEmptyText(prev)) {
        html += '<p class="contract-result-kv">' + escapeHtml(prev) + "</p>";
      }
      if (!isEmptyText(titleLine)) {
        html +=
          '<p class="contract-result-kv"><span class="hint">关联风险：</span>' +
          escapeHtml(titleLine) +
          "</p>";
      }
      html += "</div>";
    }
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
    var html = "";
    if (!isEmptyText(status) || score != null) {
      var bits = [];
      if (!isEmptyText(status)) bits.push("状态：" + status);
      if (score != null) bits.push("分数：" + safeStr(score));
      html +=
        '<p class="contract-result-text">' + escapeHtml(bits.join(" · ")) + "</p>";
    }
    if (!isEmptyText(shortSum)) {
      html += paragraphOrMuted(shortSum, "");
    }
    if (miss.length) {
      html += '<p class="contract-result-kv hint">缺失核心项</p><ul class="contract-result-list">';
      for (var i = 0; i < miss.length; i++) {
        html += "<li>" + escapeHtml(safeStr(miss[i])) + "</li>";
      }
      html += "</ul>";
    }
    if (unclear.length) {
      html += '<p class="contract-result-kv hint">不明确项</p><ul class="contract-result-list">';
      for (var j = 0; j < unclear.length; j++) {
        html += "<li>" + escapeHtml(safeStr(unclear[j])) + "</li>";
      }
      html += "</ul>";
    }
    return html;
  }

  function renderActionAdvice(items) {
    var arr = safeArray(items);
    if (arr.length === 0) {
      return paragraphOrMuted("", "暂无行动建议");
    }
    var html = '<ol class="contract-result-list">';
    for (var i = 0; i < arr.length; i++) {
      html += "<li>" + escapeHtml(safeStr(arr[i])) + "</li>";
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
        "Overall Conclusion",
        "总体结论",
        paragraphOrMuted(sv.overall_conclusion, "暂无总体结论")
      )
    );
    parts.push(
      wrapBlock(
        "Key Risk Summary",
        "核心风险摘要",
        paragraphOrMuted(sv.key_risk_summary, "暂无核心风险摘要")
      )
    );
    parts.push(
      wrapBlock(
        "Risk Category Summary",
        "风险分类汇总",
        renderRiskCategorySummary(sv.risk_category_summary)
      )
    );
    parts.push(
      wrapBlock(
        "Highlighted Risk Clauses",
        "高亮风险条款",
        renderHighlightedClauses(sv.highlighted_risk_clauses)
      )
    );
    parts.push(
      wrapBlock(
        "Top Risky Clauses",
        "优先关注条款",
        renderClauseSeverityOverview(sv.clause_severity_overview)
      )
    );
    parts.push(
      wrapBlock(
        "Contract Completeness Check",
        "合同完整性",
        renderCompletenessOverview(sv.contract_completeness_overview)
      )
    );
    parts.push(
      wrapBlock("Action Advice", "行动建议", renderActionAdvice(sv.action_advice))
    );

    resultBody.innerHTML = parts.join("");
  }

  function readFileAsText(file) {
    return new Promise(function (resolve, reject) {
      var fr = new FileReader();
      fr.onload = function () {
        resolve(String(fr.result || ""));
      };
      fr.onerror = function () {
        reject(new Error("读取文件失败"));
      };
      fr.readAsText(file);
    });
  }

  function tryRestoreLastResult() {
    if (!CA.readLastContractAnalysisResult) return;
    var data = CA.readLastContractAnalysisResult();
    if (!data || data.ok !== true) return;
    renderSummary(data);
    if (emptyEl) emptyEl.classList.add("hidden");
    if (resultSection) resultSection.classList.remove("hidden");
  }

  btn.addEventListener("click", function () {
    setError("");
    var isFile = modeFile && modeFile.checked;

    function run(apiPromise) {
      setLoading(true);
      setError("");
      if (resultBody) resultBody.innerHTML = "";
      apiPromise
        .then(function (data) {
          try {
            CA.saveLastContractAnalysisResult(data);
          } catch (e) {}
          renderSummary(data);
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
        })
      );
      return;
    }

    var pathRaw = filePathInput ? filePathInput.value.trim() : "";
    var file = localFile && localFile.files && localFile.files[0];

    if (pathRaw) {
      run(
        CA.analyzeContractFile(pathRaw, {
          source_name: "contract-analysis-web-path",
        })
      );
      return;
    }

    if (file) {
      if (!/\.txt$/i.test(file.name) && file.type && file.type.indexOf("text") === -1) {
        setError("本地文件模式当前仅支持 .txt；其它格式请填写服务端 file_path 或使用文本模式粘贴。");
        return;
      }
      run(
        readFileAsText(file).then(function (txt) {
          var t = (txt || "").trim();
          if (!t) {
            throw new Error("所选文件为空或无法作为文本读取。");
          }
          return CA.analyzeContractText(t, {
            source_name: file.name || "local.txt",
            source_type: "txt",
          });
        })
      );
      return;
    }

    setError("文件模式下请填写 file_path（服务端路径）或选择本地 .txt 文件。");
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", tryRestoreLastResult);
  } else {
    tryRestoreLastResult();
  }
})();
