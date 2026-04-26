/**
 * Phase 5 Step 2: /start — mock only, no /api/ai/* calls.
 */
(function () {
  function buildMockResponse(text) {
    return (
      "This is a placeholder response (demo). In the full product, RentalAI will connect to the analysis service.\n\n" +
      "---\n" +
      "Summary (mock): We would review your postcode, rent level, contract clauses, and any repair or deposit concerns you mentioned.\n\n" +
      "Your input:\n" +
      text
    );
  }

  function runMock() {
    var input = document.getElementById("start-analysis-input");
    var out = document.getElementById("start-analysis-result");
    var body = document.getElementById("start-analysis-result-body");
    var err = document.getElementById("start-analysis-err");
    var btn = document.getElementById("start-analyze-btn");
    if (!input || !out || !body) return;

    var text = (input.value || "").trim();
    if (!text) {
      if (err) {
        err.classList.remove("hidden");
        err.textContent = "Please add a few details to analyse.";
      }
      return;
    }
    if (err) {
      err.classList.add("hidden");
      err.textContent = "";
    }

    if (btn) {
      btn.disabled = true;
      btn.setAttribute("aria-busy", "true");
    }
    body.textContent = "";

    window.setTimeout(function () {
      body.textContent = buildMockResponse(text);
      out.classList.remove("hidden");
      out.scrollIntoView({ behavior: "smooth", block: "nearest" });
      if (btn) {
        btn.disabled = false;
        btn.setAttribute("aria-busy", "false");
      }
    }, 450);
  }

  document.addEventListener("DOMContentLoaded", function () {
    var btn = document.getElementById("start-analyze-btn");
    var input = document.getElementById("start-analysis-input");
    if (btn) btn.addEventListener("click", runMock);
    if (input) {
      input.addEventListener("keydown", function (e) {
        if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
          e.preventDefault();
          runMock();
        }
      });
    }
  });
})();
