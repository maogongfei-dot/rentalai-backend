(function (global) {
  var POLL_MS = 2500;

  function getToken() {
    var t = localStorage.getItem("rentalai_bearer");
    if (t) return Promise.resolve(t);
    var id = crypto.randomUUID();
    var email = "guest_" + id.replace(/-/g, "") + "@guest.rentalai.local";
    var password = crypto.randomUUID().replace(/-/g, "").slice(0, 32);
    return fetch("/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email, password: password }),
    })
      .then(function (r1) {
        if (!r1.ok) return Promise.reject(new Error("register failed"));
        return fetch("/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: email, password: password }),
        });
      })
      .then(function (r2) {
        if (!r2.ok) return Promise.reject(new Error("login failed"));
        return r2.json();
      })
      .then(function (j2) {
        t = j2.token;
        if (!t) return Promise.reject(new Error("no token"));
        localStorage.setItem("rentalai_bearer", t);
        return t;
      });
  }

  function pollUntilDone(taskId, token, loadEl) {
    var max = 120;
    function step(i) {
      if (i >= max) return Promise.reject(new Error("poll timeout"));
      return fetch("/tasks/" + encodeURIComponent(taskId), {
        headers: { Authorization: "Bearer " + token },
      }).then(function (r) {
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
    var qEl = document.getElementById("q");
    var load = document.getElementById("load");
    var err = document.getElementById("err");
    var go = document.getElementById("go");
    err.classList.add("hidden");
    err.textContent = "";
    var raw = ((qEl && qEl.value) || "").trim();
    if (!raw) {
      err.textContent = "Please enter a postcode, area, or listing URL.";
      err.classList.remove("hidden");
      return;
    }
    load.classList.remove("hidden");
    go.disabled = true;
    getToken()
      .then(function (token) {
        var body = { limit_per_source: 10, persist: true, headless: true };
        if (/^https?:\/\//i.test(raw)) {
          body.listing_url = raw;
        } else {
          body.target_postcode = raw;
        }
        return fetch("/tasks", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: "Bearer " + token,
          },
          body: JSON.stringify(body),
        }).then(function (resp) {
          if (!resp.ok) return Promise.reject(new Error("start failed"));
          return resp.json().then(function (created) {
            return { token: token, created: created };
          });
        });
      })
      .then(function (x) {
        var taskId = x.created.task_id;
        if (!taskId) return Promise.reject(new Error("no task_id"));
        return pollUntilDone(taskId, x.token, load).then(function () {
          window.location.href = "/result/" + encodeURIComponent(taskId);
        });
      })
      .catch(function () {
        err.textContent = "Analysis failed, please try again";
        err.classList.remove("hidden");
        load.classList.add("hidden");
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
    getToken()
      .then(function (token) {
        var max = 120;
        function poll(i) {
          if (i >= max) {
            return Promise.reject(new Error("timeout"));
          }
          return fetch("/tasks/" + encodeURIComponent(taskId), {
            headers: { Authorization: "Bearer " + token },
          }).then(function (r) {
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
        return poll(0);
      })
      .catch(function (e) {
        var msg =
          e && e.message === "task_not_found"
            ? "Task not found (wrong account or expired)."
            : e && e.message
              ? String(e.message).slice(0, 200)
              : "";
        RV.renderFromViewModel({
          phase: "failed",
          errorMessage: msg || "Network or server error",
          raw_task_state: { error: String(e && e.message ? e.message : e) },
        });
      });
  }

  global.RentalAIPhase3 = { startAnalyze: startAnalyze, renderResultPage: renderResultPage };
})(window);
