/**
 * 本地假登录：写入 current_user 后跳转首页。
 */
(function () {
  try {
    var raw = localStorage.getItem("current_user");
    if (raw) {
      var o = JSON.parse(raw);
      if (o && o.user_id) {
        window.location.replace("/");
        return;
      }
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
    var user = {
      user_id: "u_" + Date.now(),
      display_name: v,
      login_at: new Date().toISOString(),
    };
    localStorage.setItem("current_user", JSON.stringify(user));
    window.location.href = "/";
  });
})();
