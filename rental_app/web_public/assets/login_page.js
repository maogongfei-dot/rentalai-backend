/**
 * 登录页：RentalAIAuthApi.loginApi → applySessionFromAuthBody → 跳转首页。
 */
(function () {
  var form = document.getElementById("login-form");
  var err = document.getElementById("login-err");
  if (!form) return;

  function showErr(msg) {
    if (!err) return;
    err.textContent = msg || "登录失败";
    err.classList.remove("hidden");
  }

  function clearErr() {
    if (!err) return;
    err.textContent = "";
    err.classList.add("hidden");
  }

  form.addEventListener("submit", function (ev) {
    ev.preventDefault();
    clearErr();
    var email = (document.getElementById("login-email") || {}).value || "";
    var password = (document.getElementById("login-password") || {}).value || "";

    var api = window.RentalAIAuthApi;
    if (!api || typeof api.loginApi !== "function") {
      showErr("缺少 auth_api.js，请刷新页面。");
      return;
    }

    api
      .loginApi(email, password)
      .then(function (result) {
        if (!result.ok) {
          showErr(api.getErrorMessage(result.body));
          return;
        }
        var b = result.body || {};
        if (!b.token) {
          showErr("登录响应缺少 token");
          return;
        }
        if (typeof api.applySessionFromAuthBody === "function") {
          api.applySessionFromAuthBody(b);
        }
        window.location.href = "/";
      })
      .catch(function () {
        showErr("无法连接服务器，请稍后重试。");
      });
  });
})();
