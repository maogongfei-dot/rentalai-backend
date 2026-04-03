/**
 * API base URL: empty = same-origin (FastAPI + static 同进程)；非空 = 分域部署时 API 根（无尾部斜杠）。
 * 读取顺序：meta vite-rentalai-api-base > rentalai-api-base > 构建前预设的 window.RENTALAI_API_BASE（测试用）。
 * 与 scripts/inject-api-base.mjs、Vercel Build 环境变量 RENTALAI_API_BASE 等配合。
 */
(function () {
  function getMeta(name) {
    var el = document.querySelector('meta[name="' + name + '"]');
    return el ? String(el.getAttribute("content") || "").trim() : "";
  }

  var preset =
    typeof window.RENTALAI_API_BASE === "string"
      ? String(window.RENTALAI_API_BASE).trim()
      : "";
  var viteBase = getMeta("vite-rentalai-api-base");
  var rentalBase = getMeta("rentalai-api-base");
  var base = (viteBase || rentalBase || preset || "").replace(/\/$/, "");
  window.RENTALAI_API_BASE = base;

  var envMeta = getMeta("rentalai-env");
  if (envMeta) {
    window.RENTALAI_ENV = envMeta;
  } else {
    var h = (location.hostname || "").toLowerCase();
    window.RENTALAI_ENV =
      h === "localhost" || h === "127.0.0.1" || h === "[::1]"
        ? "development"
        : "production";
  }

  window.rentalaiApiUrl = function (path) {
    var p = (path || "").trim();
    if (!p) return "";
    if (p.charAt(0) !== "/") p = "/" + p;
    if (!base) return p;
    return base + p;
  };
})();
