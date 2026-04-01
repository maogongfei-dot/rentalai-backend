/**
 * 本地假登录：经 RentalAIUserStore.loginUser(local_demo) 写入 current_user。
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

  var input = document.getElementById("local-login-input");
  var btn = document.getElementById("local-login-go");
  if (!input || !btn) return;

  btn.addEventListener("click", function () {
    var v = (input.value || "").trim();
    if (!v) {
      alert("请输入用户名或邮箱");
      return;
    }
    var looksEmail = v.indexOf("@") > 0;
    var user = {
      user_id: "u_" + Date.now(),
      display_name: v,
      login_at: new Date().toISOString(),
    };
    if (window.RentalAIUserStore && typeof window.RentalAIUserStore.loginUser === "function") {
      window.RentalAIUserStore.loginUser({
        source: "local_demo",
        userId: user.user_id,
        displayName: user.display_name,
        email: looksEmail ? v : undefined,
      });
    } else {
      try {
        localStorage.setItem("current_user", JSON.stringify(user));
      } catch (e2) {}
    }
    window.location.href = "/";
  });
})();
