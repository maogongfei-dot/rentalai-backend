/**
 * Phase12 Step3-3 — Account: sessionStorage login + Logout.
 * Phase13 Step3-5 — Load GET /analysis-records/{user_id} and list saved analyses.
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

  function apiUrl(path) {
    return typeof global.rentalaiApiUrl === "function" ? global.rentalaiApiUrl(path) : path;
  }

  function truncateText(s, max) {
    var t = safePlainText(s);
    if (t.length <= max) return t;
    return t.slice(0, max) + "...";
  }

  function safePlainText(v) {
    if (v == null) return "";
    if (typeof v === "object") return "";
    var t = String(v).trim();
    if (!t) return "";
    if (t === "undefined" || t === "null" || t === "[object Object]") return "";
    return t;
  }

  function setRecordsUi(statusEl, listEl, statusMsg, showList) {
    if (statusEl) {
      statusEl.textContent = statusMsg || "";
      if (statusMsg) statusEl.classList.remove("hidden");
      else statusEl.classList.add("hidden");
    }
    if (listEl) {
      if (showList) listEl.classList.remove("hidden");
      else {
        listEl.classList.add("hidden");
        listEl.innerHTML = "";
      }
    }
  }

  function renderRecordsList(records) {
    var listEl = global.document.getElementById("account-records-list");
    var statusEl = global.document.getElementById("account-records-status");
    if (!listEl || !statusEl) return;

    if (!records || !records.length) {
      statusEl.classList.remove("hidden");
      statusEl.textContent = "No saved analysis records yet.";
      listEl.classList.add("hidden");
      listEl.innerHTML = "";
      return;
    }

    statusEl.textContent = "";
    statusEl.classList.add("hidden");
    listEl.classList.remove("hidden");
    listEl.innerHTML = "";

    records.forEach(function (rec) {
      var row = global.document.createElement("div");
      row.className = "account-record-row";

      var dateLabel = global.document.createElement("p");
      dateLabel.className = "account-record-label";
      dateLabel.textContent = "Analysis date";

      var meta = global.document.createElement("p");
      meta.className = "account-record-meta";
      meta.textContent = safePlainText(rec.created_at);

      var summaryLabel = global.document.createElement("p");
      summaryLabel.className = "account-record-label";
      summaryLabel.textContent =
        rec.analysis_kind &&
        String(rec.analysis_kind).toLowerCase().trim() === "contract"
          ? "Input summary (contract)"
          : "Input summary (property)";

      var inp = global.document.createElement("p");
      inp.className = "account-record-input";
      inp.textContent = truncateText(rec.input_text, 120);

      var btn = global.document.createElement("button");
      btn.type = "button";
      btn.className = "saas-btn saas-btn--primary account-record-view";
      btn.textContent = "View Result";

      var rj = rec.result_json != null ? String(rec.result_json) : "";
      btn.addEventListener("click", function () {
        try {
          var kind =
            rec.analysis_kind &&
            String(rec.analysis_kind).toLowerCase().trim() === "contract"
              ? "contract"
              : "property";
          global.sessionStorage.setItem("rentalai_analysis_type", kind);
        } catch (eT) {}
        try {
          global.sessionStorage.setItem("rentalai_result", rj);
        } catch (e1) {}
        global.location.href = "/ai-result";
      });

      row.appendChild(dateLabel);
      row.appendChild(meta);
      row.appendChild(summaryLabel);
      row.appendChild(inp);
      row.appendChild(btn);
      listEl.appendChild(row);
    });
  }

  function loadAnalysisRecords(uid) {
    var statusEl = global.document.getElementById("account-records-status");
    var listEl = global.document.getElementById("account-records-list");
    if (statusEl) {
      statusEl.classList.remove("hidden");
      statusEl.textContent = "Loading…";
    }
    if (listEl) {
      listEl.classList.add("hidden");
      listEl.innerHTML = "";
    }

    var url = apiUrl("/analysis-records/" + encodeURIComponent(uid));
    global
      .fetch(url, { credentials: typeof global.rentalaiDefaultFetchCredentials === "function"
        ? global.rentalaiDefaultFetchCredentials()
        : "same-origin" })
      .then(function (r) {
        if (!r.ok) throw new Error("records_http_" + r.status);
        return r.json();
      })
      .then(function (j) {
        if (!j || j.success !== true || !Array.isArray(j.records)) {
          renderRecordsList([]);
          return;
        }
        renderRecordsList(j.records);
      })
      .catch(function () {
        if (statusEl) {
          statusEl.classList.remove("hidden");
          statusEl.textContent = "Could not load records. Try again later.";
        }
        if (listEl) {
          listEl.classList.add("hidden");
          listEl.innerHTML = "";
        }
      });
  }

  function refreshRecordsSection(s) {
    var statusEl = global.document.getElementById("account-records-status");
    var listEl = global.document.getElementById("account-records-list");

    var uid = "";
    try {
      uid = String(global.sessionStorage.getItem(KEYS.userId) || "").trim();
    } catch (e2) {}

    if (!isLoggedIn(s) || !uid) {
      setRecordsUi(statusEl, listEl, "Please log in to view your saved analysis records.", false);
      return;
    }

    loadAnalysisRecords(uid);
  }

  function run() {
    var inBlock = global.document.getElementById("account-state-logged-in");
    var outBlock = global.document.getElementById("account-state-logged-out");
    var emailLine = global.document.getElementById("account-email-line");
    var btn = global.document.getElementById("account-logout-btn");

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

    refreshRecordsSection(s);
  }

  if (global.document.readyState === "loading") {
    global.document.addEventListener("DOMContentLoaded", run);
  } else {
    run();
  }
})();
