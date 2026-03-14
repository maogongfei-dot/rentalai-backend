from __future__ import annotations
import json
import math
import os
from typing import Optional, Tuple

from area_module import get_area_score

DEFAULT_WEIGHTS = {
    "price": 35,
    "commute": 30,
    "bills": 15,
    "area": 10,
    "bedrooms": 10,
}

# Module5 Area Score config (Phase2-B)
AREA_SCORE_EXACT_MATCH = 10.0
AREA_SCORE_AREA_LOOSE = 8.0
AREA_SCORE_MISSING = 5.0
AREA_SCORE_NO_MATCH = 6.0
AREA_SCORE_AVOIDED = 2.0

# Postcode prefix tiered scores (Phase2-B(2)-B2-A)
POSTCODE_PREFIX_SCORE_LONG = 9.0   # e.g. "MK40 2", "MK402"
POSTCODE_PREFIX_SCORE_MEDIUM = 8.0 # e.g. "MK40"
POSTCODE_PREFIX_SCORE_SHORT = 7.0  # e.g. "MK"

from module5_area.area_service import AreaService
from contract_risk import calculate_structured_risk_score, calculate_risk_penalty

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


def _norm(s: Any) -> str:
    """Normalize string for comparison: strip + lower. Empty/None -> ''."""
    if s is None:
        return ""
    return str(s).strip().lower()


def get_area_from_postcode(postcode: Any) -> str:
    """
    Module5 Phase3: postcode -> area 自动识别.
    MK40/MK41 -> bedford, E1 -> london_east, SW11 -> london_sw, CR4 -> croydon.
    不匹配或 postcode 为空则返回 "unknown".
    """
    if postcode is None or not str(postcode).strip():
        return "unknown"
    raw = str(postcode).strip().upper()
    # 取 outward code（空格前一段，如 MK40 1AB -> MK40）
    parts = raw.split()
    prefix = parts[0] if parts else raw[:4] or ""
    if prefix.startswith("MK40") or prefix.startswith("MK41"):
        return "bedford"
    if prefix.startswith("E1"):
        return "london_east"
    if prefix.startswith("SW11"):
        return "london_sw"
    if prefix.startswith("CR4"):
        return "croydon"
    return "unknown"


_AREA_DATA_CACHE = None

def _load_area_data() -> dict:
    """Load data/area_data.json once; return {} on missing/invalid."""
    global _AREA_DATA_CACHE
    if _AREA_DATA_CACHE is not None:
        return _AREA_DATA_CACHE
    try:
        base = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base, "data", "area_data.json")
        with open(path, "r", encoding="utf-8") as f:
            _AREA_DATA_CACHE = json.load(f)
        return _AREA_DATA_CACHE
    except Exception:
        _AREA_DATA_CACHE = {}
        return _AREA_DATA_CACHE


def calculate_area_quality_score(area: Any) -> float:
    """
    Module5 Phase2 后半: 根据 area_data.json 的 safety/transport/amenities/cost/noise 计算区域质量分 (0-10).
    area 不存在或缺失时返回中性分 5.
    """
    if area is None or (isinstance(area, str) and not area.strip()):
        return 5.0
    key = _norm(area)
    if not key:
        return 5.0
    data = _load_area_data()
    row = data.get(key) or data.get(area.strip()) or data.get(area.strip().upper())
    if not row or not isinstance(row, dict):
        return 5.0
    dims = ["safety", "transport", "amenities", "cost", "noise"]
    values = []
    for d in dims:
        v = row.get(d)
        if v is not None:
            try:
                values.append(float(v))
            except (TypeError, ValueError):
                pass
    if not values:
        return 5.0
    avg = sum(values) / len(values)
    return round(max(0.0, min(10.0, avg)), 2)


