/**
 * Phase 5 Step 4: /compare mock experience.
 * No backend/API calls in this step.
 */
(function () {
  var MIN_PROPERTIES = 2;
  var nextPropertyId = 1;

  function propertyTemplate(id) {
    return (
      '<article class="compare-property-card card-muted" data-property-id="' +
      id +
      '">' +
      '<div class="compare-property-head">' +
      '<h3 class="subsection-title">Property ' +
      id +
      "</h3>" +
      '<button type="button" class="compare-remove-btn" data-remove-id="' +
      id +
      '" aria-label="Remove property ' +
      id +
      '">Remove</button>' +
      "</div>" +
      '<div class="field-row">' +
      '<div class="field-col"><label class="field-label">rent (£/month)<input class="compare-input compare-rent" type="text" inputmode="decimal" placeholder="e.g. 1400" /></label></div>' +
      '<div class="field-col"><label class="field-label">postcode<input class="compare-input compare-postcode" type="text" placeholder="e.g. E14 9TP" /></label></div>' +
      "</div>" +
      '<div class="field-row">' +
      '<div class="field-col"><label class="field-label">bills included or not<select class="compare-input compare-bills"><option value="">Select</option><option value="yes">Bills included</option><option value="no">Bills not included</option><option value="partial">Partially included</option></select></label></div>' +
      '<div class="field-col"><label class="field-label">bedrooms<input class="compare-input compare-bedrooms" type="text" inputmode="numeric" placeholder="e.g. 2" /></label></div>' +
      "</div>" +
      '<label class="field-label">notes / property link<textarea class="compare-input compare-notes" rows="3" placeholder="Listing link, condition notes, commute, landlord comments..."></textarea></label>' +
      "</article>"
    );
  }

  function parseMoney(value) {
    var n = parseFloat(String(value || "").replace(/[^0-9.]/g, ""));
    return isNaN(n) ? null : n;
  }

  function scoreProperty(p) {
    var score = 50;
    if (p.rent != null) score += Math.max(0, 1600 - p.rent) / 40;
    if (p.bills === "yes") score += 10;
    if (p.bills === "partial") score += 4;
    if (p.bedrooms != null) score += Math.min(3, p.bedrooms) * 4;
    if (p.postcode) score += 3;
    if (p.notes && /mould|leak|damp|agency fee|unclear|penalty/i.test(p.notes)) score -= 8;
    return Math.round(score * 10) / 10;
  }

  function computeRiskLevel(p) {
    var risk = 55;
    if (p.bills === "yes") risk -= 8;
    if (p.notes && /new|renovated|managed|licensed/i.test(p.notes)) risk -= 4;
    if (p.notes && /unclear|missing|penalty|damp|mould|leak|dispute/i.test(p.notes)) risk += 15;
    if (p.rent != null && p.rent > 1800) risk += 5;
    return Math.max(5, Math.min(95, Math.round(risk)));
  }

  function readProperties() {
    var cards = document.querySelectorAll(".compare-property-card");
    var out = [];
    var i;
    for (i = 0; i < cards.length; i++) {
      var c = cards[i];
      var rent = parseMoney(c.querySelector(".compare-rent").value);
      var bedroomsRaw = parseFloat((c.querySelector(".compare-bedrooms").value || "").trim());
      out.push({
        label: "Property " + (i + 1),
        rent: rent,
        postcode: (c.querySelector(".compare-postcode").value || "").trim(),
        bills: (c.querySelector(".compare-bills").value || "").trim(),
        bedrooms: isNaN(bedroomsRaw) ? null : bedroomsRaw,
        notes: (c.querySelector(".compare-notes").value || "").trim(),
      });
    }
    return out;
  }

  function updateRemoveButtons() {
    var cards = document.querySelectorAll(".compare-property-card");
    var canRemove = cards.length > MIN_PROPERTIES;
    var i;
    for (i = 0; i < cards.length; i++) {
      var btn = cards[i].querySelector(".compare-remove-btn");
      if (btn) btn.disabled = !canRemove;
    }
  }

  function setText(id, text) {
    var el = document.getElementById(id);
    if (el) el.textContent = text;
  }

  function setList(id, rows) {
    var el = document.getElementById(id);
    if (!el) return;
    el.innerHTML = "";
    rows.forEach(function (r) {
      var li = document.createElement("li");
      li.textContent = r;
      el.appendChild(li);
    });
  }

  function runCompare() {
    var err = document.getElementById("compare-run-err");
    var resultCard = document.getElementById("compare-result-card");
    var btn = document.getElementById("compare-run-btn");
    var properties = readProperties();
    if (properties.length < MIN_PROPERTIES) {
      if (err) {
        err.textContent = "Please add at least two properties.";
        err.classList.remove("hidden");
      }
      return;
    }
    if (err) {
      err.textContent = "";
      err.classList.add("hidden");
    }

    var anySignals = properties.some(function (p) {
      return p.rent != null || p.postcode || p.notes || p.bedrooms != null;
    });
    if (!anySignals) {
      if (err) {
        err.textContent = "Please fill in some property details before comparing.";
        err.classList.remove("hidden");
      }
      return;
    }

    if (btn) {
      btn.disabled = true;
      btn.setAttribute("aria-busy", "true");
    }

    window.setTimeout(function () {
      var scored = properties.map(function (p) {
        return {
          item: p,
          score: scoreProperty(p),
          risk: computeRiskLevel(p),
        };
      });

      var best = scored.slice().sort(function (a, b) {
        return b.score - a.score;
      })[0];
      var cheapest = scored
        .filter(function (s) {
          return s.item.rent != null;
        })
        .sort(function (a, b) {
          return a.item.rent - b.item.rent;
        })[0];
      var lowRisk = scored.slice().sort(function (a, b) {
        return a.risk - b.risk;
      })[0];

      var watchOut = [];
      scored.forEach(function (s) {
        if (s.item.bills === "no") {
          watchOut.push(s.item.label + ": bills are excluded from listed rent.");
        }
        if (s.risk >= 65) {
          watchOut.push(s.item.label + ": higher risk signals in notes/terms, verify carefully.");
        }
      });
      if (!watchOut.length) {
        watchOut.push("No strong red flags from this mock input, but verify contract details and repair responsibilities.");
      }

      setText(
        "compare-result-best",
        best.item.label +
          " appears strongest overall in this mock comparison (score " +
          best.score +
          ")."
      );
      setText(
        "compare-result-cheapest",
        cheapest
          ? cheapest.item.label + " has the lowest listed monthly rent (£" + cheapest.item.rent + ")."
          : "No rent values were entered, so cheapest option cannot be determined."
      );
      setText(
        "compare-result-low-risk",
        lowRisk.item.label + " looks lowest risk in this draft review (risk index " + lowRisk.risk + "/100)."
      );
      setList("compare-result-watch-out", watchOut.slice(0, 5));
      setText(
        "compare-result-advice",
        "Shortlist the best and cheapest options, then ask follow-up questions on bills, maintenance, and contract clauses before paying any holding deposit."
      );

      resultCard.classList.remove("hidden");
      resultCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
      if (btn) {
        btn.disabled = false;
        btn.setAttribute("aria-busy", "false");
      }
    }, 420);
  }

  function addPropertyCard() {
    var host = document.getElementById("compare-property-list");
    if (!host) return;
    host.insertAdjacentHTML("beforeend", propertyTemplate(nextPropertyId));
    nextPropertyId += 1;
    updateRemoveButtons();
  }

  document.addEventListener("DOMContentLoaded", function () {
    var host = document.getElementById("compare-property-list");
    var addBtn = document.getElementById("compare-add-property-btn");
    var runBtn = document.getElementById("compare-run-btn");
    if (!host) return;

    addPropertyCard();
    addPropertyCard();

    if (addBtn) addBtn.addEventListener("click", addPropertyCard);
    if (runBtn) runBtn.addEventListener("click", runCompare);
    host.addEventListener("click", function (ev) {
      var btn = ev.target.closest(".compare-remove-btn");
      if (!btn) return;
      var cards = host.querySelectorAll(".compare-property-card");
      if (cards.length <= MIN_PROPERTIES) return;
      var card = btn.closest(".compare-property-card");
      if (card) card.remove();
      updateRemoveButtons();
    });
  });
})();
