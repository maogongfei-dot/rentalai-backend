/**
 * Phase12 Step3-3 — Account: sessionStorage login state + Logout (no backend).
 */
(function () {
  var global = window;
  var KEYS = {
    userId: "rentalai_user_id",
    email: "rentalai_user_email",
    status: "rentalai_login_status",
  };

  function readSession() {
    try {
      return {
        userId: global.sessionStorage.getItem(KEYS.userId),
        email: global.sessionStorage.getItem(KEYS.email),
        status: global.sessionStorage.getItem(KEYS.status),
      };
    } catch (e) {
      return { userId: null, email: null, status: null };
    }
  }

  function isLoggedIn(s) {
    return (
      s &&
      s.status === "logged_in" &&
      s.email != null &&
      String(s.email).trim() !== ""
    );
  }

  function clearSession() {
    try {
      global.sessionStorage.removeItem(KEYS.userId);
      global.sessionStorage.removeItem(KEYS.email);
      global.sessionStorage.removeItem(KEYS.status);
    } catch (e) {}
  }

  function run() {
    var inBlock = document.getElementById("account-state-logged-in");
    var outBlock = document.getElementById("account-state-logged-out");
    var emailLine = document.getElementById("account-email-line");
    var btn = document.getElementById("account-logout-btn");

    var s = readSession();
    if (isLoggedIn(s)) {
      if (outBlock) outBlock.classList.add("hidden");
      if (inBlock) inBlock.classList.remove("hidden");
      if (emailLine) {
        emailLine.textContent = "Logged in as: " + String(s.email).trim();
      }
    } else {
      if (inBlock) inBlock.classList.add("hidden");
      if (outBlock) outBlock.classList.remove("hidden");
    }

    if (btn) {
      btn.addEventListener("click", function () {
        clearSession();
        global.location.href = "/";
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run);
  } else {
    run();
  }
})();
