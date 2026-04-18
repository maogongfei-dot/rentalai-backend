/**
 * /history 页面统一按「当前历史作用域」工作：
 * - 已登录：展示当前账号自己的历史
 * - 未登录：展示当前游客 guest:<session> 历史
 * - 登录用户与游客历史不合并
 * 本文件不再使用「必须登录才能查看历史」的旧前提逻辑。
 *
 * 拉取 / 删除 / 清空一律经 RentalAIServerHistoryApi，配合 getCurrentHistoryScopeUserId() 与
 * getCurrentHistoryScopeMeta()；不自行拼 Authorization、不判断 isLoggedIn、不直连旧 ui-history 等第二套实现。
 * 登录态变化后的刷新见 refreshHistoryIfScopeChanged / bootHistoryPage。
 */
(function (global) {
  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  /**
   * 表格渲染：列结构不变。空状态文案与 loadHistory 成功路径共用同一套 meta（见第二参数），避免两套空状态逻辑。
   */
  function renderRows(items, scopeMeta) {
    var tbody = document.getElementById("history-tbody");
    var empty = document.getElementById("history-empty");
    var err = document.getElementById("history-error");
    if (!tbody) return;
    tbody.innerHTML = "";
    if (err) err.classList.add("hidden");
    if (!items || !items.length) {
      var metaForEmpty = scopeMeta != null ? scopeMeta : getCurrentHistoryScopeMeta();
      if (empty) {
        empty.textContent =
          metaForEmpty.mode === "user"
            ? "No saved history for this account yet."
            : "No history for this guest session yet.";
        empty.classList.remove("hidden");
      }
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
      var recId =
        row.record_id != null && String(row.record_id).trim()
          ? String(row.record_id).trim()
          : row.id != null && String(row.id).trim()
            ? String(row.id).trim()
            : "";
      var delCell =
        recId
          ? '<button type="button" class="history-delete-one-btn" data-record-id="' +
            esc(recId) +
            '">Delete</button>'
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
        "</td><td>" +
        delCell +
        "</td>";
      tbody.appendChild(tr);
    });
  }

  function getCurrentHistoryScopeUserId() {
    try {
      var S = global.RentalAIUserStore;
      if (S && typeof S.getCurrentHistoryScopeUserId === "function") {
        return String(S.getCurrentHistoryScopeUserId() || "").trim();
      }
    } catch (e) {}
    return "";
  }

  function getCurrentHistoryScopeMeta() {
    try {
      var S = global.RentalAIUserStore;
      if (S && typeof S.loadUserFromStorage === "function") {
        var u = S.loadUserFromStorage();
        var scopeId = getCurrentHistoryScopeUserId();
        if (u && u.isAuthenticated) {
          return {
            mode: "user",
            title: "Your saved history",
            detail: u.email
              ? "Showing saved history for " + String(u.email)
              : "Showing saved history for your account",
            scopeUserId: scopeId,
          };
        }
        return {
          mode: "guest",
          title: "Guest history",
          detail:
            "Showing history for the current guest session only. It will not be merged automatically after login.",
          scopeUserId: scopeId,
        };
      }
    } catch (e) {}

    return {
      mode: "guest",
      title: "Guest history",
      detail:
        "Showing history for the current guest session only. It will not be merged automatically after login.",
      scopeUserId: getCurrentHistoryScopeUserId(),
    };
  }

  function applyHistoryScopeLeadIfPresent(meta) {
    if (!meta) return;
    try {
      var lead = document.getElementById("history-page-lead");
      if (lead) lead.textContent = meta.detail || "";
    } catch (e0) {}
  }

  /** 列表唯一入口：RentalAIServerHistoryApi.fetchUserHistory + 当前作用域 userId。 */
  function loadHistory() {
    var load = document.getElementById("history-loading");
    var err = document.getElementById("history-error");
    var empty = document.getElementById("history-empty");
    if (load) load.classList.remove("hidden");
    if (err) err.classList.add("hidden");
    if (empty) empty.classList.add("hidden");

    var Api = global.RentalAIServerHistoryApi;
    if (!Api || typeof Api.fetchUserHistory !== "function") {
      if (load) load.classList.add("hidden");
      if (err) {
        err.textContent = "Failed to load history";
        err.classList.remove("hidden");
      }
      return;
    }

    var scopeUserId = getCurrentHistoryScopeUserId();

    Api.fetchUserHistory(scopeUserId, { cacheBust: true })
      .then(function (body) {
        if (load) load.classList.add("hidden");

        if (!body || body.success === false) {
          if (err) {
            err.textContent = "Failed to load history";
            err.classList.remove("hidden");
          }
          renderRows([], getCurrentHistoryScopeMeta());
          return;
        }

        var rec = Array.isArray(body.records) ? body.records : [];
        var meta = getCurrentHistoryScopeMeta();
        applyHistoryScopeLeadIfPresent(meta);
        renderRows(rec, meta);
      })
      .catch(function () {
        if (load) load.classList.add("hidden");
        if (err) {
          err.textContent = "Failed to load history";
          err.classList.remove("hidden");
        }
        renderRows([], getCurrentHistoryScopeMeta());
      });
  }

  function getHistoryScopeFingerprint() {
    var meta = getCurrentHistoryScopeMeta();
    return String((meta && meta.mode) || "") + "::" + String((meta && meta.scopeUserId) || "");
  }

  var __historyPageLastScopeFingerprint = "";

  function refreshHistoryIfScopeChanged() {
    var nextFp = getHistoryScopeFingerprint();
    if (!nextFp) return;
    if (__historyPageLastScopeFingerprint && __historyPageLastScopeFingerprint !== nextFp) {
      __historyPageLastScopeFingerprint = nextFp;
      loadHistory();
      return;
    }
    __historyPageLastScopeFingerprint = nextFp;
  }

  /** 删除单条：仅 RentalAIServerHistoryApi.deleteHistoryRecord；成功仅 loadHistory()，不出现登录门槛文案。 */
  function deleteHistoryRecordInScope(recordId) {
    var rid = String(recordId || "").trim();
    var err = document.getElementById("history-error");
    var Api = global.RentalAIServerHistoryApi;
    if (!rid) {
      if (err) {
        err.textContent = "Failed to delete history record";
        err.classList.remove("hidden");
      }
      return;
    }
    if (!Api || typeof Api.deleteHistoryRecord !== "function") {
      if (err) {
        err.textContent = "Failed to delete history record";
        err.classList.remove("hidden");
      }
      return;
    }
    Api.deleteHistoryRecord(rid).then(function (j) {
      if (j && j.success === true) {
        loadHistory();
        return;
      }
      if (err) {
        err.textContent = "Failed to delete history record";
        err.classList.remove("hidden");
      }
    }).catch(function () {
      if (err) {
        err.textContent = "Failed to delete history record";
        err.classList.remove("hidden");
      }
    });
  }

  /** 清空：仅 RentalAIServerHistoryApi.clearAllHistory；成功仅 loadHistory()。 */
  function clearHistoryInScope() {
    var err = document.getElementById("history-error");
    var Api = global.RentalAIServerHistoryApi;
    if (!Api || typeof Api.clearAllHistory !== "function") {
      if (err) {
        err.textContent = "Failed to clear history";
        err.classList.remove("hidden");
      }
      return;
    }
    Api.clearAllHistory().then(function (j) {
      if (j && j.success === true) {
        loadHistory();
        return;
      }
      if (err) {
        err.textContent = "Failed to clear history";
        err.classList.remove("hidden");
      }
    }).catch(function () {
      if (err) {
        err.textContent = "Failed to clear history";
        err.classList.remove("hidden");
      }
    });
  }

  function bindHistoryPageActionsOnce() {
    if (bindHistoryPageActionsOnce._done) return;
    bindHistoryPageActionsOnce._done = true;
    var tbody = document.getElementById("history-tbody");
    if (tbody) {
      tbody.addEventListener("click", function (ev) {
        var t = ev.target;
        if (!t || !t.closest) return;
        var btn = t.closest(".history-delete-one-btn");
        if (!btn) return;
        ev.preventDefault();
        var rid = btn.getAttribute("data-record-id");
        if (!rid) return;
        deleteHistoryRecordInScope(rid);
      });
    }
    var clearBtn = document.getElementById("history-clear-all-btn");
    if (clearBtn && !clearBtn.getAttribute("data-scope-clear-bound")) {
      clearBtn.setAttribute("data-scope-clear-bound", "1");
      clearBtn.addEventListener("click", function () {
        if (typeof global.confirm === "function" && !global.confirm("Clear all history in the current scope?")) {
          return;
        }
        clearHistoryInScope();
      });
    }
  }

  function bootHistoryPage() {
    bindHistoryPageActionsOnce();
    __historyPageLastScopeFingerprint = getHistoryScopeFingerprint();
    loadHistory();

    // 跨标签：同源 storage 变更时刷新作用域（非「必须登录」判断）
    if (!bootHistoryPage._storageBound) {
      bootHistoryPage._storageBound = true;
      try {
        global.addEventListener("storage", function (ev) {
          if (!ev || !ev.key) return;
          if (
            ev.key === "rentalai_bearer" ||
            ev.key === "rentalai_user_id" ||
            ev.key === "guest_session_id"
          ) {
            refreshHistoryIfScopeChanged();
          }
        });
      } catch (eSt) {}
    }

    // 同页登录/登出：storage 不可靠，轮询 fingerprint；仅变化时 loadHistory
    if (!bootHistoryPage._pollStarted) {
      bootHistoryPage._pollStarted = true;
      setInterval(function () {
        refreshHistoryIfScopeChanged();
      }, 1500);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootHistoryPage);
  } else {
    bootHistoryPage();
  }

  global.RentalAIHistoryPage = {
    loadHistory: loadHistory,
    deleteHistoryRecordInScope: deleteHistoryRecordInScope,
    clearHistoryInScope: clearHistoryInScope,
    refreshHistoryIfScopeChanged: refreshHistoryIfScopeChanged,
  };
})(window);
