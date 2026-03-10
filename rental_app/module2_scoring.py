from __future__ import annotations
import math
from typing import Optional, Tuple

from area_module import get_area_score

DEFAULT_WEIGHTS = {
    "price": 35,
    "commute": 30,
    "bills": 15,
    "area": 10,
    "bedrooms": 10,
}

from module5_area.area_service import AreaService

def score_commute(commute_mins):
    if commute_mins is None:
        return 0, "commute_mins 缺失，不计分"

    m = int(commute_mins)
    if m <= 30:
        return 8, f"通勤 {m}min 很好 +8"
    if m <= 45:
        return 4, f"通勤 {m}min OK +4"
    if m <= 60:
        return 0, f"通勤 {m}min 一般 0"
    if m <= 75:
        return -4, f"通勤 {m}min 偏久 -4"
    return -8, f"通勤 {m}min 很久 -8"

def filter_houses(houses, prefs):
    """返回通过硬性条件的房源列表（例如预算、区域、bills等）"""
    return []


from typing import Dict, Any, List, Tuple



def calc_price_score(rent_pcm: Optional[float], budget_pcm: Optional[float]) -> Tuple[Optional[float], str]:
    """
    Return (score 0-100 or None, reason)
    Rule:
      - <=60% budget: flat good but not max (avoid weird-low listings)
      - 60%~90%: ramp up to 100
      - 90%~100%: slightly down to 95 (still great)
      - >100%: drop fast by bands
    """
    if rent_pcm is None or budget_pcm is None or budget_pcm <= 0:
        return None, "Missing rent/budget"

    r, b = float(rent_pcm), float(budget_pcm)
    ratio = r / b

    if ratio <= 0.60:
        return 75.0, "Very cheap vs budget"
    if ratio <= 0.90:
        # 0.60 -> 75, 0.90 -> 100
        score = 75.0 + (ratio - 0.60) / 0.30 * 25.0
        return score, "Under budget"
    if ratio <= 1.00:
        # 0.90 -> 100, 1.00 -> 95
        score = 100.0 - (ratio - 0.90) / 0.10 * 5.0
        return score, "Near budget"

    # Over budget: banded drops
    if ratio <= 1.05:
        return 80.0, "Slightly over budget"
    if ratio <= 1.10:
        return 65.0, "Over budget"
    if ratio <= 1.20:
        return 40.0, "Too expensive"

    # >120%: slide to 0 by 200%
    score = max(0.0, 40.0 * (1.0 - (ratio - 1.20) / 0.80))
    return score, "Far over budget"


def _to_float(x: Any, default: float | None = None) -> float | None:
    """Try convert to float; return default on failure."""
    if x is None:
        return default
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def _to_int(x: Any, default: int | None = None) -> int | None:
    """Try convert to int; return default on failure."""
    if x is None:
        return default
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return default


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))

def score_distance(distance):
    if distance is None:
        return 0

    if distance <= 1:
        return 20
    elif distance <= 3:
        return 15
    elif distance <= 5:
        return 10
    elif distance <= 8:
        return 5
    else:
        return 0

