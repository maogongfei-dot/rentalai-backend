/**
 * Phase12 Step3-2 — Login: POST /login, validation, sessionStorage, redirect to account.
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

  function postLogin(email, password) {
    return global
      .fetch(apiUrl("/login"), {
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

  function persistLoginSession(body) {
    try {
      var uid = body.user_id != null ? String(body.user_id) : "";
      var em = body.email != null ? String(body.email) : "";
      global.sessionStorage.setItem("rentalai_user_id", uid);
      global.sessionStorage.setItem("rentalai_user_email", em);
      global.sessionStorage.setItem("rentalai_login_status", "logged_in");
    } catch (e) {}
  }

  var form = document.getElementById("login-form");
  var errEl = document.getElementById("login-err");
  var btn = document.getElementById("login-submit-btn");

  if (!form) return;

  function showErr(msg) {
    if (!errEl) return;
    errEl.textContent = msg || "Something went wrong";
    errEl.classList.remove("hidden");
  }

  function clearErr() {
    if (!errEl) return;
    errEl.textContent = "";
    errEl.classList.add("hidden");
  }

  function onSubmit() {
    clearErr();

    var emailEl = document.getElementById("login-email");
    var passEl = document.getElementById("login-password");
    var email = emailEl ? String(emailEl.value || "").trim() : "";
    var password = passEl ? String(passEl.value || "") : "";

    if (!email) {
      showErr("Please enter your email.");
      return;
    }
    if (!password) {
      showErr("Please enter your password.");
      return;
    }

    if (btn) btn.disabled = true;

    postLogin(email, password)
      .then(function (result) {
        var body = result.body || {};
        if (result.ok && body.success === true) {
          persistLoginSession(body);
          global.location.href = "/account";
          return;
        }
        if (body.success === false) {
          showErr(getBackendMessage(body));
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
