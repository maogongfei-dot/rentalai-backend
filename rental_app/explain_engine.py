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


def explain_why_not(
    house: Dict[str, Any],
    result: Dict[str, Any],
    settings: Dict[str, Any] | None = None,
) -> List[str]:
    """
    Explain Engine Phase3:
    Generate negative/penalty reasons for why this listing is less recommended.

    house: original listing dict
    result: entry from rank_houses
    settings: state["settings"], may contain budget etc.
    """
    reasons: List[str] = []

    settings = settings or {}

    # 1) Budget issue: rent above budget
    budget = _to_float_safe(settings.get("budget"))
    rent = _to_float_safe(house.get("rent"))
    if budget is not None and rent is not None and rent > budget:
        reasons.append("Rent is above budget")

    # 2) Long commute (low commute score)
    base_detail = result.get("base_detail") or {}
    commute_info = base_detail.get("commute") or {}
    commute_points = _to_float_safe(commute_info.get("points"))
    if commute_points is None:
        commute_points = _to_float_safe(result.get("commute_score"))
    if commute_points is not None and commute_points <= 4:
        reasons.append("Long commute time")

    # 3) Area quality average/weak
    area_quality_score = _to_float_safe(result.get("area_quality_score"))
    if area_quality_score is not None and area_quality_score < 6:
        reasons.append("Area quality is average or weak")

    # 4) High risk listing
    risk_score = _to_float_safe(result.get("risk_score"))
    if risk_score is not None and risk_score >= 7:
        reasons.append("High risk listing")

    # 5) Bills not included
    bills = house.get("bills")
    if isinstance(bills, bool):
        if bills is False:
            reasons.append("Bills not included")
    elif bills is not None:
        # string-like flag
        text = str(bills).strip().lower()
        if text in ["no", "false", "n", "not included"]:
            reasons.append("Bills not included")

    return reasons


def generate_final_verdict(
    house: Dict[str, Any],
    result: Dict[str, Any],
    settings: Dict[str, Any] | None = None,
) -> str:
    """
    Explain Engine Phase4:
    Generate one-line AI verdict for this listing.
    """
    settings = settings or {}

    risk_score = _to_float_safe(result.get("risk_score"))
    final_score_raw = _to_float_safe(result.get("final_score"))

    # Normalize final_score into ~0-10 band if it looks like a 0-100 score
    if final_score_raw is None:
        final_band = None
    else:
        if final_score_raw > 10:
            final_band = final_score_raw / 10.0
        else:
            final_band = final_score_raw

    # 1) High risk: risk_score >= 9
    if risk_score is not None and risk_score >= 9:
        return "AI不推荐：高风险房源"

    # 2) Noticeable risk: risk_score >= 7
    if risk_score is not None and risk_score >= 7:
        return "AI谨慎：存在明显风险信号"

    # 3) Budget pressure: rent > budget and bills=False
    budget = _to_float_safe(settings.get("budget"))
    rent = _to_float_safe(house.get("rent"))
    bills = house.get("bills")
    bills_included = None
    if isinstance(bills, bool):
        bills_included = bills
    elif bills is not None:
        txt = str(bills).strip().lower()
        if txt in ["yes", "true", "y", "included"]:
            bills_included = True
        elif txt in ["no", "false", "n", "not included"]:
            bills_included = False

    if (
        budget is not None
        and rent is not None
        and rent > budget
        and bills_included is False
    ):
        return "AI不推荐：预算压力偏大"

    # 4) Strong overall, low risk
    if final_band is not None and risk_score is not None:
        if final_band >= 8 and risk_score <= 2:
            return "AI推荐：综合表现强，风险低"

    # 5) Generally good, low-to-moderate risk
    if final_band is not None and risk_score is not None:
        if final_band >= 6 and risk_score <= 4:
            return "AI可考虑：整体不错，适合进一步看房"

    # 6) Fallback
    return "AI中性：建议结合个人偏好继续比较"


def generate_overall_summary(
    top_results: List[Dict[str, Any]],
    settings: Dict[str, Any] | None = None,
) -> List[str]:
    """
    Explain Engine Phase5:
    Generate an overall summary for Top3 results.
    """
    summaries: List[str] = []
    settings = settings or {}
    budget = _to_float_safe(settings.get("budget"))

    for idx, res in enumerate(top_results, start=1):
        house = res.get("house", {}) or {}
        parts: List[str] = []

        # 1) Risk signal
        risk_score = _to_float_safe(res.get("risk_score"))
        if risk_score is not None and risk_score >= 7:
            parts.append("该房源存在明显风险信号")

        # 2) Rent vs budget
        rent = _to_float_safe(house.get("rent"))
        if budget is not None and rent is not None and rent < budget:
            parts.append("价格低于预算")

        # 3) Bills included or not
        bills = house.get("bills")
        bills_included = None
        if isinstance(bills, bool):
            bills_included = bills
        elif bills is not None:
            txt = str(bills).strip().lower()
            if txt in ["yes", "true", "y", "included"]:
                bills_included = True
            elif txt in ["no", "false", "n", "not included"]:
                bills_included = False
        if bills_included is False:
            parts.append("不包含 bills")

        # 4) Area quality
        area_quality_score = _to_float_safe(res.get("area_quality_score"))
        if area_quality_score is not None and area_quality_score < 6:
            parts.append("区域质量一般")

        if not parts:
            summary = f"Top{idx} 房源暂无明显优劣点，建议结合个人偏好进一步查看"
        else:
            summary = f"Top{idx} 房源：" + "，".join(parts)
        summaries.append(summary)

    return summaries


def generate_confidence_level(house: Dict[str, Any], result: Dict[str, Any]) -> str:
    """
    Explain Engine MVP Phase2:
    Generate a simple confidence level: High / Medium / Low.
    """
    risk_score = _to_float_safe(result.get("risk_score"))
    final_score = _to_float_safe(result.get("final_score"))

    # Defensive defaults
    if risk_score is None:
        risk_score = 0.0
    if final_score is None:
        final_score = 0.0

    # 1) High risk -> Low confidence
    if risk_score >= 7:
        return "Low"

    # 2) Strong score & low risk -> High
    if final_score >= 8 and risk_score <= 2:
        return "High"

    # 3) Good score & low-moderate risk -> Medium
    if final_score >= 6 and risk_score <= 4:
        return "Medium"

    # 4) Low score -> Low
    if final_score < 6:
        return "Low"

    # 5) Fallback
    return "Medium"

