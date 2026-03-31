/**
 * P10 Phase3 Step4 — browser session (Bearer token + profile in localStorage).
 * P10 Phase7 — guest session header for tasks without blocking analysis.
 */
(function (global) {
  function apiUrl(path) {
    return typeof global.rentalaiApiUrl === "function" ? global.rentalaiApiUrl(path) : path;
  }

  var K = {
    bearer: "rentalai_bearer",
    userId: "rentalai_user_id",
    email: "rentalai_user_email",
  };
  var GUEST_KEY = "rentalai_guest_session";

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
    updateHomeGuestNotice();
    updateResultGuestBanner();
  }

  function clearSession() {
    localStorage.removeItem(K.bearer);
    localStorage.removeItem(K.userId);
    localStorage.removeItem(K.email);
    initAuthNav();
    updateHomeGuestNotice();
    updateResultGuestBanner();
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

  function ensureGuestSessionId() {
    try {
      var x = sessionStorage.getItem(GUEST_KEY);
      if (x && /^[a-fA-F0-9\-]{8,128}$/.test(x)) return x;
      x = "";
      if (global.crypto && typeof global.crypto.randomUUID === "function") {
        x = global.crypto.randomUUID();
      } else {
        x = String(Date.now()) + "-" + Math.random().toString(16).slice(2);
      }
      sessionStorage.setItem(GUEST_KEY, x);
      return x;
    } catch (e) {
      return (Date.now().toString(16) + Math.random().toString(16).slice(2, 18)).replace(/[^a-f0-9]/gi, "0").slice(0, 40);
    }
  }

  function getTaskApiHeaders() {
    var h = { "Content-Type": "application/json" };
    var t = getStoredToken();
    if (t) {
      h.Authorization = "Bearer " + t;
      return h;
    }
    h["X-Guest-Session"] = ensureGuestSessionId();
    return h;
  }

  function updateHomeGuestNotice() {
    var el = document.getElementById("home-guest-notice");
    if (!el) return;
    if (isLoggedIn()) el.classList.add("hidden");
    else el.classList.remove("hidden");
  }

  function updateResultGuestBanner() {
    var el = document.getElementById("result-guest-banner");
    if (!el) return;
    if (isLoggedIn()) el.classList.add("hidden");
    else el.classList.remove("hidden");
  }

  function guardHistoryLinks() {
    document.querySelectorAll('a[href="/history"], a[href="/analysis-history"]').forEach(function (a) {
      a.addEventListener("click", function (ev) {
        try {
          if (localStorage.getItem("current_user")) return;
        } catch (e) {}
        if (!isLoggedIn()) {
          ev.preventDefault();
          window.alert("Login to save your analysis history");
        }
      });
    });
  }

  function logout() {
    var t = getStoredToken();
    var p = Promise.resolve();
    if (t) {
      p = fetch(apiUrl("/auth/logout"), {
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
    fetch(apiUrl("/auth/me"), { headers: { Authorization: "Bearer " + t } })
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
        updateHomeGuestNotice();
        updateResultGuestBanner();
      })
      .catch(function () {});
  }

  function onReady() {
    initAuthNav();
    updateHomeGuestNotice();
    updateResultGuestBanner();
    guardHistoryLinks();
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
    getTaskApiHeaders: getTaskApiHeaders,
    ensureGuestSessionId: ensureGuestSessionId,
    logout: logout,
    initAuthNav: initAuthNav,
    updateHomeGuestNotice: updateHomeGuestNotice,
  };
})(window);