def calculate_area_preference_score(house: dict, settings: dict) -> Tuple[float, str]:
    """
    Module5 Phase2-B(2)-A: Area Score Engine 细化版.
    Returns (area_score 0~10, area_score_reason).

    Priority rules (highest wins, no stacking):
      1) area 精确命中 或 postcode 精确命中 -> 10
      2) postcode 前缀命中 -> 8
      3) area 弱匹配（包含关系） -> 8
      4) area/postcode 均缺失 -> 5
      5) 其余情况 -> 6
    """
    try:
        preferred_areas = [
            _norm(x) for x in (settings.get("preferred_areas") or []) if x is not None
        ]
        avoided_areas = [
            _norm(x) for x in (settings.get("avoided_areas") or []) if x is not None
        ]
        preferred_postcodes = [
            _norm(x) for x in (settings.get("preferred_postcodes") or []) if x is not None
        ]
    except (TypeError, AttributeError):
        return AREA_SCORE_MISSING, "Area/postcode preferences not set, neutral score applied"

    listing_area = _norm(house.get("area"))
    raw_postcode = house.get("postcode") or house.get("post_code") or ""
    listing_postcode = _norm(raw_postcode)

    def _postcode_prefix_match(listing: str, prefs: list[str]) -> Tuple[bool, str, float, str]:
        """
        返回 (matched, best_prefix, score, level)
        level in {"long", "medium", "short"} when matched is True.
        """
        if not listing or not prefs:
            return False, "", 0.0, ""
        lp = listing.replace(" ", "")
        best_prefix = ""
        best_score = 0.0
        best_level = ""

        for p in prefs:
            if not p:
                continue
            pp = p.replace(" ", "")
            if not pp:
                continue
            if lp.startswith(pp):
                length = len(pp)
                # 长前缀: 长度 >= 5
                if length >= 5:
                    score = POSTCODE_PREFIX_SCORE_LONG
                    level = "long"
                # 中前缀: 长度 == 4
                elif length == 4:
                    score = POSTCODE_PREFIX_SCORE_MEDIUM
                    level = "medium"
                # 短前缀: 长度 <= 3
                else:
                    score = POSTCODE_PREFIX_SCORE_SHORT
                    level = "short"

                # longest prefix wins (比较长度优先，其次分值防御性)
                if len(pp) > len(best_prefix) or (len(pp) == len(best_prefix) and score > best_score):
                    best_prefix = pp
                    best_score = score
                    best_level = level

        if best_prefix:
            return True, best_prefix, best_score, best_level
        return False, "", 0.0, ""

    def _area_loose_match(listing: str, prefs: list[str]) -> bool:
        if not listing or not prefs:
            return False
        for p in prefs:
            if not p:
                continue
            if listing in p or p in listing:
                return True
        return False

    in_preferred_area = bool(listing_area) and listing_area in preferred_areas
    in_preferred_postcode = bool(listing_postcode) and listing_postcode in preferred_postcodes
    in_avoided_area = bool(listing_area) and listing_area in avoided_areas
    has_avoided_loose = _area_loose_match(listing_area, avoided_areas)
    has_postcode_prefix, best_prefix, best_prefix_score, best_prefix_level = _postcode_prefix_match(
        listing_postcode, preferred_postcodes
    )
    has_area_loose_pref = _area_loose_match(listing_area, preferred_areas)

    # 1) 精确命中（area 或 postcode）——最高优先级
    if in_preferred_area and in_preferred_postcode:
        return AREA_SCORE_EXACT_MATCH, "Matched preferred area and postcode"
    if in_preferred_area:
        return AREA_SCORE_EXACT_MATCH, "Matched preferred area"
    if in_preferred_postcode:
        return AREA_SCORE_EXACT_MATCH, "Matched preferred postcode"

    # 2) 避免区域（精确或弱匹配）——第二优先级
    if in_avoided_area:
        return AREA_SCORE_AVOIDED, "Matched avoided area"
    if has_avoided_loose:
        return AREA_SCORE_AVOIDED, "Matched avoided area loosely"

    # 3) postcode 前缀命中（分层）
    if has_postcode_prefix:
        # best_prefix_score 已根据长度映射到 long/medium/short
        if best_prefix_level == "long":
            level_desc = "long"
        elif best_prefix_level == "medium":
            level_desc = "medium"
        else:
            level_desc = "short"
        return best_prefix_score, f"Matched preferred postcode prefix ({level_desc})"

    # 4) area 弱匹配（包含关系）
    if has_area_loose_pref:
        return AREA_SCORE_AREA_LOOSE, "Matched preferred area loosely"

    # 5) 缺失信息 -> 中性
    if not listing_area and not listing_postcode:
        return AREA_SCORE_MISSING, "Area/postcode missing, neutral score applied"

    # 6) 其他 -> 略正向分数
    return AREA_SCORE_NO_MATCH, "No preference match"


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


def _get_dimension_weights(prefs: dict) -> dict:
    """从 settings 读取统一权重，缺省 1.0。B2-B2-A 收口。仅兼容用；final_score 应使用 validate_score_weights 结果."""
    out = {}
    for key in ("price_weight", "commute_weight", "bills_weight", "bedrooms_weight", "area_weight"):
        v = prefs.get(key, 1.0)
        try:
            out[key.replace("_weight", "")] = float(v)
        except (TypeError, ValueError):
            out[key.replace("_weight", "")] = 1.0
    return out


def validate_score_weights(settings: dict) -> tuple[dict, list]:
    """
    B2-B2-B1: 统一权重合法性校验。
    输入: settings / preferences
    输出: (validated_weights_dict, warnings_list)
    validated_weights_dict 键: price, commute, bills, bedrooms, area
    """
    warnings: list = []
    fields = [
        ("price_weight", "price"),
        ("commute_weight", "commute"),
        ("bills_weight", "bills"),
        ("bedrooms_weight", "bedrooms"),
        ("area_weight", "area"),
    ]
    out = {}
    for skey, dkey in fields:
        v = settings.get(skey)
        # 1. 缺失 / None / 空字符串
        if v is None or (isinstance(v, str) and str(v).strip() == ""):
            out[dkey] = 1.0
            warnings.append(f"{skey} missing, defaulted to 1.0")
            continue
        # 2. 非数字
        try:
            fv = float(v)
        except (TypeError, ValueError):
            out[dkey] = 1.0
            warnings.append(f"{skey} invalid, defaulted to 1.0")
            continue
        # 3. 负数
        if fv < 0:
            out[dkey] = 1.0
            warnings.append(f"{skey} negative, defaulted to 1.0")
            continue
        # 4. 0 允许保留
        # 5. 超大值温和提示
        if fv > 5.0:
            warnings.append(f"{skey} unusually high (>5.0)")
        out[dkey] = fv

    # 五个权重全为 0 时整组回退为全 1.0
    if sum(out.values()) == 0:
        for dkey in out:
            out[dkey] = 1.0
        warnings.append("all weights are 0, defaulted all weights to 1.0")
    return out, warnings


# B2-B2-B2-A: 权重预设，名称小写，集中定义
WEIGHT_PRESETS = {
    "balanced": {
        "price_weight": 1.0,
        "commute_weight": 1.0,
        "bills_weight": 1.0,
        "bedrooms_weight": 1.0,
        "area_weight": 1.0,
    },
    "price_first": {
        "price_weight": 1.5,
        "commute_weight": 1.0,
        "bills_weight": 1.0,
        "bedrooms_weight": 1.0,
        "area_weight": 1.0,
    },
    "area_first": {
        "price_weight": 1.0,
        "commute_weight": 1.0,
        "bills_weight": 1.0,
        "bedrooms_weight": 1.0,
        "area_weight": 1.5,
    },
    "commute_first": {
        "price_weight": 1.0,
        "commute_weight": 1.5,
        "bills_weight": 1.0,
        "bedrooms_weight": 1.0,
        "area_weight": 1.0,
    },
}


# B2-B2-B2-B1: 正向/负向因素阈值与标签，规则集中
_EXPLAIN_SCORE_STRONG = 80.0   # >= 视为明显优势 (0-100)
_EXPLAIN_SCORE_WEAK = 50.0    # <= 视为明显弱项 (0-100)
_EXPLAIN_TOP_N = 3            # 每类最多条数

