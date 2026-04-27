/**
 * Phase 5 Step 5: unified result page with mock data only.
 * This script intentionally avoids backend/API integration.
 */
(function () {
  var mock = {
    recommendation: "Caution",
    why: [
      "Rent is slightly above the ideal budget range",
      "Bills are unclear in the listing",
      "Location is acceptable but commute needs checking",
    ],
    mainRisks: [
      "Contract risk: unclear break clause",
      "Cost risk: bills not confirmed",
      "Location risk: limited transport information",
      "Agency risk: reputation needs checking",
    ],
    nextStep: [
      "Ask the landlord or agent to confirm bills",
      "Request the full contract before paying deposit",
      "Check commute time before booking a viewing",
    ],
    locationInsight: [
      "Area appears suitable for basic living needs",
      "Transport and nearby amenities should be verified",
    ],
    reputationCheck: [
      "No confirmed high-risk record found",
      "Agency/address reputation should be checked before payment",
    ],
  };

  function renderList(id, items) {
    var el = document.getElementById(id);
    if (!el) return;
    el.innerHTML = "";
    items.forEach(function (item) {
      var li = document.createElement("li");
      li.textContent = item;
      el.appendChild(li);
    });
  }

  function applyRecommendationStyle(label) {
    var badge = document.getElementById("analysis-recommendation-badge");
    if (!badge) return;
    var v = String(label || "")
      .trim()
      .toLowerCase()
      .replace(/[_-]+/g, " ");
    badge.textContent = label;
    badge.classList.remove(
      "analysis-recommendation--recommended",
      "analysis-recommendation--caution",
      "analysis-recommendation--not-recommended",
      "analysis-recommendation--need-more-information"
    );
    if (v === "recommended") {
      badge.classList.add("analysis-recommendation--recommended");
    } else if (v === "not recommended") {
      badge.classList.add("analysis-recommendation--not-recommended");
    } else if (v === "need more information" || v === "more information needed") {
      badge.classList.add("analysis-recommendation--need-more-information");
    } else {
      badge.classList.add("analysis-recommendation--caution");
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    applyRecommendationStyle(mock.recommendation);
    renderList("analysis-why-list", mock.why);
    renderList("analysis-risks-list", mock.mainRisks);
    renderList("analysis-next-step-list", mock.nextStep);
    renderList("analysis-location-list", mock.locationInsight);
    renderList("analysis-reputation-list", mock.reputationCheck);
  });
})();
