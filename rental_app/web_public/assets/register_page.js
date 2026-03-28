(function () {
  function apiUrl(path) {
    return typeof window.rentalaiApiUrl === "function" ? window.rentalaiApiUrl(path) : path;
  }

  var form = document.getElementById("register-form");
  var err = document.getElementById("register-err");
  if (!form) return;

  form.addEventListener("submit", function (ev) {
    ev.preventDefault();
    if (err) {
      err.textContent = "";
      err.classList.add("hidden");
    }
    var email = (document.getElementById("register-email") || {}).value || "";
    var password = (document.getElementById("register-password") || {}).value || "";
    fetch(apiUrl("/auth/register"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email.trim(), password: password }),
    })
      .then(function (r) {
        return r.json().then(function (j) {
          return { ok: r.ok, body: j };
        });
      })
      .then(function (x) {
        if (!x.ok) {
          var msg =
            x.body && x.body.message
              ? String(x.body.message)
              : "Could not register.";
          if (err) {
            err.textContent = msg;
            err.classList.remove("hidden");
          }
          return;
        }
        if (window.RentalAIAuth && typeof window.RentalAIAuth.persistSession === "function") {
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
          err.textContent = "Could not register.";
          err.classList.remove("hidden");
        }
      });
  });
})();