_POSITIVE_LABELS = {
    "price": "Affordable rent",
    "commute": "Good commute score",
    "bills": "Bills score strong",
    "bedrooms": "Bedroom fit",
    "area": "Strong area match",
}
_NEGATIVE_LABELS = {
    "price": "Rent score low",
    "commute": "Weak commute",
    "bills": "Bills score is low",
    "bedrooms": "Weak bedroom fit",
    "area": "Area preference not matched",
}


def _build_listing_explain(
    final_score: float,
    weight_preset_used: str,
    resolved_weights: dict,
    validated_weights: dict,
    weighted_base_score_detail: dict,
    area_pref_reason: str,
    price_score: float,
    commute_score: float,
    bills_score: float,
    bedrooms_score: float,
    area_score_100: float,
) -> dict:
    """
    为单条房源生成统一 explain 结构。B2-B2-B2-B1。
    分数均为 0-100 尺度（area 已用 area_score_100）。
    """
    # weighted_breakdown: score, weight, weighted_value; area 带 reason
    weighted_breakdown = {}
    for dim in ("price", "commute", "bills", "bedrooms", "area"):
        detail = (weighted_base_score_detail or {}).get(dim) or {}
        score_val = _to_float(detail.get("score_100"), 0) or 0.0
        weight_val = _to_float(detail.get("weight"), 1) or 1.0
        contrib = _to_float(detail.get("contribution"), 0) or 0.0
        entry = {"score": round(score_val, 2), "weight": round(weight_val, 2), "weighted_value": round(contrib, 2)}
        if dim == "area" and area_pref_reason:
            entry["reason"] = area_pref_reason
        weighted_breakdown[dim] = entry

    scores = {
        "price": price_score,
        "commute": commute_score,
        "bills": bills_score,
        "bedrooms": bedrooms_score,
        "area": area_score_100,
    }
    top_positive_factors: list = []
    top_negative_factors: list = []
    for dim in ("price", "commute", "bills", "bedrooms", "area"):
        s = scores.get(dim) or 0
        if s >= _EXPLAIN_SCORE_STRONG and len(top_positive_factors) < _EXPLAIN_TOP_N:
            if dim == "area" and area_pref_reason:
                top_positive_factors.append(area_pref_reason[:80] if len(area_pref_reason) > 80 else area_pref_reason)
            else:
                top_positive_factors.append(_POSITIVE_LABELS.get(dim, dim))
        if s <= _EXPLAIN_SCORE_WEAK and len(top_negative_factors) < _EXPLAIN_TOP_N:
            if dim == "area" and area_pref_reason and s <= _EXPLAIN_SCORE_WEAK:
                top_negative_factors.append(area_pref_reason[:80] if len(area_pref_reason) > 80 else area_pref_reason)
            else:
                top_negative_factors.append(_NEGATIVE_LABELS.get(dim, dim))

    # recommendation_summary: 一句话，与正负因素呼应
    if top_positive_factors and not top_negative_factors:
        recommendation_summary = f"Recommended mainly for {top_positive_factors[0].lower()}" + (
            f" and {top_positive_factors[1].lower()}." if len(top_positive_factors) > 1 else "."
        )
    elif top_negative_factors and not top_positive_factors:
        recommendation_summary = f"Less preferred due to {top_negative_factors[0].lower()}" + (
            f" and {top_negative_factors[1].lower()}." if len(top_negative_factors) > 1 else "."
        )
    elif top_positive_factors and top_negative_factors:
        recommendation_summary = f"Balanced: strong on {top_positive_factors[0].lower()}, weak on {top_negative_factors[0].lower()}."
    else:
        recommendation_summary = "Mid-range scores across dimensions; no strong standouts."
    try:
        final_f = float(final_score)
        if final_f >= 80:
            recommendation_summary = "High overall score. " + recommendation_summary
        elif final_f <= 50:
            recommendation_summary = "Lower overall score. " + recommendation_summary
    except (TypeError, ValueError):
        pass

    return {
        "final_score": final_score,
        "weight_preset": weight_preset_used,
        "resolved_weights": resolved_weights,
        "validated_weights": validated_weights,
        "weighted_breakdown": weighted_breakdown,
        "top_positive_factors": top_positive_factors,
        "top_negative_factors": top_negative_factors,
        "recommendation_summary": recommendation_summary,
    }


# B2-B2-B2-B2-A: 对比解释维度与差异文案，规则集中
_COMPARE_DIMENSIONS = ("price", "commute", "bills", "bedrooms", "area")
_COMPARE_DIFF_LABELS = {
    "price": "Better price/rent score",
    "commute": "Stronger commute score",
    "bills": "Better bills fit",
    "bedrooms": "Better bedroom fit",
    "area": "Better area match",
}
_COMPARE_TOP_N_DIFFS = 3


def _score_100_for_compare(result: dict, dim: str) -> float:
    """从 result 取维度 dim 的 0-100 分，缺则 0。"""
    if dim == "area":
        # result["area_score"] 为 0-10
        s = _to_float(result.get("area_score"), 0) or 0
        return min(100.0, max(0.0, float(s) * 10.0))
    key = f"{dim}_score"
    return _to_float(result.get(key), 0) or 0.0


