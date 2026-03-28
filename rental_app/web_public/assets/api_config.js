/**
 * 公网前后端分离：API 根与静态页不同域时配置。
 * 运行时优先级：meta vite-rentalai-api-base（对应构建环境变量 VITE_RENTALAI_API_BASE）
 *   > meta rentalai-api-base > 已存在的 window.RENTALAI_API_BASE
 * 本地同源（python run.py）两 meta 留空即可。
 *
 * 统一请求：window.rentalaiApiUrl("/api/ai/query")；勿在页面写死后端 URL。
 */
(function () {
  var base = "";
  try {
    var mv = document.querySelector('meta[name="vite-rentalai-api-base"]');
    var m = document.querySelector('meta[name="rentalai-api-base"]');
    var vc = mv && (mv.getAttribute("content") || "").trim();
    var mc = m && (m.getAttribute("content") || "").trim();
    if (vc) base = vc;
    else if (mc) base = mc;
  } catch (e) {}
  if (!base && typeof window.RENTALAI_API_BASE === "string") {
    base = window.RENTALAI_API_BASE;
  }
  window.RENTALAI_API_BASE = String(base).replace(/\/$/, "");

  window.rentalaiApiUrl = function (path) {
    var p = (path || "").trim();
    if (!p) return window.RENTALAI_API_BASE || "";
    if (p.charAt(0) !== "/") p = "/" + p;
    var b = window.RENTALAI_API_BASE || "";
    return b ? b + p : p;
  };
})();
