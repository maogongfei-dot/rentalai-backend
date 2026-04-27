/**
 * Phase 5 Step 5: unified result page with mock data only.
 * This script intentionally avoids backend/API integration.
 */
(function () {
  var RESULT_STORAGE_KEY = "rentalai_latest_result_v1";

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

  function readStoredResult() {
    try {
      var raw = localStorage.getItem(RESULT_STORAGE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  }

  function toList(v) {
    if (Array.isArray(v)) return v.filter(Boolean).map(String);
    if (v == null || v === "") return [];
    return [String(v)];
  }

  function mapApiToResultShape(stored) {
    if (!stored || !stored.response || typeof stored.response !== "object") return null;
    var resp = stored.response;
    var data = resp && typeof resp.data === "object" ? resp.data : {};
    var decision = data && typeof data.decision === "object" ? data.decision : {};
    var status = data && typeof data.status === "object" ? data.status : {};
    var analysis = data && typeof data.analysis === "object" ? data.analysis : {};
    var userFacing = data && typeof data.user_facing === "object" ? data.user_facing : {};
    var explainResult = data && typeof data.explain_result === "object" ? data.explain_result : {};

    var recommendation =
      status.overall_recommendation ||
      decision.final_summary ||
      decision.action ||
      mock.recommendation;
    var finalScore = data.score != null ? data.score : resp.final_score;

    var reasons = toList(analysis.supporting_reasons);
    if (!reasons.length) reasons = toList(explainResult.recommended_reasons);
    if (!reasons.length) reasons = toList(userFacing.reasoning_note || userFacing.summary);

    var risks = toList(analysis.primary_blockers);
    if (!risks.length) risks = toList(explainResult.risks);
    if (!risks.length) risks = toList(userFacing.risk_note);

    var nextSteps = toList(data.next_actions);
    if (!nextSteps.length) nextSteps = toList(userFacing.next_step);

    return {
      recommendation: String(recommendation),
      finalScore: finalScore,
      why: reasons.length ? reasons : mock.why,
      mainRisks: risks.length ? risks : mock.mainRisks,
      nextStep: nextSteps.length ? nextSteps : mock.nextStep,
      locationInsight: mock.locationInsight,
      reputationCheck: mock.reputationCheck,
    };
  }

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
    var stored = readStoredResult();
    var realResult = mapApiToResultShape(stored);
    var view = realResult || mock;

    applyRecommendationStyle(view.recommendation);
    renderList("analysis-why-list", view.why);
    renderList("analysis-risks-list", view.mainRisks);
    renderList("analysis-next-step-list", view.nextStep);
    renderList("analysis-location-list", view.locationInsight);
    renderList("analysis-reputation-list", view.reputationCheck);

    var badge = document.getElementById("analysis-recommendation-badge");
    if (badge && view.finalScore != null && view.finalScore !== "") {
      badge.textContent = String(view.recommendation) + " · score " + String(view.finalScore);
    }
  });
})();