def build_compare_explain(ranked_results: list) -> dict:
    """
    B2-B2-B2-B2-A: 为排序后的结果列表生成相邻名次两两对比解释。
    返回: { "pairwise_comparisons": [ { better_house_label, lower_house_label, score_gap, key_differences, comparison_summary }, ... ] }
    """
    pairwise_comparisons = []
    n = len(ranked_results)
    if n < 2:
        return {"pairwise_comparisons": pairwise_comparisons}

    for i in range(n - 1):
        better = ranked_results[i]
        lower = ranked_results[i + 1]
        better_label = f"Rank {i + 1}"
        lower_label = f"Rank {i + 2}"
        score_b = _to_float(better.get("final_score"), 0) or 0.0
        score_l = _to_float(lower.get("final_score"), 0) or 0.0
        score_gap = round(score_b - score_l, 2)

        # 关键差异：各维度分差，取差异最大的前 2~3 个（更好方领先的维度）
        diffs = []
        for dim in _COMPARE_DIMENSIONS:
            sb = _score_100_for_compare(better, dim)
            sl = _score_100_for_compare(lower, dim)
            delta = sb - sl
            if delta > 0:
                diffs.append((dim, delta))
        diffs.sort(key=lambda x: -x[1])
        key_differences = [_COMPARE_DIFF_LABELS.get(d, d) for d, _ in diffs[:_COMPARE_TOP_N_DIFFS]]

        # area 可结合 reason：若 better 的 area 领先且存在 reason，可替换为首条 area 文案（此处保持简洁统一用 Better area match）
        if not key_differences:
            key_differences = ["More balanced total score"]

        # comparison_summary: 一句话
        if key_differences:
            if len(key_differences) == 1:
                comparison_summary = f"{better_label} ranks above {lower_label} mainly because of {key_differences[0].lower()}."
            else:
                comparison_summary = f"{better_label} ranks above {lower_label} mainly because of {key_differences[0].lower()} and {key_differences[1].lower()}."
        else:
            comparison_summary = f"{better_label} has a slight edge over {lower_label} (score gap {score_gap})."
        try:
            if abs(score_gap) < 0.01 and key_differences:
                comparison_summary = f"The ranking gap is driven mostly by {key_differences[0].lower()}."
        except Exception:
            pass

        pairwise_comparisons.append({
            "better_house_label": better_label,
            "lower_house_label": lower_label,
            "score_gap": score_gap,
            "key_differences": key_differences,
            "comparison_summary": comparison_summary,
        })

    return {"pairwise_comparisons": pairwise_comparisons}


# B2-B2-B2-B2-B1-A: 线下核实清单映射（弱项 -> 可执行检查项），规则集中
_VIEWING_CHECK_BY_WEAKNESS = {
    "area": "Check whether the surrounding area still feels acceptable in person.",
    "Area preference not matched": "Check whether the surrounding area still feels acceptable in person.",
    "Strong area match": None,  # 强项不生成检查
    "bills": "Confirm which bills are included and estimate monthly extras.",
    "Bills score is low": "Confirm which bills are included and estimate monthly extras.",
    "bedrooms": "Verify bedroom size, layout, and storage usability in person.",
    "Weak bedroom fit": "Verify bedroom size, layout, and storage usability in person.",
    "commute": "Test the actual commute route and travel time.",
    "Weak commute": "Test the actual commute route and travel time.",
    "price": "Double-check the full monthly cost against your budget.",
    "Rent score low": "Double-check the full monthly cost against your budget.",
}
_VIEWING_CHECK_DEFAULT = "Do a normal viewing check to confirm overall fit."
_VIEWING_CHECK_MAX = 3

# B2-B2-B2-B2-B1-B1: 偏好切换提示阈值与文案，规则集中
_SWITCH_THRESHOLD = 15.0   # Top2 在某维度领先 Top1 至少 15（0-100 尺度）才视为反转因子
_SWITCH_TRIGGER_MAX = 2    # 最多取 2 个 trigger_factor
_SWITCH_FACTOR_LABELS = {
    "price": ("affordability", "affordability is your top priority"),
    "commute": ("commute", "commute matters more to you"),
    "bills": ("bills fit", "bills predictability matters more"),
    "bedrooms": ("bedroom fit", "bedroom fit is a key priority"),
    "area": ("area fit", "area preference matters more than overall balance"),
}

# B2-B2-B2-B2-B1-B2-A: 单维偏好模拟，规则集中
_SIM_FACTORS = ("price", "commute", "bills", "bedrooms", "area")
_SIM_WEIGHT_MULTIPLIER = 1.5   # 模拟时将该维度权重 ×1.5
_SIM_FACTOR_DISPLAY = {"price": "price/affordability", "commute": "commute", "bills": "bills", "bedrooms": "bedrooms", "area": "area"}

# B2-B2-B2-B2-B1-B2-B1: 双维组合模拟，集中定义（仅 3 组）
_MULTI_FACTOR_PAIRS = [
    ["price", "area"],
    ["commute", "area"],
    ["price", "commute"],
]


def _neg_to_viewing_checks(neg_label: str) -> str | None:
    """将负向因素标签映射为一条检查项文案，无映射则返回 None。"""
    s = (neg_label or "").strip()
    if not s:
        return None
    if s in _VIEWING_CHECK_BY_WEAKNESS:
        return _VIEWING_CHECK_BY_WEAKNESS.get(s)
    for key, val in _VIEWING_CHECK_BY_WEAKNESS.items():
        if val and key.lower() in s.lower():
            return val
    if "area" in s.lower():
        return _VIEWING_CHECK_BY_WEAKNESS["area"]
    if "bills" in s.lower():
        return _VIEWING_CHECK_BY_WEAKNESS["bills"]
    if "bedroom" in s.lower():
        return _VIEWING_CHECK_BY_WEAKNESS["bedrooms"]
    if "commute" in s.lower():
        return _VIEWING_CHECK_BY_WEAKNESS["commute"]
    if "rent" in s.lower() or "price" in s.lower():
        return _VIEWING_CHECK_BY_WEAKNESS["price"]
    return None


