from __future__ import annotations

from typing import Any, Dict, List


# Module3 Phase1: Contract Risk Engine (minimal runnable skeleton)
RISK_KEYWORDS: Dict[str, Dict[str, List[str]]] = {
    "deposit_risk": {
        "high": [
            "non-refundable deposit",
            "deposit before viewing",
            "pay deposit before viewing",
            "cash deposit",
            "cash only",
            "deposit today",
            "holding deposit non refundable",
            "押金不退",
            "先付押金",
        ],
        "medium": [
            "deposit required",
            "holding deposit",
            "reservation fee",
            "advance deposit",
            "提前押金",
        ],
    },
    "scam_risk": {
        "high": [
            "bank transfer only",
            "urgent payment",
            "no viewing",
            "pay now",
            "send money",
            "western union",
            "crypto only",
            "gift card",
            "wire transfer only",
            "不看房",
            "立刻转账",
        ],
        "medium": [
            "overseas landlord",
            "out of country",
            "can't meet",
            "keys will be mailed",
            "agent not available",
        ],
    },
    "contract_risk": {
        "high": [
            "no contract",
            "verbal only",
            "informal agreement",
            "no tenancy agreement",
            "no paperwork",
            "不签合同",
            "口头协议",
        ],
        "medium": [
            "contract later",
            "we can discuss later",
            "no written agreement",
            "skip references",
        ],
    },
    "pressure_risk": {
        "high": [
            "decide today",
            "last chance",
            "pay today",
            "first come first served",
            "must pay now",
            "今天决定",
            "马上决定",
        ],
        "medium": [
            "many people interested",
            "lots of interest",
            "high demand",
            "limited time",
            "urgent",
        ],
    },
}


def _norm_text(text: Any) -> str:
    if text is None:
        return ""
    return str(text).strip().lower()


