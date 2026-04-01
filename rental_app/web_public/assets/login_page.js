(function () {
  function apiUrl(path) {
    return typeof window.rentalaiApiUrl === "function" ? window.rentalaiApiUrl(path) : path;
  }

  var form = document.getElementById("login-form");
  var err = document.getElementById("login-err");
  if (!form) return;

  form.addEventListener("submit", function (ev) {
    ev.preventDefault();
    if (err) {
      err.textContent = "";
      err.classList.add("hidden");
    }
    var email = (document.getElementById("login-email") || {}).value || "";
    var password = (document.getElementById("login-password") || {}).value || "";
    fetch(apiUrl("/auth/login"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email.trim(), password: password }),
    })
      .then(function (r) {
        return r.json().then(function (j) {
          return { ok: r.ok, status: r.status, body: j };
        });
      })
      .then(function (x) {
        if (!x.ok) {
          var msg =
            x.body && x.body.message
              ? String(x.body.message)
              : "邮箱或密码错误。";
          if (err) {
            err.textContent = msg;
            err.classList.remove("hidden");
          }
          return;
        }
        if (window.RentalAIUserStore && typeof window.RentalAIUserStore.loginUser === "function") {
          window.RentalAIUserStore.loginUser({
            token: x.body.token,
            userId: x.body.user_id,
            email: x.body.email,
          });
        } else if (window.RentalAIAuth && typeof window.RentalAIAuth.persistSession === "function") {
          try {
            localStorage.removeItem("current_user");
          } catch (e) {}
          window.RentalAIAuth.persistSession({
            token: x.body.token,
            user_id: x.body.user_id,
            email: x.body.email,
          });
        }
        window.location.href = "/";
      })
      .catch(function () {
        if (err) {
          err.textContent = "无法连接服务器，请稍后重试。";
          err.classList.remove("hidden");
        }
      });
  });
})();