def score_house(house, prefs, weights):

    if not isinstance(house, dict):
        return 0, {"error": "house data invalid"}
    
    """返回 (score, breakdown)  breakdown用于解释（加分/扣分明细）"""
    breakdown = {}
    breakdown["penalties"] = []
    score = 0
    
    distance = house.get("distance_to_target", None)
    distance_score = score_distance(distance) if distance is not None else 0

    # --- PRICE ---
    rent = house.get("rent")
    budget_max = prefs.get("budget")
    if budget_max is None:
        budget_max = prefs.get("budget_pcm")
    
    if rent is None:
        breakdown["price"] = {"points": 0, "reason": "price 缺失，不计分"}
    else:
        try:
            price_num = float(rent)

            if budget_max is not None:
                diff = float(budget_max) - price_num

                if diff >= 0:
                    points = min(30, diff / budget_max * 30)
                    breakdown["price"] = {"points": round(points, 1), "reason": "低于预算，加分"}
                    score += points
                else:
                    penalty = max(-20, diff / budget_max * 30)
                    breakdown["price"] = {"points": round(penalty, 1), "reason": "超过预算，扣分"}
                    score += penalty
            else:
                breakdown["price"] = {"points": 0, "reason": "未设置预算"}

        except ValueError:
            breakdown["price"] = {"points": 0, "reason": f"rent 无法解析: {rent}"}
    # --- COMMUTE ---
        commute = house.get("commute_mins")
        commute_target = prefs.get("commute_target", 45)  # 用户期望通勤，默认45分钟

        if commute is None:
            breakdown["commute"] = {"points": 0, "reason": "commute_mins 缺失，不计分"}
        else:
            try:
                commute_num = float(commute)
                if commute_num <= float(commute_target):
                    points = weights.get("commute", 0)  # 达标加分（由weights控制）
                    breakdown["commute"] = {"points": points, "reason": f"通勤{commute_num:.0f}分钟 <= {commute_target}，加分"}
                    score += points
                else:
                    breakdown["commute"] = {"points": 0, "reason": f"通勤{commute_num:.0f}分钟 > {commute_target}，不加分"}
            except ValueError:
                breakdown["commute"] = {"points": 0, "reason": f"commute_mins 无法解析: {commute}，不计分"}
    # --- BILLS ---
    bills = house.get("bills")

    if bills is None:
        breakdown["bills"] = {"points": 0, "reason": "bills 信息缺失，不计分"}
    else:
        if str(bills).lower() in ["included", "yes", "true", "y"]:
            points = weights.get("bills", 0)
            breakdown["bills"] = {"points": points, "reason": "bills 包含，加分"}
            score += points
        else:
            breakdown["bills"] = {"points": 0, "reason": "bills 不包含，不加分"}
   
    # --- BEDROOMS ---
    bedrooms = house.get("bedrooms")
    min_bedrooms = prefs.get("min_bedrooms", 1)

    if bedrooms is None:
        breakdown["bedrooms"] = {"points": 0, "reason": "bedrooms 信息缺失，不计分"}
    else:
        try:
            bedrooms_num = int(bedrooms)
            if bedrooms_num >= int(min_bedrooms):
                points = weights.get("bedrooms", 0)
                breakdown["bedrooms"] = {"points": points, "reason": f"卧室数 {bedrooms_num} >= 需求 {min_bedrooms}，加分"}
                score += points
            else:
                breakdown["bedrooms"] = {"points": 0, "reason": f"卧室数 {bedrooms_num} < 需求 {min_bedrooms}，不加分"}
        except ValueError:
            breakdown["bedrooms"] = {"points": 0, "reason": f"bedrooms 无法解析: {bedrooms}，不计分"}

    # --- PENALTIES total ---
    for p in breakdown.get("penalties", []):
        score += p.get("points", 0)

    if distance is None:
        distance_reason = "distance missing"
    elif distance <= 1:
        distance_reason = f"within 1 mile ({distance} miles)"
    elif distance <= 3:
        distance_reason = f"within 3 miles ({distance} miles)"
    elif distance <= 5:
        distance_reason = f"within 5 miles ({distance} miles)"
    elif distance <= 8:
        distance_reason = f"within 8 miles ({distance} miles)"
    else:
        distance_reason = f"over 8 miles ({distance} miles)"

    breakdown["distance"] = {
        "points": distance_score,
        "reason": distance_reason
    }

    distance = house.get("distance")
    distance_score_value = score_distance(distance)

    house["distance_score"] = distance_score_value

    score += distance_score_value
    house["distance_score"] = distance_score_value
    return score, breakdown

def rank_houses(houses, prefs, weights):
    area_service = AreaService()   # ✅ 只创建一次

    results = []

    for h in houses:
        if "distance" not in h:
            h["distance"] = None 

        base_score, base_detail = score_house(h, prefs, weights)

        final_score, area_detail = add_area_score_to_house(
            house=h,
            base_score=base_score,
            area_service=area_service,
            area_weight=0.2
        )

        results.append({
            "house": h,
            "base_score": base_score,
            "final_score": final_score,
            "base_detail": base_detail,
            "area_detail": area_detail
        })

    results.sort(key=lambda x: x["final_score"], reverse=True)
    return results

def add_area_score_to_house(house: dict, base_score: float, area_service, area_weight: float = 0.2):
    # 兼容 postcode / post_code / 老的 area 字段
    postcode = house.get("postcode") or house.get("post_code") or house.get("area") or ""
    from area_module import get_area_score

    area_score = get_area_score(postcode) if postcode else 0
    
    area_add = round(area_weight * area_score, 2)
    final_score = round(base_score + area_add, 2)

    explain = {
        "postcode": postcode,
        "base_score": base_score,
        "area_score": area_score,
        "area_weight": area_weight,
        "area_add": area_add,
        "final_score": final_score
    }
    return final_score, explain

def explain_house(result):
    """把 breakdown 变成人话解释字符串"""
    house = result["house"]
    score = result["score"]
    breakdown = result["breakdown"]

    lines = []
    lines.append(f"房源 {house.get('id', '(no id)')} 总分：{score}")

    # 维度解释
    for k in ["price", "commute", "bills", "area", "bedrooms"]:
        if k in breakdown:
            item = breakdown[k]
            lines.append(f"- {k}: {item['points']}分，原因：{item['reason']}")

    # 扣分项
    if breakdown.get("penalties"):
        lines.append("扣分：")
        for p in breakdown["penalties"]:
            lines.append(f"- {p['points']}分，原因：{p['reason']}")

    return "\n".join(lines)