def _dedupe_preserve_order(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for x in items:
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def _to_float(x: Any) -> float | None:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip().lower()
    if not s:
        return None
    # keep digits and dot only
    filtered = "".join(ch for ch in s if (ch.isdigit() or ch == "."))
    if not filtered:
        return None
    try:
        return float(filtered)
    except ValueError:
        return None


def _get_text_fields(listing: Dict[str, Any], keys: List[str]) -> str:
    parts: List[str] = []
    for k in keys:
        v = listing.get(k)
        if v is None:
            continue
        s = str(v).strip()
        if s:
            parts.append(s)
    return " ".join(parts)


def calculate_structured_risk_score(listing: Dict[str, Any] | None) -> Dict[str, Any]:
    """
    Structured risk engine (Module3 Phase2 - first half).
    Input: listing dict (safe for None/missing fields)
    Output:
      {
        "structured_risk_score": 0-10,
        "matched_rules": list[str],
        "risk_reasons": list[str]
      }
    """
    if not isinstance(listing, dict):
        return {
            "structured_risk_score": 0,
            "matched_rules": [],
            "risk_reasons": ["listing is None/invalid; default low risk."],
        }

    matched_rules: List[str] = []
    risk_reasons: List[str] = []
    points = 0

    # Gather free-text signals from multiple fields (safe)
    text = _norm_text(
        _get_text_fields(
            listing,
            [
                "notes",
                "description",
                "contract_text",
                "payment_method",
                "deposit",
                "holding_deposit",
            ],
        )
    )

    # --- Rule group 1: Deposit / holding deposit ---
    rent = _to_float(listing.get("rent"))
    deposit_amount = _to_float(listing.get("deposit_amount"))
    if deposit_amount is None:
        # allow "deposit" field to be numeric-like
        deposit_amount = _to_float(listing.get("deposit"))

    if rent is not None and deposit_amount is not None:
        # risk if deposit > 1.5 months rent (simplified threshold)
        if deposit_amount > 1.5 * rent:
            matched_rules.append("deposit_too_high")
            risk_reasons.append(f"Deposit amount unusually high vs rent: deposit={deposit_amount}, rent={rent}")
            points += 3

    holding_deposit = listing.get("holding_deposit")
    holding_text = _norm_text(holding_deposit)
    if holding_text and ("non-refundable" in holding_text or "non refundable" in holding_text):
        matched_rules.append("holding_deposit_non_refundable")
        risk_reasons.append("Holding deposit described as non-refundable.")
        points += 4

    # --- Rule group 2: Payment method / urgent payment ---
    if any(k in text for k in ["cash only", "bank transfer only", "pay now", "urgent payment"]):
        matched_rules.append("suspicious_payment_terms")
        risk_reasons.append("Suspicious payment terms detected (cash only / bank transfer only / pay now / urgent payment).")
        points += 3

    # --- Rule group 3: Viewing availability ---
    viewing_available = listing.get("viewing_available")
    viewing = listing.get("viewing")
    if viewing_available is False:
        matched_rules.append("no_viewing_flag")
        risk_reasons.append("Viewing available flag is False.")
        points += 4
    if isinstance(viewing, str) and "unavailable" in _norm_text(viewing):
        matched_rules.append("viewing_unavailable_text")
        risk_reasons.append("Viewing marked unavailable.")
        points += 4
    if any(k in text for k in ["no viewing", "viewing unavailable"]):
        matched_rules.append("no_viewing_text")
        risk_reasons.append("No viewing mentioned in text.")
        points += 4

    # --- Rule group 4: Contract availability ---
    contract_available = listing.get("contract_available")
    contract = listing.get("contract")
    if contract_available is False:
        matched_rules.append("no_contract_flag")
        risk_reasons.append("Contract available flag is False.")
        points += 3
    if isinstance(contract, str) and any(k in _norm_text(contract) for k in ["no contract", "verbal only"]):
        matched_rules.append("no_contract_text_field")
        risk_reasons.append("Contract field indicates no contract / verbal only.")
        points += 3
    if any(k in text for k in ["no contract", "verbal only"]):
        matched_rules.append("no_contract_text")
        risk_reasons.append("No contract / verbal only mentioned in text.")
        points += 3

    # --- Rule group 5: Bills ambiguity ---
    if any(k in text for k in ["bills not clear", "ask later", "depends"]):
        matched_rules.append("bills_unclear")
        risk_reasons.append("Bills information unclear (bills not clear / ask later / depends).")
        points += 2

    # --- Rule group 6: Verification flags (if present) ---
    if "landlord_verified" in listing and listing.get("landlord_verified") is False:
        matched_rules.append("landlord_not_verified")
        risk_reasons.append("Landlord explicitly not verified.")
        points += 2
    if "agent_verified" in listing and listing.get("agent_verified") is False:
        matched_rules.append("agent_not_verified")
        risk_reasons.append("Agent explicitly not verified.")
        points += 2

    # --- Combination escalation ---
    has_no_viewing = any(r.startswith("no_viewing") or r.startswith("viewing_") for r in matched_rules)
    has_transfer_only = "suspicious_payment_terms" in matched_rules and ("bank transfer only" in text)
    has_cash_only = "suspicious_payment_terms" in matched_rules and ("cash only" in text)
    has_urgent = "suspicious_payment_terms" in matched_rules and (("urgent payment" in text) or ("pay now" in text))
    has_no_contract = any(r.startswith("no_contract") for r in matched_rules)
    has_deposit_issue = any(r.startswith("deposit_") or r.startswith("holding_deposit") for r in matched_rules)

    if has_no_viewing and has_transfer_only:
        matched_rules.append("combo_no_viewing_transfer_only")
        risk_reasons.append("High-risk combo: no viewing + bank transfer only.")
        points += 4
    if has_no_contract and has_deposit_issue:
        matched_rules.append("combo_no_contract_deposit")
        risk_reasons.append("High-risk combo: no contract + deposit issue.")
        points += 3
    if has_urgent and has_cash_only:
        matched_rules.append("combo_urgent_cash_only")
        risk_reasons.append("High-risk combo: urgent payment + cash only.")
        points += 3

    matched_rules = _dedupe_preserve_order(matched_rules)
    risk_reasons = _dedupe_preserve_order(risk_reasons)

    # --- Map points -> 0~10 (stable bands) ---
    if not matched_rules:
        score = 1
    else:
        if points <= 3:
            score = 3
        elif points <= 7:
            score = 6
        elif points <= 11:
            score = 8
        else:
            score = 10

    score = max(0, min(10, int(score)))
    return {
        "structured_risk_score": score,
        "matched_rules": matched_rules,
        "risk_reasons": risk_reasons,
    }


def calculate_risk_penalty(score: int | float | None) -> float:
    """
    Map structured_risk_score (0-10) to a numeric penalty added to final_score.
    Spec:
      0-1  ->  0
      2-3  -> -0.5
      4-6  -> -1.5
      7-8  -> -3
      9-10 -> -5
    """
    if score is None:
        return 0.0
    try:
        v = float(score)
    except (TypeError, ValueError):
        return 0.0
    if v < 0:
        v = 0.0
    if v > 10:
        v = 10.0

    if v <= 1:
        return 0.0
    if v <= 3:
        return -0.5
    if v <= 6:
        return -1.5
    if v <= 8:
        return -3.0
    return -5.0


def calculate_contract_risk_score(text: str | None) -> Dict[str, Any]:
    """
    Input: listing/contract description text (string)
    Output:
      - risk_score: 0~10
      - matched_categories: list[str]
      - matched_keywords: list[str]
      - risk_reasons: list[str]

    Simple substring matching; safe for None/empty; case-insensitive.
    """
    t = _norm_text(text)
    if not t:
        return {
            "risk_score": 0,
            "matched_categories": [],
            "matched_keywords": [],
            "risk_reasons": ["No text provided; default low risk."],
        }

    matched_categories: List[str] = []
    matched_keywords: List[str] = []
    risk_reasons: List[str] = []

    points = 0
    high_hits = 0
    medium_hits = 0

    for cat, levels in RISK_KEYWORDS.items():
        cat_hits: List[str] = []

        for kw in levels.get("high", []):
            k = _norm_text(kw)
            if k and k in t:
                cat_hits.append(kw)
                matched_keywords.append(kw)
                points += 3
                high_hits += 1

        for kw in levels.get("medium", []):
            k = _norm_text(kw)
            if k and k in t:
                cat_hits.append(kw)
                matched_keywords.append(kw)
                points += 1
                medium_hits += 1

        if cat_hits:
            matched_categories.append(cat)
            risk_reasons.append(f"{cat} matched: {', '.join(_dedupe_preserve_order(cat_hits))}")

    # Escalation rules (obvious scam/deposit combination)
    has_scam = "scam_risk" in matched_categories
    has_deposit = "deposit_risk" in matched_categories
    has_contract = "contract_risk" in matched_categories
    has_pressure = "pressure_risk" in matched_categories

    if has_scam and has_deposit and (high_hits >= 2):
        points += 4
        risk_reasons.append("Escalation: scam + deposit high-risk combination.")
    if has_pressure and has_scam and high_hits >= 1:
        points += 2
        risk_reasons.append("Escalation: pressure + suspicious payment signals.")
    if has_contract and has_deposit and high_hits >= 1:
        points += 1
        risk_reasons.append("Escalation: no contract + deposit-related risk.")

    # Map points -> 0~10 (simplified, stable)
    total_hits = high_hits + medium_hits
    if total_hits == 0:
        risk_score = 1
    else:
        # base by points then clamp
        risk_score = max(0, min(10, int(round(points))))
        # ensure "few general risks" falls into 2~4
        if risk_score < 2 and total_hits >= 1:
            risk_score = 2
        if risk_score > 10:
            risk_score = 10

    matched_categories = _dedupe_preserve_order(matched_categories)
    matched_keywords = _dedupe_preserve_order(matched_keywords)

    return {
        "risk_score": risk_score,
        "matched_categories": matched_categories,
        "matched_keywords": matched_keywords,
        "risk_reasons": risk_reasons,
    }

