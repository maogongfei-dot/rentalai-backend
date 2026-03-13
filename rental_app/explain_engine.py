from __future__ import annotations

from typing import Any, Dict, List


def _to_float_safe(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def explain_score(house: Dict[str, Any], result: Dict[str, Any]) -> List[str]:
    """
    Explain Engine Phase1:
    Generate human-readable recommendation reasons based on existing scores.

    house: original listing dict
    result: entry from rank_houses (contains final_score, area_quality_score, risk_score, etc.)
    """
    reasons: List[str] = []

    # 1) Rent advantage: use price dimension from base_detail if available
    base_detail = result.get("base_detail") or {}
    price_info = base_detail.get("price") or {}
    rent_points = _to_float_safe(price_info.get("points"))
    if rent_points is None:
        # fallback: maybe a normalized price_score field was added later
        rent_points = _to_float_safe(result.get("price_score"))

    if rent_points is not None and rent_points >= 7:
        reasons.append("Rent is competitive for the area")

    # 2) Commute advantage
    commute_info = base_detail.get("commute") or {}
    commute_points = _to_float_safe(commute_info.get("points"))
    if commute_points is None:
        commute_points = _to_float_safe(result.get("commute_score"))

    if commute_points is not None and commute_points >= 7:
        reasons.append("Short commute time")

    # 3) Area quality
    area_quality_score = _to_float_safe(result.get("area_quality_score"))
    if area_quality_score is not None and area_quality_score >= 7:
        reasons.append("Good area quality")

    # 4 & 5) Risk level (structured_risk_score already mapped into risk_score)
    risk_score = _to_float_safe(result.get("risk_score"))
    if risk_score is not None:
        if risk_score <= 2:
            reasons.append("Low risk listing")
        elif risk_score >= 7:
            reasons.append("High risk listing")

    return reasons

