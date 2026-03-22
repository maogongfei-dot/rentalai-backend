/**
 * P10 Phase3 Step2 — 结果页展示适配层（不触碰后端分析逻辑）。
 * 从 GET /tasks/{id} 响应构建 normalized 的 display_payload，并写入 DOM。
 */
(function (global) {
  var VERDICT_LABELS = {
    recommended: "Recommended",
    not_recommended: "Not Recommended",
    uncertain: "Caution",
    "n/a": "N/A",
    na: "N/A",
  };

  /** 将 pros/cons/risk 等统一为 string[]；支持 string（含换行）、单值、数组。 */
  function normalizeStrList(x) {
    if (x == null) return [];
    if (Array.isArray(x)) {
      return x
        .map(function (z) {
          return String(z).trim();
        })
        .filter(Boolean);
    }
    if (typeof x === "string") {
      var t = x.trim();
      if (!t) return [];
      if (t.indexOf("\n") >= 0) {
        return t
          .split(/\n+/)
          .map(function (s) {
            return s.trim().replace(/^[-•*\d.)]+\s*/, "");
          })
          .filter(Boolean);
      }
      return [t];
    }
    if (typeof x === "object") return [];
    return [String(x)];
  }

  function dedupeStrings(arr) {
    var seen = {};
    var out = [];
    (arr || []).forEach(function (s) {
      var k = String(s)
        .trim()
        .toLowerCase();
      if (!k || seen[k]) return;
      seen[k] = 1;
      out.push(String(s).trim());
    });
    return out;
  }

  function firstNumber() {
    for (var i = 0; i < arguments.length; i++) {
      var v = arguments[i];
      if (v == null || v === "") continue;
      var n = Number(v);
      if (!isNaN(n) && isFinite(n)) return n;
    }
    return null;
  }

  function formatScore(n) {
    if (n == null) return null;
    var x = Number(n);
    if (isNaN(x) || !isFinite(x)) return null;
    return Math.abs(x - Math.round(x)) < 1e-9 ? String(Math.round(x)) : String(Math.round(x * 10) / 10);
  }

  function verdictKeyFromRow(row) {
    row = row && typeof row === "object" ? row : {};
    var code = row.decision_code;
    if (code != null && String(code).trim()) {
      return String(code).trim().toLowerCase().replace(/\s+/g, "_");
    }
    var label = row.decision_label || row.decision_summary;
    if (label != null && String(label).trim()) {
      var low = String(label).toLowerCase();
      if (low.indexOf("not recommend") >= 0 || low.indexOf("avoid") >= 0) return "not_recommended";
      if (low.indexOf("recommend") >= 0 || low.indexOf("proceed") >= 0) return "recommended";
      if (low !== "n/a" && low) return "uncertain";
    }
    return "n/a";
  }

  function verdictDisplay(key) {
    var k = (key || "n/a").toLowerCase();
    return VERDICT_LABELS[k] || VERDICT_LABELS[k.replace(/-/g, "_")] || "N/A";
  }

  function analysisStatusLabel(taskStatus, degraded) {
    var s = (taskStatus || "").toLowerCase();
    if (s === "failed" || s === "timeout" || s === "interrupted") return "failed";
    if (s === "degraded" || degraded) return "completed (degraded)";
    if (s === "success") return "completed";
    return s || "unknown";
  }

  /**
   * @param {object} taskState — GET /tasks/{task_id} 完整 JSON
   * @returns {{ display_payload: object, phase: string, errorMessage?: string }}
   */
  function buildResultViewModel(taskState) {
    var st = taskState && typeof taskState === "object" ? taskState : {};
    var phase = "loading";
    var errMsg = "";

    var ts = String(st.status || "").toLowerCase();
    if (ts === "failed" || ts === "timeout" || ts === "interrupted") {
      phase = "failed";
      errMsg = st.error || st.last_error_at || ts || "Unknown error";
    } else if (ts === "success" || ts === "degraded") {
      phase = "ready";
    } else {
      phase = "loading";
    }

    var result = st.result && typeof st.result === "object" ? st.result : {};
    var row = result.representative_row || result.sample_analyzed_listing || {};
    if (typeof row !== "object" || row === null) row = {};
    var im = row.input_meta && typeof row.input_meta === "object" ? row.input_meta : {};
    var ex = result.p10_explain && typeof result.p10_explain === "object" ? result.p10_explain : {};

    var vKey = verdictKeyFromRow(row);
    var scoreNum = firstNumber(row.score, row.final_score, row.property_score);
    var scoreStr = formatScore(scoreNum);

    var pros = dedupeStrings(
      normalizeStrList(ex.pros).concat(normalizeStrList(row.recommended_reasons))
    );
    var cons = dedupeStrings(
      normalizeStrList(ex.cons).concat(normalizeStrList(row.concerns))
    );

    var summary =
      (ex.explain_summary && String(ex.explain_summary).trim()) ||
      (row.decision_summary && String(row.decision_summary).trim()) ||
      (row.decision_label && String(row.decision_label).trim()) ||
      "";

    var riskFromExplain = normalizeStrList(ex.risk_flags);
    var riskFromRow = normalizeStrList(row.risks);
    var riskFlags = dedupeStrings(riskFromExplain.concat(riskFromRow));

    var dec = row.decision && typeof row.decision === "object" ? row.decision : {};
    var severity = null;
    if (dec.risk_signal != null && String(dec.risk_signal).trim()) {
      severity = String(dec.risk_signal).trim();
    } else if (dec.risk_level != null && String(dec.risk_level).trim()) {
      severity = String(dec.risk_level).trim();
    }

    var nextSteps = dedupeStrings(normalizeStrList(row.next_steps));

    var analysis = row.analysis && typeof row.analysis === "object" ? row.analysis : {};
    if (!nextSteps.length && analysis.recommended_inputs_to_improve_decision) {
      nextSteps = dedupeStrings(normalizeStrList(analysis.recommended_inputs_to_improve_decision));
    }
    if (!nextSteps.length && analysis.required_actions_before_proceeding) {
      nextSteps = dedupeStrings(normalizeStrList(analysis.required_actions_before_proceeding));
    }

    var hasRiskSignal =
      riskFlags.length > 0 ||
      (severity &&
        String(severity).trim() &&
        String(severity).trim().toLowerCase() !== "n/a");

    var property = {
      title: im.title || row.title || null,
      price:
        firstNumber(im.rent, row.rent_pcm, row.rent, row.price) != null
          ? String(firstNumber(im.rent, row.rent_pcm, row.rent, row.price))
          : null,
      postcode: im.postcode || im.area || row.postcode || null,
      bedrooms:
        im.bedrooms != null && String(im.bedrooms).trim()
          ? String(im.bedrooms)
          : row.bedrooms != null && String(row.bedrooms).trim()
            ? String(row.bedrooms)
            : null,
      bills:
        im.bills_included === true
          ? "Included"
          : im.bills_included === false
            ? "Not included"
            : null,
      listingUrl: im.source_url || row.listing_url || row.source_url || null,
    };

    var display_payload = {
      version: 1,
      task_id: st.task_id || null,
      task_status: st.status || null,
      header: {
        verdict_key: vKey,
        verdict_label: verdictDisplay(vKey),
        final_score: scoreStr,
        analysis_status: analysisStatusLabel(st.status, st.degraded),
        degraded: Boolean(st.degraded),
      },
      property: property,
      explain: {
        summary: summary || null,
        pros: pros,
        cons: cons,
      },
      risk: {
        risk_flags: riskFlags,
        severity: severity,
        next_steps: nextSteps,
        show_no_flags_message: !hasRiskSignal,
      },
      meta: {
        elapsed_seconds: st.elapsed_seconds != null ? st.elapsed_seconds : null,
        stage: st.stage || null,
        batch_row_index: row.index != null ? row.index : null,
      },
    };

    return {
      phase: phase,
      errorMessage: errMsg,
      display_payload: display_payload,
      raw_task_state: st,
    };
  }

  function setText(id, text) {
    var el = document.getElementById(id);
    if (el) el.textContent = text == null ? "" : String(text);
  }

  function showEl(id, on) {
    var el = document.getElementById(id);
    if (!el) return;
    if (on) el.classList.remove("hidden");
    else el.classList.add("hidden");
  }

  function fillUl(ulId, items, emptyPlaceholder) {
    var ul = document.getElementById(ulId);
    if (!ul) return;
    ul.innerHTML = "";
    var arr = Array.isArray(items) ? items : [];
    if (!arr.length) {
      if (emptyPlaceholder != null) {
        var li0 = document.createElement("li");
        li0.textContent = emptyPlaceholder;
        li0.className = "muted";
        ul.appendChild(li0);
      }
      return;
    }
    arr.forEach(function (t) {
      var li = document.createElement("li");
      li.textContent = String(t);
      ul.appendChild(li);
    });
  }

  function setListingUrl(anchorId, wrapId, href) {
    var wrap = document.getElementById(wrapId);
    var a = document.getElementById(anchorId);
    if (!wrap || !a) return;
    if (!href || !String(href).trim()) {
      wrap.classList.add("hidden");
      return;
    }
    wrap.classList.remove("hidden");
    a.href = href;
    a.textContent = "Open listing";
  }

  function setRow(rowId, value) {
    var row = document.getElementById(rowId);
    if (!row) return;
    if (value == null || String(value).trim() === "") {
      row.classList.add("hidden");
      return;
    }
    row.classList.remove("hidden");
    var span = row.querySelector("[data-value]");
    if (span) span.textContent = String(value);
  }

  /**
   * 根据 buildResultViewModel 输出切换面板并填充内容。
   */
  function renderFromViewModel(vm) {
    var dbgPre = document.getElementById("debug-json");
    var dbgDetails = document.getElementById("debug-details");

    if (!vm || vm.phase === "loading") {
      showEl("loading-panel", true);
      showEl("failed-panel", false);
      showEl("result-panel", false);
      if (dbgDetails) dbgDetails.classList.add("hidden");
      return;
    }

    if (vm.phase === "failed") {
      showEl("loading-panel", false);
      showEl("failed-panel", true);
      showEl("result-panel", false);
      setText("failed-title", "Analysis failed");
      setText("failed-sub", "Please try again.");
      var shortErr = vm.errorMessage ? String(vm.errorMessage).slice(0, 280) : "";
      setText("failed-detail", shortErr);
      showEl("failed-detail-wrap", Boolean(shortErr));
      if (dbgPre && vm.raw_task_state) {
        try {
          dbgPre.textContent = JSON.stringify(vm.raw_task_state, null, 2);
        } catch (e) {
          dbgPre.textContent = String(e);
        }
      }
      if (dbgDetails) dbgDetails.classList.remove("hidden");
      return;
    }

    showEl("loading-panel", false);
    showEl("failed-panel", false);
    showEl("result-panel", true);

    var p = vm.display_payload || {};
    var h = p.header || {};
    var prop = p.property || {};
    var ex = p.explain || {};
    var rk = p.risk || {};
    var meta = p.meta || {};

    setText("hdr-verdict", h.verdict_label || "N/A");
    setText("hdr-score", h.final_score != null ? h.final_score : "N/A");
    setText("hdr-task-id", p.task_id || "—");
    setText("hdr-status", h.analysis_status || "—");
    if (meta.elapsed_seconds != null && document.getElementById("hdr-elapsed")) {
      setText("hdr-elapsed", "Elapsed: " + String(meta.elapsed_seconds) + "s");
      showEl("hdr-elapsed-wrap", true);
    } else {
      showEl("hdr-elapsed-wrap", false);
    }

    setRow("prop-title", prop.title);
    setRow("prop-price", prop.price != null ? prop.price : null);
    setRow("prop-postcode", prop.postcode);
    setRow("prop-bedrooms", prop.bedrooms);
    setRow("prop-bills", prop.bills);
    setListingUrl("prop-url", "prop-url-wrap", prop.listingUrl);

    var hasAnyProp =
      prop.title ||
      prop.price ||
      prop.postcode ||
      prop.bedrooms ||
      prop.bills ||
      prop.listingUrl;
    showEl("sec-property", Boolean(hasAnyProp));

    setText("ex-summary", ex.summary || "N/A");
    fillUl("ex-pros", ex.pros, "N/A");
    fillUl("ex-cons", ex.cons, "N/A");

    showEl("risk-no-flags", Boolean(rk.show_no_flags_message));
    showEl("risk-has-flags", !rk.show_no_flags_message);
    fillUl("risk-flags-ul", rk.show_no_flags_message ? [] : rk.risk_flags, null);

    if (rk.severity) {
      setText("risk-severity", rk.severity);
      showEl("risk-severity-row", true);
    } else {
      showEl("risk-severity-row", false);
    }

    if (rk.next_steps && rk.next_steps.length) {
      fillUl("risk-next-ul", rk.next_steps, null);
      showEl("risk-next-block", true);
    } else {
      showEl("risk-next-block", false);
    }

    if (dbgPre && vm.raw_task_state) {
      try {
        dbgPre.textContent = JSON.stringify(vm.raw_task_state, null, 2);
      } catch (e2) {
        dbgPre.textContent = String(e2);
      }
    }
    if (dbgDetails) dbgDetails.classList.remove("hidden");

    try {
      global.__rentalaiLastDisplayPayload = p;
    } catch (e3) {}
  }

  global.RentalAIResultView = {
    buildResultViewModel: buildResultViewModel,
    renderFromViewModel: renderFromViewModel,
  };
})(window);