def build_decision_hints(ranked_results: list, compare_explain: dict) -> dict:
    """
    B2-B2-B2-B2-B1(+A): 为排序结果生成决策提示：primary / backup / caution + best_if / caution_if + viewing_checklist。
    返回: { primary_recommendation, backup_option, caution_option, viewing_checklist }。
    """
    out = {"primary_recommendation": None, "backup_option": None, "caution_option": None, "viewing_checklist": [], "preference_switch_hints": [], "preference_simulation": [], "multi_factor_simulation": [], "action_plan": {}}
    n = len(ranked_results)
    if n < 1:
        return out

    # primary_recommendation: Rank 1 + best_if
    r1 = ranked_results[0]
    ex1 = r1.get("explain") or {}
    rec_summary = ex1.get("recommendation_summary") or ""
    positives = ex1.get("top_positive_factors") or []
    if rec_summary:
        short_reason = rec_summary[:120] if len(rec_summary) > 120 else rec_summary
    elif positives:
        short_reason = "Strong on " + ", ".join(positives[:2])
    else:
        short_reason = "Highest final score in this set."
    summary = "This is the current top choice."
    if rec_summary:
        summary = rec_summary.strip()
    elif positives:
        summary = f"This is the strongest overall option, with strengths in {positives[0].lower()}" + (f" and {positives[1].lower()}." if len(positives) > 1 else ".")
    else:
        summary = "This is the strongest overall option because it has the highest final score in this set."
    # best_if: 基于 positives 或整体均衡
    if positives and any("area" in p.lower() for p in positives[:2]):
        best_if = "Best if area preference is a top priority."
    elif positives and len(positives) >= 2:
        best_if = "Best if you want the strongest overall balance."
    elif positives:
        best_if = "Best if you want the highest total fit with fewer obvious weak points."
    else:
        best_if = "Best if you want the strongest overall balance."
    out["primary_recommendation"] = {
        "house_label": "Rank 1",
        "short_reason": short_reason,
        "summary": summary,
        "best_if": best_if,
    }

    # backup_option: Rank 2 if exists + best_if
    if n >= 2:
        r2 = ranked_results[1]
        ex2 = r2.get("explain") or {}
        comp_list = compare_explain.get("pairwise_comparisons") or []
        gap = None
        key_diffs_1v2 = []
        if comp_list:
            first_comp = comp_list[0]
            gap = _to_float(first_comp.get("score_gap"), None)
            key_diffs_1v2 = first_comp.get("key_differences") or []
        r2_positives = ex2.get("top_positive_factors") or []
        if gap is not None and gap <= 2.0 and r2_positives:
            short_reason = f"Score close to Rank 1 (gap {gap}); still strong on " + ", ".join(r2_positives[:2])
            summary = "Worth keeping as a second option because its overall score remains close to the top listing."
        elif r2_positives:
            short_reason = "Strong on " + ", ".join(r2_positives[:2])
            summary = "A solid backup choice if the top option is unavailable; still has notable strengths."
        else:
            short_reason = "Second-highest score; viable alternative."
            summary = "A solid backup choice if the primary option does not work out."
        # best_if: 基于 gap 或 Rank 2 相对优势
        if gap is not None and gap <= 2.0:
            best_if = "Best if you want a viable fallback with a close overall score."
        elif key_diffs_1v2 and any("price" in d.lower() or "rent" in d.lower() for d in key_diffs_1v2):
            best_if = "Best if rent fit matters more than area preference."
        elif r2_positives:
            best_if = "Best if you are willing to trade a little on the top option for a solid alternative."
        else:
            best_if = "Best if you want a viable fallback when the primary is unavailable."
        out["backup_option"] = {
            "house_label": "Rank 2",
            "short_reason": short_reason,
            "summary": summary,
            "best_if": best_if,
        }

    # caution_option: 负向因素最明显的一套房（排除 Rank 1，从 Rank 2 及以后选）
    if n >= 2:
        # 在 Rank 2..Rank n 中选：top_negative_factors 最多 或 final_score 最低
        candidates = []
        for i in range(1, n):
            r = ranked_results[i]
            ex = r.get("explain") or {}
            negs = ex.get("top_negative_factors") or []
            score = _to_float(r.get("final_score"), 0) or 0.0
            # 弱项数量 + 低分倾向
            neg_count = len(negs)
            candidates.append((i + 1, r, neg_count, score, negs))
        if candidates:
            # 优先 neg_count 多，其次 score 低
            candidates.sort(key=lambda x: (-x[2], x[3]))
            rank_idx, caution_r, _nc, _sc, negs = candidates[0]
            ex_c = caution_r.get("explain") or {}
            negs = ex_c.get("top_negative_factors") or []
            if negs:
                short_reason = "Weaker on " + ", ".join(negs[:2])
                summary = f"This option needs more caution because {negs[0].lower()} may affect overall suitability."
            else:
                short_reason = "Lower rank; some dimensions may need extra verification."
                summary = "This listing ranks lower; worth double-checking dimensions that matter to you."
            # caution_if: 基于 negs 生成条件化提示
            if negs:
                n0 = (negs[0] or "").lower()
                if "bedroom" in n0:
                    caution_if = "Use caution if bedroom fit is important."
                elif "bills" in n0:
                    caution_if = "Use caution if bills predictability matters."
                elif "area" in n0:
                    caution_if = "Use caution if area alignment is a key priority."
                elif "commute" in n0:
                    caution_if = "Use caution if commute time is a key factor."
                elif "rent" in n0 or "price" in n0:
                    caution_if = "Use caution if staying within budget is critical."
                else:
                    caution_if = f"Use caution if {negs[0].lower()} matters to you."
            else:
                caution_if = "Use caution and verify dimensions that matter to you."
            out["caution_option"] = {
                "house_label": f"Rank {rank_idx}",
                "short_reason": short_reason,
                "summary": summary,
                "caution_if": caution_if,
            }

    # viewing_checklist: 为每套房生成 2~3 条线下核实项
    for i, r in enumerate(ranked_results):
        label = f"Rank {i + 1}"
        ex = r.get("explain") or {}
        negs = ex.get("top_negative_factors") or []
        checks = []
        seen = set()
        for neg in negs[: _VIEWING_CHECK_MAX]:
            line = _neg_to_viewing_checks(neg)
            if line and line not in seen:
                seen.add(line)
                checks.append(line)
        if not checks:
            checks.append(_VIEWING_CHECK_DEFAULT)
        out["viewing_checklist"].append({"house_label": label, "checks": checks[: _VIEWING_CHECK_MAX]})

    # preference_switch_hints: Rank1 -> Rank2 的反转条件（仅 Top1 vs Top2）
    if n >= 2:
        r1, r2 = ranked_results[0], ranked_results[1]
        diffs = []
        for dim in ("price", "commute", "bills", "bedrooms", "area"):
            s1 = _score_100_for_compare(r1, dim)
            s2 = _score_100_for_compare(r2, dim)
            delta = (s2 or 0) - (s1 or 0)
            if delta >= _SWITCH_THRESHOLD:
                diffs.append((dim, delta))
        diffs.sort(key=lambda x: -x[1])
        triggers = [d for d, _ in diffs[:_SWITCH_TRIGGER_MAX]]
        if triggers:
            factor = triggers[0]
            label_short, label_cond = _SWITCH_FACTOR_LABELS.get(factor, (factor, factor))
            short_reason = f"Top2 is stronger on {label_short}."
            summary = f"If {label_cond}, consider reviewing Rank 2 before making a final decision."
            if factor == "price":
                summary = "If affordability is your top priority, Rank 2 may be worth checking alongside the current top choice."
            elif factor == "area":
                summary = "If area preference matters more than overall balance, consider reviewing Rank 2 before making a final decision."
            elif factor == "commute":
                summary = "If commute matters more to you, Rank 2 could become the more suitable option."
            out["preference_switch_hints"].append({
                "from_house_label": "Rank 1",
                "to_house_label": "Rank 2",
                "trigger_factor": factor,
                "short_reason": short_reason,
                "summary": summary,
            })

    # preference_simulation: 单维权重 ×1.5 后重算 Top1 vs Top2 的模拟分差与是否反转
    if n >= 2:
        r1, r2 = ranked_results[0], ranked_results[1]
        vw = r1.get("validated_weights") or {}
        base1 = _to_float(r1.get("weighted_base_score"), 0) or 0.0
        base2 = _to_float(r2.get("weighted_base_score"), 0) or 0.0
        final1 = _to_float(r1.get("final_score"), 0) or 0.0
        final2 = _to_float(r2.get("final_score"), 0) or 0.0
        add1 = final1 - base1
        add2 = final2 - base2
        scores1 = {d: _score_100_for_compare(r1, d) for d in _SIM_FACTORS}
        scores2 = {d: _score_100_for_compare(r2, d) for d in _SIM_FACTORS}
        orig_gap = round(final1 - final2, 2)

        for factor in _SIM_FACTORS:
            w = dict(vw) if vw else {d: 1.0 for d in _SIM_FACTORS}
            w[factor] = (w.get(factor) or 1.0) * _SIM_WEIGHT_MULTIPLIER
            sum_w = sum(w.get(d, 1) for d in _SIM_FACTORS) or 1.0
            sim_base1 = sum((scores1.get(d) or 0) * (w.get(d) or 1) for d in _SIM_FACTORS) / sum_w
            sim_base2 = sum((scores2.get(d) or 0) * (w.get(d) or 1) for d in _SIM_FACTORS) / sum_w
            sim_final1 = round(sim_base1 + add1, 2)
            sim_final2 = round(sim_base2 + add2, 2)
            sim_gap = round(sim_final1 - sim_final2, 2)
            ranking_changed = (orig_gap >= 0 and sim_gap < 0) or (orig_gap < 0 and sim_gap > 0)

            if ranking_changed:
                summary_sim = f"If {_SIM_FACTOR_DISPLAY.get(factor, factor)} matters more, Rank 2 becomes the stronger option."
            elif orig_gap > 0 and 0 <= sim_gap < orig_gap:
                summary_sim = f"If {_SIM_FACTOR_DISPLAY.get(factor, factor)} matters more, Rank 2 closes the gap but does not overtake Rank 1."
            elif abs(sim_gap - orig_gap) < 0.5:
                summary_sim = f"Increasing {_SIM_FACTOR_DISPLAY.get(factor, factor)} priority does not materially change the current top choice."
            else:
                summary_sim = f"If {_SIM_FACTOR_DISPLAY.get(factor, factor)} matters more, the gap changes (simulated gap {sim_gap})."
            out["preference_simulation"].append({
                "simulated_factor": factor,
                "original_top_house_label": "Rank 1",
                "challenger_house_label": "Rank 2",
                "original_score_gap": orig_gap,
                "simulated_score_gap": sim_gap,
                "ranking_changed": ranking_changed,
                "summary": summary_sim,
            })

        # multi_factor_simulation: 双维同时 ×1.5，复用 scores1/scores2/add1/add2/orig_gap
        for pair in _MULTI_FACTOR_PAIRS:
            if len(pair) != 2:
                continue
            w = dict(vw) if vw else {d: 1.0 for d in _SIM_FACTORS}
            for f in pair:
                w[f] = (w.get(f) or 1.0) * _SIM_WEIGHT_MULTIPLIER
            sum_w = sum(w.get(d, 1) for d in _SIM_FACTORS) or 1.0
            sim_base1 = sum((scores1.get(d) or 0) * (w.get(d) or 1) for d in _SIM_FACTORS) / sum_w
            sim_base2 = sum((scores2.get(d) or 0) * (w.get(d) or 1) for d in _SIM_FACTORS) / sum_w
            sim_final1 = round(sim_base1 + add1, 2)
            sim_final2 = round(sim_base2 + add2, 2)
            sim_gap = round(sim_final1 - sim_final2, 2)
            ranking_changed = (orig_gap >= 0 and sim_gap < 0) or (orig_gap < 0 and sim_gap > 0)
            lab_a = _SIM_FACTOR_DISPLAY.get(pair[0], pair[0])
            lab_b = _SIM_FACTOR_DISPLAY.get(pair[1], pair[1])
            if ranking_changed:
                summary_m = f"If both {lab_a} and {lab_b} matter more, Rank 2 becomes the stronger option."
            elif orig_gap > 0 and 0 <= sim_gap < orig_gap:
                summary_m = f"If {lab_a} and {lab_b} are both prioritised, Rank 2 closes the gap but does not overtake Rank 1."
            elif abs(sim_gap - orig_gap) < 0.5:
                summary_m = f"Increasing both {lab_a} and {lab_b} priority does not materially change the current top choice."
            else:
                summary_m = f"If both {lab_a} and {lab_b} matter more, the gap changes (simulated gap {sim_gap})."
            out["multi_factor_simulation"].append({
                "simulated_factors": list(pair),
                "original_top_house_label": "Rank 1",
                "challenger_house_label": "Rank 2",
                "original_score_gap": orig_gap,
                "simulated_score_gap": sim_gap,
                "ranking_changed": ranking_changed,
                "summary": summary_m,
            })

    # C1: action_plan 收口层（contact_first / view_first / keep_as_backup / investigate_before_committing）
    primary = out.get("primary_recommendation")
    backup = out.get("backup_option")
    caution = out.get("caution_option")
    comp_list = compare_explain.get("pairwise_comparisons") or []
    gap_small = False
    if comp_list and n >= 2:
        gap = _to_float(comp_list[0].get("score_gap"), None)
        if gap is not None and abs(gap) <= 2.0:
            gap_small = True
    has_switch = bool(out.get("preference_switch_hints"))

    if primary:
        contact_summary = "Contact this listing first because it is the strongest overall fit."
        if primary.get("summary"):
            contact_summary = primary["summary"]
        if gap_small:
            contact_summary = contact_summary.rstrip(".") + "; consider keeping Rank 2 as a second option."
        out["action_plan"]["contact_first"] = {
            "house_label": primary.get("house_label", "Rank 1"),
            "short_reason": primary.get("short_reason", "Top overall score"),
            "summary": contact_summary,
        }

    if primary:
        view_summary = "View this one first to confirm whether the strong paper score matches the real in-person fit."
        if has_switch:
            view_summary = view_summary.rstrip(".") + "; you may also view Rank 2 if that factor matters more."
        out["action_plan"]["view_first"] = {
            "house_label": primary.get("house_label", "Rank 1"),
            "short_reason": primary.get("short_reason", "Top overall score"),
            "summary": view_summary,
        }

    if backup:
        out["action_plan"]["keep_as_backup"] = {
            "house_label": backup.get("house_label", "Rank 2"),
            "short_reason": backup.get("short_reason", "Second-highest score"),
            "summary": backup.get("summary") or "Keep this as a backup because it stays close on score and may suit you better if your priorities shift.",
        }

    if caution:
        c_reason = (caution.get("short_reason") or "some dimensions look weaker on paper").lower()
        out["action_plan"]["investigate_before_committing"] = {
            "house_label": caution.get("house_label", ""),
            "short_reason": caution.get("short_reason", "Weaker on some dimensions"),
            "summary": "Investigate this option carefully before committing because " + c_reason.rstrip(".") + ".",
        }

    return out


