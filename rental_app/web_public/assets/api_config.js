/**
 * API 根地址：仅当前端与 FastAPI 不同域时在 meta 中填写（如 Vercel + Render）。
 * 与当前页面同域（同一 Render Web Service 跑 python run.py）时：meta 留空 → 只用相对路径，无 CORS。
 *
 * 优先级：meta vite-rentalai-api-base > meta rentalai-api-base > window.RENTALAI_API_BASE
 * 若解析出的 base 与 location.origin 相同，则视为同源并清空 base（避免误配导致跨域）。
 */
(function () {
  function normalizeSameOrigin(b) {
    var s = String(b || "").trim().replace(/\/$/, "");
    if (!s) return "";
    try {
      var o = window.location.origin || "";
      if (o && s === o) return "";
    } catch (e) {}
    return s;
  }

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
  base = normalizeSameOrigin(base);
  window.RENTALAI_API_BASE = String(base).replace(/\/$/, "");

  window.rentalaiApiUrl = function (path) {
    var p = (path || "").trim();
    if (!p) return window.RENTALAI_API_BASE || "";
    if (p.charAt(0) !== "/") p = "/" + p;
    var b = window.RENTALAI_API_BASE || "";
    return b ? b + p : p;
  };
})();
