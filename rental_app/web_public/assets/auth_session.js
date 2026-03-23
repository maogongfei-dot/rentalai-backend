/**
 * P10 Phase3 Step4 — browser session for registered users (Bearer token + profile in localStorage).
 */
(function (global) {
  var K = {
    bearer: "rentalai_bearer",
    userId: "rentalai_user_id",
    email: "rentalai_user_email",
  };

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function persistSession(data) {
    if (!data || !data.token) return;
    localStorage.setItem(K.bearer, String(data.token));
    if (data.user_id) localStorage.setItem(K.userId, String(data.user_id));
    if (data.email) localStorage.setItem(K.email, String(data.email));
    initAuthNav();
  }

  function clearSession() {
    localStorage.removeItem(K.bearer);
    localStorage.removeItem(K.userId);
    localStorage.removeItem(K.email);
    initAuthNav();
  }

  function getStoredToken() {
    return localStorage.getItem(K.bearer);
  }

  function isLoggedIn() {
    return Boolean(getStoredToken());
  }

  function requireToken() {
    var t = getStoredToken();
    if (!t) return Promise.reject(new Error("not_logged_in"));
    return Promise.resolve(t);
  }

  function logout() {
    var t = getStoredToken();
    var p = Promise.resolve();
    if (t) {
      p = fetch("/auth/logout", {
        method: "POST",
        headers: { Authorization: "Bearer " + t },
      }).catch(function () {});
    }
    return p.then(function () {
      clearSession();
      window.location.href = "/login";
    });
  }

  function initAuthNav() {
    var slots = document.querySelectorAll("[data-auth-nav]");
    if (!slots.length) return;
    var email = localStorage.getItem(K.email);
    var has = isLoggedIn();
    var html;
    if (has && email) {
      html =
        '<span class="auth-email">' +
        esc(email) +
        '</span> <button type="button" class="auth-logout-btn" data-action="logout">Logout</button>';
    } else {
      html =
        '<a href="/login">Login</a><span class="nav-sep">·</span><a href="/register">Register</a>';
    }
    slots.forEach(function (el) {
      el.innerHTML = html;
    });
    document.querySelectorAll("[data-action=logout]").forEach(function (btn) {
      btn.onclick = function () {
        logout();
      };
    });
  }

  function backfillProfileFromServer() {
    var t = getStoredToken();
    if (!t) return;
    fetch("/auth/me", { headers: { Authorization: "Bearer " + t } })
      .then(function (r) {
        if (r.status === 401) {
          clearSession();
          return null;
        }
        return r.ok ? r.json() : null;
      })
      .then(function (j) {
        if (!j || !j.email) return;
        localStorage.setItem(K.email, String(j.email));
        if (j.user_id) localStorage.setItem(K.userId, String(j.user_id));
        initAuthNav();
      })
      .catch(function () {});
  }

  function onReady() {
    initAuthNav();
    if (getStoredToken() && !localStorage.getItem(K.email)) {
      backfillProfileFromServer();
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", onReady);
  } else {
    onReady();
  }

  global.RentalAIAuth = {
    persistSession: persistSession,
    clearSession: clearSession,
    requireToken: requireToken,
    isLoggedIn: isLoggedIn,
    getStoredToken: getStoredToken,
    logout: logout,
    initAuthNav: initAuthNav,
  };
})(window);
