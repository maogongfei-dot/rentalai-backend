/**
 * 仅使用同域相对路径，不拼接任何外部域名（与 FastAPI 同源部署，避免 CORS）。
 * 所有 API 请求经 rentalaiApiUrl("/path") → "/path"
 */
(function () {
  window.RENTALAI_API_BASE = "";

  window.rentalaiApiUrl = function (path) {
    var p = (path || "").trim();
    if (!p) return "";
    return p.charAt(0) === "/" ? p : "/" + p;
  };
})();
