/**
 * 注册页：RentalAIAuthApi.registerApi → applySessionFromAuthBody → 跳转首页。
 */
(function () {
  try {
    if (
      window.RentalAIUserStore &&
      window.RentalAIUserStore.loadUserFromStorage().isAuthenticated
    ) {
      window.location.replace("/");
      return;
    }
  } catch (e) {}

  var form = document.getElementById("register-form");
  var err = document.getElementById("register-err");
  if (!form) return;

  function showErr(msg) {
    if (!err) return;
    err.textContent = msg || "注册失败";
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
    var email = (document.getElementById("register-email") || {}).value || "";
    var password = (document.getElementById("register-password") || {}).value || "";

    var api = window.RentalAIAuthApi;
    if (!api || typeof api.registerApi !== "function") {
      showErr("缺少 auth_api.js，请刷新页面。");
      return;
    }

    api
      .registerApi(email, password)
      .then(function (result) {
        if (!result.ok) {
          showErr(api.getErrorMessage(result.body));
          return;
        }
        var b = result.body || {};
        if (!b.token) {
          showErr("注册响应缺少 token");
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
