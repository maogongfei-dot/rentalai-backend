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

