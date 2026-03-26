/**
 * 公网前后端分离时：API 根地址（Render）与静态页（Vercel）不同域，需配置此项。
 * 优先级：meta[name="rentalai-api-base"] > 页面中已存在的 window.RENTALAI_API_BASE
 * 本地同源（python run.py 同时提供页面与 API）时保持为空即可。
 */
(function () {
  var base = "";
  try {
    var m = document.querySelector('meta[name="rentalai-api-base"]');
    if (m) {
      var c = (m.getAttribute("content") || "").trim();
      if (c) base = c;
    }
  } catch (e) {}
  if (!base && typeof window.RENTALAI_API_BASE === "string") {
    base = window.RENTALAI_API_BASE;
  }
  window.RENTALAI_API_BASE = String(base).replace(/\/$/, "");
})();
