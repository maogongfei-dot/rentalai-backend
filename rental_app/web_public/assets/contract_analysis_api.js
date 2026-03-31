/**
 * Phase 4：合同分析 API 客户端（与 api_config.js 同源 fetch，无 axios）。
 *
 * - analyzeContractText：POST /api/contract/analysis/text
 * - analyzeContractFile：POST /api/contract/analysis/file-path（服务端可读路径，非 multipart）
 */
(function (global) {
  var LAST_KEY = "rentalai_contract_analysis_last";

  function apiUrl(path) {
    if (typeof global.rentalaiApiUrl === "function") {
      return global.rentalaiApiUrl(path);
    }
    var p = (path || "").trim();
    return p.charAt(0) === "/" ? p : "/" + p;
  }

  function postJson(path, body) {
    var url = apiUrl(path);
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    }).then(function (r) {
      return r.text().then(function (text) {
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

  /** 将最近一次成功响应写入 sessionStorage，供刷新或后续页面读取 */
  function saveLastContractAnalysisResult(payload) {
    try {
      global.sessionStorage.setItem(LAST_KEY, JSON.stringify(payload));
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

  global.RentalAIContractAnalysis = {
    analyzeContractText: analyzeContractText,
    /** 服务端路径版「文件」分析（与 multipart 上传无关） */
    analyzeContractFile: analyzeContractFile,
    saveLastContractAnalysisResult: saveLastContractAnalysisResult,
    readLastContractAnalysisResult: readLastContractAnalysisResult,
    LAST_RESULT_STORAGE_KEY: LAST_KEY,
  };
})(window);
