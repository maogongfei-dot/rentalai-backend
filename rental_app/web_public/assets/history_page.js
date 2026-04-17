/**
 * P10 Phase3 Step3 — /history list UI.
 */
(function (global) {
  function apiUrl(path) {
    return typeof global.rentalaiApiUrl === "function" ? global.rentalaiApiUrl(path) : path;
  }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  /**
   * 旧版历史列表渲染点（/history）：
   * 渲染后每条通过 task_id 跳转 /result/{task_id}，用于“点击历史还原结果页”。
   */
  function renderRows(items) {
    var tbody = document.getElementById("history-tbody");
    var empty = document.getElementById("history-empty");
    var err = document.getElementById("history-error");
    if (!tbody) return;
    tbody.innerHTML = "";
    if (err) err.classList.add("hidden");
    if (!items || !items.length) {
      if (empty) empty.classList.remove("hidden");
      return;
    }
    if (empty) empty.classList.add("hidden");
    items.forEach(function (row) {
      var tr = document.createElement("tr");
      var taskId = row.task_id ? String(row.task_id) : "";
      var href = taskId ? "/result/" + encodeURIComponent(taskId) : "";
      var title = row.title || "—";
      var score = row.final_score != null ? String(row.final_score) : "N/A";
      var verdict = row.verdict || "N/A";
      var when = row.created_at || "—";
      var inp = row.input_value ? String(row.input_value) : "—";
      if (inp.length > 48) inp = inp.slice(0, 45) + "…";
      var linkCell = href
        ? '<a class="history-link" href="' + href + '">View</a>'
        : "\u2014";
      tr.innerHTML =
        "<td>" +
        esc(when) +
        "</td><td>" +
        esc(inp) +
        "</td><td>" +
        esc(title) +
        "</td><td>" +
        esc(score) +
        "</td><td>" +
        esc(verdict) +
        "</td><td>" +
        linkCell +
        "</td>";
      tbody.appendChild(tr);
    });
  }

  /**
   * 旧版历史列表获取点：
   * 调用 /records/ui-history（Bearer 必需）读取当前用户已保存的历史快照列表。
   */
  function loadHistory() {
    var load = document.getElementById("history-loading");
    var err = document.getElementById("history-error");
    var empty = document.getElementById("history-empty");
    if (load) load.classList.remove("hidden");
    if (err) err.classList.add("hidden");
    if (empty) empty.classList.add("hidden");

    var H = global.RentalAIHistoryShelf;
    var A = global.RentalAIAuth;
    if (!H || typeof H.getToken !== "function") {
      if (load) load.classList.add("hidden");
      if (err) {
        err.textContent = "Failed to load history";
        err.classList.remove("hidden");
      }
      return;
    }

    if (!A || typeof A.isLoggedIn !== "function" || !A.isLoggedIn()) {
      if (load) load.classList.add("hidden");
      if (err) {
        err.textContent = "Login to save your analysis history";
        err.classList.remove("hidden");
      }
      return;
    }

    H.getToken()
      .then(function (token) {
        return fetch(apiUrl("/records/ui-history?limit=50"), {
          headers: { Authorization: "Bearer " + token },
        });
      })
      .then(function (r) {
        if (load) load.classList.add("hidden");
        if (r.status === 401) {
          if (err) {
            err.innerHTML = 'Please <a href="/login">log in</a> first.';
            err.classList.remove("hidden");
          }
          return;
        }
        if (!r.ok) {
          if (err) {
            err.textContent = "Failed to load history";
            err.classList.remove("hidden");
          }
          return;
        }
        return r.json().then(function (j) {
          renderRows(j.items || []);
        });
      })
      .catch(function (e) {
        if (load) load.classList.add("hidden");
        if (err) {
          err.classList.remove("hidden");
          if (e && e.message === "not_logged_in") {
            err.innerHTML = 'Please <a href="/login">log in</a> first.';
          } else {
            err.textContent = "Failed to load history";
          }
        }
      });
  }

  global.RentalAIHistoryPage = { loadHistory: loadHistory };
})(window);
