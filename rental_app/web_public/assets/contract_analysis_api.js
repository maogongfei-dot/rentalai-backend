/**
 * Phase 4：合同分析 API 客户端（与 api_config.js 同源 fetch，无 axios）。
 *
 * - analyzeContractText：POST /api/contract/analysis/text
 * - analyzeContractFile：POST /api/contract/analysis/file-path（服务端可读路径，非 multipart）
 * - analyzeContractUpload：POST /api/contract/analysis/upload（multipart file + 可选 metadata）
 */
(function (global) {
  var LAST_KEY = "rentalai_contract_analysis_last";
  var META_KEY = "rentalai_contract_analysis_source";

  function apiUrl(path) {
    if (typeof global.rentalaiApiUrl === "function") {
      return global.rentalaiApiUrl(path);
    }
    var p = (path || "").trim();
    return p.charAt(0) === "/" ? p : "/" + p;
  }

  function parseJsonBody(r, text) {
    var j = null;
    try {
      j = text ? JSON.parse(text) : {};
    } catch (e) {
      throw new Error("服务器返回非 JSON：" + (text || "").slice(0, 120));
    }
    if (!r.ok) {
      var msg = (j && (j.message || j.error)) || "HTTP " + r.status;
      throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
    }
    if (j && j.ok === false) {
      var m = j.message || j.error || "请求失败";
      throw new Error(typeof m === "string" ? m : JSON.stringify(m));
    }
    return j;
  }

  /**
   * 上传接口：与 ``parseJsonBody`` 相同，但对已知 ``error`` 码补充中文说明（与后端 ``ContractUploadError`` 对齐）。
   */
  function uploadErrorMessageFromPayload(j, status) {
    var code = j && j.error;
    var msg = j && j.message != null ? String(j.message).trim() : "";
    if (msg) return msg;
    var byCode = {
      unsupported_file_type: "不支持的文件类型：仅支持 .txt、.pdf、.docx。",
      empty_file: "上传的文件为空，请选择包含合同内容的文件。",
      empty_filename: "无法识别文件名，请重新选择文件。",
      read_failed: "读取上传文件失败。",
      file_too_large: "文件超过最大允许大小。",
      invalid_metadata: "metadata 格式错误。",
      analyze_failed: "合同分析失败。",
    };
    if (code && byCode[code]) return byCode[code];
    return "上传失败（HTTP " + (status != null ? status : "?") + "）。";
  }

  function parseUploadJsonBody(r, text) {
    var j = null;
    try {
      j = text ? JSON.parse(text) : {};
    } catch (e) {
      throw new Error("服务器返回非 JSON：" + (text || "").slice(0, 120));
    }
    if (!r.ok) {
      throw new Error(uploadErrorMessageFromPayload(j, r.status));
    }
    if (j && j.ok === false) {
      throw new Error(uploadErrorMessageFromPayload(j, r.status));
    }
    return j;
  }

  /**
   * 成功响应轻量归一化：保证 ``result.summary_view`` 与各字段存在，避免 text / upload / file-path
   * 后端细微差异导致渲染端分支判断。
   */
  function normalizeContractAnalysisResponse(j) {
    if (!j || typeof j !== "object") return j;
    if (!j.result || typeof j.result !== "object") {
      j.result = {};
    }
    var r = j.result;
    if (!r.summary_view || typeof r.summary_view !== "object") {
      r.summary_view = {};
    }
    var sv = r.summary_view;
    if (typeof sv.overall_conclusion !== "string") sv.overall_conclusion = "";
    if (typeof sv.key_risk_summary !== "string") sv.key_risk_summary = "";
    if (!Array.isArray(sv.risk_category_summary)) sv.risk_category_summary = [];
    if (!Array.isArray(sv.highlighted_risk_clauses)) sv.highlighted_risk_clauses = [];
    if (!Array.isArray(sv.clause_severity_overview)) sv.clause_severity_overview = [];
    if (!sv.contract_completeness_overview || typeof sv.contract_completeness_overview !== "object") {
      sv.contract_completeness_overview = {};
    }
    if (!Array.isArray(sv.action_advice)) sv.action_advice = [];
    return j;
  }

  function postJson(path, body) {
    var url = apiUrl(path);
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    }).then(function (r) {
      return r.text().then(function (text) {
        return normalizeContractAnalysisResponse(parseJsonBody(r, text));
      });
    });
  }

  /**
   * @param {string} contractText 非空合同正文
   * @param {object} [metadata] 可选，如 source_name、source_type、月租等
   * @returns {Promise<object>} 完整响应 { ok, engine, result }
   */
  function analyzeContractText(contractText, metadata) {
    var body = { contract_text: contractText || "" };
    if (metadata && typeof metadata === "object") {
      body.metadata = metadata;
    }
    return postJson("/api/contract/analysis/text", body);
  }

  /**
   * 按服务端可读路径分析（与后端 analyze_contract_file 一致，浏览器不上传文件体）。
   * @param {string} filePath 非空路径（相对 rental_app 根或绝对路径）
   * @param {object} [metadata]
   * @returns {Promise<object>}
   */
  function analyzeContractFile(filePath, metadata) {
    var body = { file_path: filePath || "" };
    if (metadata && typeof metadata === "object") {
      body.metadata = metadata;
    }
    return postJson("/api/contract/analysis/file-path", body);
  }

  /**
   * multipart/form-data 上传 .txt / .pdf / .docx，字段名 ``file``；可选 ``metadata`` JSON 字符串。
   * @param {File} file 浏览器 File 对象
   * @param {object} [metadata] 可选，将序列化为表单字段 metadata
   * @returns {Promise<object>}
   */
  function analyzeContractUpload(file, metadata) {
    if (!file || typeof file !== "object") {
      return Promise.reject(new Error("请选择有效的文件"));
    }
    var url = apiUrl("/api/contract/analysis/upload");
    var fd = new FormData();
    fd.append("file", file, file.name || "contract.bin");
    if (metadata && typeof metadata === "object" && Object.keys(metadata).length > 0) {
      fd.append("metadata", JSON.stringify(metadata));
    }
    return fetch(url, {
      method: "POST",
      body: fd,
    })
      .then(function (r) {
        return r.text().then(function (text) {
          return normalizeContractAnalysisResponse(parseUploadJsonBody(r, text));
        });
      })
      .catch(function (e) {
        if (e && e.name === "TypeError" && /fetch|Failed to fetch|NetworkError/i.test(String(e))) {
          return Promise.reject(new Error("无法连接服务器，请确认 API 已启动且与页面同源。"));
        }
        return Promise.reject(e);
      });
  }

  /**
   * @param {object} payload 成功响应 JSON
   * @param {object} [sourceMeta] 可选 ``{ kind: 'text'|'upload'|'path', label?: string }``，用于结果区来源提示与恢复
   */
  function saveLastContractAnalysisResult(payload, sourceMeta) {
    try {
      global.sessionStorage.setItem(LAST_KEY, JSON.stringify(payload));
      if (sourceMeta && typeof sourceMeta === "object") {
        global.sessionStorage.setItem(META_KEY, JSON.stringify(sourceMeta));
      } else {
        global.sessionStorage.removeItem(META_KEY);
      }
    } catch (e) {}
  }

  function readLastContractAnalysisResult() {
    try {
      var raw = global.sessionStorage.getItem(LAST_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  }

  function readLastContractAnalysisSource() {
    try {
      var raw = global.sessionStorage.getItem(META_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  }

  global.RentalAIContractAnalysis = {
    analyzeContractText: analyzeContractText,
    /** 服务端路径版「文件」分析（与 multipart 上传无关） */
    analyzeContractFile: analyzeContractFile,
    analyzeContractUpload: analyzeContractUpload,
    saveLastContractAnalysisResult: saveLastContractAnalysisResult,
    readLastContractAnalysisResult: readLastContractAnalysisResult,
    readLastContractAnalysisSource: readLastContractAnalysisSource,
    LAST_RESULT_STORAGE_KEY: LAST_KEY,
    LAST_SOURCE_STORAGE_KEY: META_KEY,
  };
})(window);
