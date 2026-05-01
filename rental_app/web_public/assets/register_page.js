/**
 * Phase12 Step3-1 — Register: POST /register, client validation, then redirect to /login.
 */
(function () {
  var global = window;

  function apiUrl(path) {
    return typeof global.rentalaiApiUrl === "function" ? global.rentalaiApiUrl(path) : path;
  }

  function parseJsonResponse(r) {
    var ct = (r.headers.get("content-type") || "").toLowerCase();
    if (ct.indexOf("application/json") >= 0) {
      return r.json().then(function (j) {
        return { ok: r.ok, status: r.status, body: j };
      });
    }
    return r.text().then(function (t) {
      return {
        ok: r.ok,
        status: r.status,
        body: { message: t || "Invalid response" },
      };
    });
  }

  function getBackendMessage(body) {
    if (body == null) return "Request failed";
    if (typeof body.message === "string" && body.message) return body.message;
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail) && body.detail.length) {
      var first = body.detail[0];
      if (first && typeof first.msg === "string") return first.msg;
    }
    return "Request failed";
  }

  function postRegister(email, password) {
    return global
      .fetch(apiUrl("/register"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email,
          password: password,
        }),
      })
      .then(parseJsonResponse)
      .catch(function () {
        return {
          ok: false,
          status: 0,
          body: { message: "Unable to reach the server. Please try again." },
        };
      });
  }

  var form = document.getElementById("register-form");
  var errEl = document.getElementById("register-err");
  var successEl = document.getElementById("register-success");
  var btn = document.getElementById("register-submit-btn");

  if (!form) return;

  function showErr(msg) {
    if (successEl) {
      successEl.textContent = "";
      successEl.classList.add("hidden");
    }
    if (!errEl) return;
    errEl.textContent = msg || "Something went wrong";
    errEl.classList.remove("hidden");
  }

  function clearErr() {
    if (!errEl) return;
    errEl.textContent = "";
    errEl.classList.add("hidden");
  }

  function showSuccess(msg) {
    if (errEl) {
      errEl.textContent = "";
      errEl.classList.add("hidden");
    }
    if (!successEl) return;
    successEl.textContent = msg || "Account created successfully";
    successEl.classList.remove("hidden");
  }

  function clearSuccess() {
    if (!successEl) return;
    successEl.textContent = "";
    successEl.classList.add("hidden");
  }

  function onSubmit() {
    clearErr();
    clearSuccess();

    var emailEl = document.getElementById("register-email");
    var passEl = document.getElementById("register-password");
    var confirmEl = document.getElementById("register-confirm-password");
    var email = emailEl ? String(emailEl.value || "").trim() : "";
    var password = passEl ? String(passEl.value || "") : "";
    var confirm = confirmEl ? String(confirmEl.value || "") : "";

    if (!email) {
      showErr("Please enter your email.");
      return;
    }
    if (!password) {
      showErr("Please enter your password.");
      return;
    }
    if (password !== confirm) {
      showErr("Passwords do not match.");
      return;
    }

    if (btn) btn.disabled = true;

    postRegister(email, password)
      .then(function (result) {
        var body = result.body || {};
        if (result.ok && body.success === true) {
          showSuccess("Account created successfully");
          setTimeout(function () {
            global.location.href = "/login";
          }, 600);
          return;
        }
        showErr(getBackendMessage(body));
      })
      .finally(function () {
        if (btn) btn.disabled = false;
      });
  }

  form.addEventListener("submit", function (ev) {
    ev.preventDefault();
    onSubmit();
  });
})();
