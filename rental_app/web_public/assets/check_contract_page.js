/**
 * Phase 5 Step 3: /check-contract mock page.
 * No backend/API integration in this step.
 */
(function () {
  function listFromInput(raw, fallback) {
    var text = (raw || "").trim();
    if (!text) return fallback.slice();
    var parts = text
      .split(/[.\n;]/)
      .map(function (s) {
        return s.trim();
      })
      .filter(Boolean);
    return (parts.length ? parts : fallback).slice(0, 4);
  }

  function setList(id, items) {
    var el = document.getElementById(id);
    if (!el) return;
    el.innerHTML = "";
    items.forEach(function (item) {
      var li = document.createElement("li");
      li.textContent = item;
      el.appendChild(li);
    });
  }

  function renderMock(contractText, fileName) {
    var conclusion = document.getElementById("contract-result-conclusion");
    var nextStep = document.getElementById("contract-result-next-step");
    var result = document.getElementById("contract-result");
    if (!result || !conclusion || !nextStep) return;

    var risks = listFromInput(contractText, [
      "Ambiguous repair responsibilities between tenant and landlord.",
      "Deposit deductions are broad and not clearly evidenced.",
      "Early termination terms may include disproportionate penalties.",
    ]);
    var confirmItems = [
      "Whether rent includes any bills or council tax.",
      "Exact notice period and break clause activation date.",
      fileName ? "Whether uploaded annexes are part of the signed agreement." : "Whether any annex pages are missing.",
    ];
    var questions = [
      "Can you provide an itemised list of all fees due before move-in?",
      "How are emergency repair requests handled and within what SLA?",
      "Can we add a written cap or process for fair wear-and-tear disputes?",
    ];

    conclusion.textContent =
      "Potentially signable, but several clauses need clarification before commitment. This preview is a local mock only.";
    nextStep.textContent =
      "Share these risk points with the landlord/agent, request written clarifications, then run a full legal/AI review in the production workflow.";

    setList("contract-result-risks", risks);
    setList("contract-result-confirm", confirmItems);
    setList("contract-result-questions", questions);
    result.classList.remove("hidden");
    result.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function runAnalyze() {
    var input = document.getElementById("contract-paste-input");
    var fileInput = document.getElementById("contract-file-input");
    var err = document.getElementById("contract-analyze-err");
    var btn = document.getElementById("contract-analyze-btn");
    if (!input || !fileInput) return;

    var text = (input.value || "").trim();
    var fileName = fileInput.files && fileInput.files[0] ? fileInput.files[0].name : "";
    if (!text && !fileName) {
      if (err) {
        err.textContent = "Paste contract content or select a file first.";
        err.classList.remove("hidden");
      }
      return;
    }
    if (err) {
      err.textContent = "";
      err.classList.add("hidden");
    }

    if (btn) {
      btn.disabled = true;
      btn.setAttribute("aria-busy", "true");
    }
    window.setTimeout(function () {
      renderMock(text, fileName);
      if (btn) {
        btn.disabled = false;
        btn.setAttribute("aria-busy", "false");
      }
    }, 420);
  }

  document.addEventListener("DOMContentLoaded", function () {
    var fileInput = document.getElementById("contract-file-input");
    var fileHint = document.getElementById("contract-file-hint");
    var button = document.getElementById("contract-analyze-btn");
    if (button) button.addEventListener("click", runAnalyze);
    if (fileInput && fileHint) {
      fileInput.addEventListener("change", function () {
        var fileName = fileInput.files && fileInput.files[0] ? fileInput.files[0].name : "";
        fileHint.textContent = fileName ? "Selected: " + fileName : "No file selected.";
      });
    }
  });
})();
