(function (global) {
  function apiUrl(path) {
    return typeof global.rentalaiApiUrl === "function" ? global.rentalaiApiUrl(path) : path;
  }

  var POLL_MS = 2500;
  var ANALYZE_COUNT_KEY = "rentalai_analyze_started_count";

  function getAuth() {
    return global.RentalAIAuth;
  }

  function taskHeaders() {
    var A = getAuth();
    if (!A || typeof A.getTaskApiHeaders !== "function") {
      return { "Content-Type": "application/json" };
    }
    return A.getTaskApiHeaders();
  }

  function readAnalyzeCount() {
    try {
      var n = parseInt(sessionStorage.getItem(ANALYZE_COUNT_KEY) || "0", 10);
      return isNaN(n) || n < 0 ? 0 : n;
    } catch (e) {
      return 0;
    }
  }

  function bumpAnalyzeCount() {
    try {
      sessionStorage.setItem(ANALYZE_COUNT_KEY, String(readAnalyzeCount() + 1));
    } catch (e) {}
  }

  function buildAnalyzeBody() {
    var body = { limit_per_source: 10, persist: true, headless: true };
    var locEl = document.getElementById("location");
    var raw = ((locEl && locEl.value) || "").trim();
    if (/^https?:\/\//i.test(raw)) {
      body.listing_url = raw;
    } else if (raw) {
      body.target_postcode = raw;
    }

    var pt = document.getElementById("property-type");
    if (pt && pt.value) body.property_type = pt.value;

    var br = document.getElementById("bedrooms");
    if (br && br.value) body.bedrooms = br.value;

    var bt = document.getElementById("bathrooms");
    if (bt && bt.value) body.bathrooms = parseFloat(bt.value);

    var budgetEl = document.getElementById("budget");
    var budgetRaw = ((budgetEl && budgetEl.value) || "").trim().replace(/,/g, "");
    if (budgetRaw) {
      var b = parseFloat(budgetRaw.replace(/[^0-9.]/g, ""));
      if (!isNaN(b) && isFinite(b)) body.budget = b;
    }

    var dist = document.getElementById("distance");
    if (dist && dist.value && dist.value !== "any") {
      body.distance_to_centre = dist.value;
    }

    var safety = document.getElementById("safety");
    if (safety && safety.value) body.safety_preference = safety.value;

    return body;
  }

  function pollUntilDone(taskId, headers, loadEl) {
    var max = 120;
    function step(i) {
      if (i >= max) return Promise.reject(new Error("poll timeout"));
      return fetch(apiUrl("/tasks/" + encodeURIComponent(taskId)), { headers: headers }).then(function (r) {
        if (r.status === 404) return Promise.reject(new Error("not found"));
        if (!r.ok) {
          return new Promise(function (resolve) {
            setTimeout(resolve, POLL_MS);
          }).then(function () {
            return step(i + 1);
          });
        }
        return r.json().then(function (st) {
          var s = st.status;
          if (loadEl) loadEl.textContent = "Analyzing... (" + s + ")";
          if (s === "failed" || s === "timeout" || s === "interrupted") {
            return Promise.reject(new Error(st.error || s));
          }
          if (s === "success" || s === "degraded") return;
          return new Promise(function (resolve) {
            setTimeout(resolve, POLL_MS);
          }).then(function () {
            return step(i + 1);
          });
        });
      });
    }
    return step(0);
  }

  function startAnalyze() {
    var load = document.getElementById("load");
    var err = document.getElementById("err");
    var go = document.getElementById("go");
    err.classList.add("hidden");
    err.innerHTML = "";
    var body = buildAnalyzeBody();
    if (!body.listing_url && !body.target_postcode) {
      err.textContent = "Please enter a postcode, area, or listing URL.";
      err.classList.remove("hidden");
      return;
    }

    var A = getAuth();
    if (A && A.isLoggedIn && !A.isLoggedIn()) {
      if (readAnalyzeCount() >= 1) {
        window.alert("Login to save your analysis history");
      }
    }

    load.classList.remove("hidden");
    go.disabled = true;
    var headers = taskHeaders();

    fetch(apiUrl("/tasks"), {
      method: "POST",
      headers: headers,
      body: JSON.stringify(body),
    })
      .then(function (resp) {
        if (!resp.ok) return Promise.reject(new Error("start failed"));
        return resp.json();
      })
      .then(function (created) {
        bumpAnalyzeCount();
        var taskId = created.task_id;
        if (!taskId) return Promise.reject(new Error("no task_id"));
        return pollUntilDone(taskId, headers, load).then(function () {
          window.location.href = "/result/" + encodeURIComponent(taskId);
        });
      })
      .catch(function (e) {
        load.classList.add("hidden");
        err.classList.remove("hidden");
        err.textContent = "Analysis failed, please try again.";
        if (e && e.message === "not found") {
          err.textContent = "Task not found. Please start again from the home page.";
        }
      })
      .then(function () {
        go.disabled = false;
      });
  }

  function renderResultPage() {
    var RV = global.RentalAIResultView;
    if (!RV || typeof RV.buildResultViewModel !== "function") {
      return;
    }
    var m = location.pathname.match(/\/result\/([^/]+)/);
    var taskId = m && m[1];
    if (!taskId) {
      RV.renderFromViewModel({
        phase: "failed",
        errorMessage: "Missing task id in URL",
        raw_task_state: { error: "bad_url" },
      });
      return;
    }
    var headers = taskHeaders();
    var max = 120;
    function poll(i) {
      if (i >= max) {
        return Promise.reject(new Error("timeout"));
      }
      return fetch(apiUrl("/tasks/" + encodeURIComponent(taskId)), { headers: headers }).then(function (r) {
        if (r.status === 404) {
          return Promise.reject(new Error("task_not_found"));
        }
        if (!r.ok) {
          return new Promise(function (resolve) {
            setTimeout(resolve, POLL_MS);
          }).then(function () {
            return poll(i + 1);
          });
        }
        return r.json().then(function (st) {
          st.task_id = st.task_id || taskId;
          var vm = RV.buildResultViewModel(st);
          var stEl = document.getElementById("loading-status");
          if (stEl && st.status) {
            stEl.textContent =
              "Analyzing\u2026 (" +
              String(st.status) +
              "). This may take several minutes; you can leave this page open.";
          }
          RV.renderFromViewModel(vm);
          if (vm.phase === "failed") {
            return null;
          }
          if (vm.phase === "ready") {
            return st;
          }
          return new Promise(function (resolve) {
            setTimeout(resolve, POLL_MS);
          }).then(function () {
            return poll(i + 1);
          });
        });
      });
    }
    poll(0).catch(function (e) {
      var msg;
      if (e && e.message === "task_not_found") {
        msg = "Task not found or it belongs to another session. Start a new analysis from the home page.";
      } else if (e && e.message) {
        msg = String(e.message).slice(0, 200);
      } else {
        msg = "";
      }
      RV.renderFromViewModel({
        phase: "failed",
        errorMessage: msg || "Network or server error",
        raw_task_state: { error: String(e && e.message ? e.message : e) },
      });
    });
  }

  global.RentalAIPhase3 = { startAnalyze: startAnalyze, renderResultPage: renderResultPage };
})(window);