def resolve_preset_and_overrides(prefs: dict) -> tuple[dict, str, list]:
    """
    B2-B2-B2-A: preset 默认 -> 用户显式 weight 覆盖 -> 返回供 validate 的 settings。
    返回: (resolved_settings, preset_used, warnings)
    resolved_settings 键: price_weight, commute_weight, ...
    """
    warnings: list = []
    preset_name = prefs.get("weight_preset") if prefs else None
    if preset_name is None or (isinstance(preset_name, str) and not preset_name.strip()):
        preset_name = "balanced"
    else:
        preset_name = str(preset_name).strip().lower()
    if preset_name not in WEIGHT_PRESETS:
        warnings.append(f"unknown weight_preset '{preset_name}', defaulted to balanced")
        preset_name = "balanced"
    base = dict(WEIGHT_PRESETS[preset_name])
    # 用户显式传入的 weight 覆盖 preset
    for key in ("price_weight", "commute_weight", "bills_weight", "bedrooms_weight", "area_weight"):
        if prefs and prefs.get(key) is not None:
            base[key] = prefs[key]
    return base, preset_name, warnings


def _points_to_score_100(points: float, low: float, high: float) -> float:
    """将原始 points 映射到 0–100。high > low."""
    if high <= low:
        return 100.0 if points >= high else 0.0
    x = (float(points) - low) / (high - low) * 100.0
    return max(0.0, min(100.0, x))


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

    # --- AREA PREFERENCE (for breakdown only, scoring加权在 rank_houses 中处理) ---
    area_pref_score, area_pref_reason = calculate_area_preference_score(house, prefs)
    breakdown["area"] = {
        "points": area_pref_score,
        "reason": area_pref_reason,
    }

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
    # B2-B2-B2-A: preset -> override -> validation -> final_score
    resolved_settings, weight_preset_used, preset_warnings = resolve_preset_and_overrides(prefs if prefs else {})
    validated_weights, validation_warnings = validate_score_weights(resolved_settings)
    weight_warnings = list(preset_warnings) + list(validation_warnings)
    resolved_weights = {
        "price": resolved_settings.get("price_weight", 1.0),
        "commute": resolved_settings.get("commute_weight", 1.0),
        "bills": resolved_settings.get("bills_weight", 1.0),
        "bedrooms": resolved_settings.get("bedrooms_weight", 1.0),
        "area": resolved_settings.get("area_weight", 1.0),
    }
    # B2-B2-B2-A: 哪些维度被用户手动 override（prefs 中显式提供）
    override_keys = [k for k in ("price", "commute", "bills", "bedrooms", "area") if prefs.get(f"{k}_weight") is not None]

    results = []

    for h in houses:
        if "distance" not in h:
            h["distance"] = None

        # Module5 Phase3: 无 area 但有 postcode 时自动推断 area（仅用于本轮评分，不覆盖已有 area）
        if not (h.get("area") or "").strip() and h.get("postcode"):
            h["area"] = get_area_from_postcode(h["postcode"])

        base_score, base_detail = score_house(h, prefs, weights)
        area_pref_score, area_pref_reason = calculate_area_preference_score(h, prefs)

        # B2-B2-A: 统一权重与加权平均（使用校验后权重 B2-B2-B1）
        dim_weights = validated_weights
        price_pts = _to_float(base_detail.get("price", {}).get("points"), 0.0) or 0.0
        commute_pts = _to_float(base_detail.get("commute", {}).get("points"), 0.0) or 0.0
        bills_pts = _to_float(base_detail.get("bills", {}).get("points"), 0.0) or 0.0
        bedrooms_pts = _to_float(base_detail.get("bedrooms", {}).get("points"), 0.0) or 0.0
        area_pts = _to_float(base_detail.get("area", {}).get("points"), 0.0) or 0.0  # 0–10

        price_score = _points_to_score_100(price_pts, -20.0, 30.0)
        commute_max = float(weights.get("commute", 30) or 30)
        commute_score = (commute_pts / commute_max * 100.0) if commute_max else 0.0
        commute_score = max(0.0, min(100.0, commute_score))
        bills_max = float(weights.get("bills", 15) or 15)
        bills_score = (bills_pts / bills_max * 100.0) if bills_max else 0.0
        bills_score = max(0.0, min(100.0, bills_score))
        bedrooms_max = float(weights.get("bedrooms", 10) or 10)
        bedrooms_score = (bedrooms_pts / bedrooms_max * 100.0) if bedrooms_max else 0.0
        bedrooms_score = max(0.0, min(100.0, bedrooms_score))
        area_score_100 = area_pts * 10.0  # 0–10 -> 0–100
        area_score_100 = max(0.0, min(100.0, area_score_100))

        pw, cw, bw, brw, aw = dim_weights.get("price", 1.0), dim_weights.get("commute", 1.0), dim_weights.get("bills", 1.0), dim_weights.get("bedrooms", 1.0), dim_weights.get("area", 1.0)
        sum_w = pw + cw + bw + brw + aw
        if sum_w <= 0:
            sum_w = 1.0
        weighted_base = (price_score * pw + commute_score * cw + bills_score * bw + bedrooms_score * brw + area_score_100 * aw) / sum_w
        weighted_base = round(weighted_base, 2)

        distance_pts = _to_float(base_detail.get("distance", {}).get("points"), 0.0) or 0.0
        penalties_sum = sum(_to_float(p.get("points"), 0.0) or 0.0 for p in base_detail.get("penalties", []))
        core_for_area = weighted_base + distance_pts + penalties_sum

        final_score, area_detail = add_area_score_to_house(
            house=h,
            base_score=core_for_area,
            area_service=area_service,
            area_weight=0.2
        )

        # Module5 Phase2 后半: 区域质量分 (area_data.json)
        area_quality = calculate_area_quality_score(h.get("area"))
        area_quality_weight = 0.15
        final_score = round(final_score + area_quality_weight * area_quality, 2)

        # Module3 Phase2: Structured contract risk penalty
        risk_struct = calculate_structured_risk_score(h)
        risk_score = risk_struct.get("structured_risk_score", 0)
        risk_penalty = calculate_risk_penalty(risk_score)
        final_score = round(final_score + risk_penalty, 2)

        # 加权明细，便于 explain/breakdown 展示
        weighted_base_score_detail = {
            "price": {"score_100": round(price_score, 2), "weight": pw, "contribution": round(price_score * pw, 2)},
            "commute": {"score_100": round(commute_score, 2), "weight": cw, "contribution": round(commute_score * cw, 2)},
            "bills": {"score_100": round(bills_score, 2), "weight": bw, "contribution": round(bills_score * bw, 2)},
            "bedrooms": {"score_100": round(bedrooms_score, 2), "weight": brw, "contribution": round(bedrooms_score * brw, 2)},
            "area": {"score_100": round(area_score_100, 2), "weight": aw, "contribution": round(area_score_100 * aw, 2)},
        }
        area_score_contribution = round((area_score_100 * aw) / sum_w, 2)  # 兼容 B2-B1 输出

        explain = _build_listing_explain(
            final_score=final_score,
            weight_preset_used=weight_preset_used,
            resolved_weights=resolved_weights,
            validated_weights={"price": pw, "commute": cw, "bills": bw, "bedrooms": brw, "area": aw},
            weighted_base_score_detail=weighted_base_score_detail,
            area_pref_reason=area_pref_reason or "",
            price_score=price_score,
            commute_score=commute_score,
            bills_score=bills_score,
            bedrooms_score=bedrooms_score,
            area_score_100=area_score_100,
        )

        results.append({
            "house": h,
            "base_score": base_score,
            "final_score": final_score,
            "base_detail": base_detail,
            "area_detail": area_detail,
            # 统一权重 (B2-B2-A)，均为校验后值 (B2-B2-B1)
            "price_weight": round(pw, 2),
            "commute_weight": round(cw, 2),
            "bills_weight": round(bw, 2),
            "bedrooms_weight": round(brw, 2),
            "area_weight": round(aw, 2),
            "weight_preset": weight_preset_used,
            "resolved_weights": resolved_weights,
            "validated_weights": {"price": pw, "commute": cw, "bills": bw, "bedrooms": brw, "area": aw},
            "weight_warnings": weight_warnings,
            "override_keys": override_keys,
            "price_score": round(price_score, 2),
            "commute_score": round(commute_score, 2),
            "bills_score": round(bills_score, 2),
            "bedrooms_score": round(bedrooms_score, 2),
            "area_score": round(area_pref_score, 2),
            "area_score_reason": area_pref_reason,
            "area_preference_score": round(area_pref_score, 2),
            "area_preference_reason": area_pref_reason,
            "area_score_contribution": area_score_contribution,
            "weighted_base_score": weighted_base,
            "weighted_base_score_detail": weighted_base_score_detail,
            # area quality & risk
            "area_quality_score": round(area_quality, 2),
            "risk_score": int(risk_score) if isinstance(risk_score, (int, float)) else risk_score,
            "risk_penalty": risk_penalty,
            "risk_reasons": risk_struct.get("risk_reasons", []),
            "explain": explain,
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