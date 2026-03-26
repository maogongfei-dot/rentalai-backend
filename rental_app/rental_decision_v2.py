# Phase C3：决策引擎 v2 — 综合分数、核心需求、风险与 explain_v2，无 LLM。
from __future__ import annotations

from typing import Any

from rental_explain_v2 import (
    _dedupe_preserve,
    _explain_bedrooms_and_type,
    _explain_bills_furnished_couple,
    _explain_budget,
    _explain_commute_station,
    _explain_location,
    _house_rent,
    _pick_focus,
)


def evaluate_core_match(
    house: dict[str, Any],
    structured_query: dict[str, Any],
    explain_v2: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    核心需求是否满足：仅对用户「明确提过」的 structured_query 维度计分；
    未提条件不记入 missed。
    explain_v2 可选，当前逻辑以规则重算为准，便于单测。
    """
    sq = structured_query or {}
    h = house or {}
    rent = _house_rent(h)

    matched_core: list[str] = []
    missed_core: list[str] = []
    partial_core: list[str] = []

    # 1) 预算
    if sq.get("budget_min") is not None or sq.get("budget_max") is not None:
        m, p, u = _explain_budget(sq, h, rent)
        matched_core.extend(m)
        partial_core.extend(p)
        missed_core.extend(u)

    # 2) 卧室 / 房型 / 物业类型
    if (
        sq.get("bedrooms") is not None
        or (sq.get("room_type") or "").strip()
        or (sq.get("property_type") or "").strip()
    ):
        m, p, u = _explain_bedrooms_and_type(sq, h)
        matched_core.extend(m)
        partial_core.extend(p)
        missed_core.extend(u)

    # 3) 城市 / 区域 / 邮编
    if (sq.get("city") or "").strip() or (sq.get("area") or "").strip() or (sq.get("postcode") or "").strip():
        m, p, u = _explain_location(sq, h)
        matched_core.extend(m)
        partial_core.extend(p)
        missed_core.extend(u)

    # 4) 明确要包 bill
    if sq.get("bills_included") is True:
        m, p, u = _explain_bills_furnished_couple(sq, h)
        for seq, target in ((m, matched_core), (p, partial_core), (u, missed_core)):
            for x in seq:
                if "bill" in x.lower() or "账单" in x:
                    target.append(x)

    # 5) 通勤 / 近车站（用户明确提过）
    if sq.get("commute_preference") or sq.get("near_station"):
        m, p, u = _explain_commute_station(sq, h)
        matched_core.extend(m)
        partial_core.extend(p)
        missed_core.extend(u)

    # 6) 情侣友好
    if sq.get("couple_friendly"):
        m, p, u = _explain_bills_furnished_couple(sq, h)
        for seq, target in ((m, matched_core), (p, partial_core), (u, missed_core)):
            for x in seq:
                if "情侣" in x or "couple" in x.lower():
                    target.append(x)

    matched_core = _dedupe_preserve(matched_core)
    partial_core = _dedupe_preserve(partial_core)
    missed_core = _dedupe_preserve(missed_core)

    # 汇总等级：预算/位置/房型等硬伤 → low；仅「不包 bill」类 → medium（顾问式妥协，非一票否决）
    def _is_bill_only_miss(items: list[str]) -> bool:
        if not items:
            return False
        for it in items:
            t = str(it).lower()
            if "bill" not in t and "账单" not in it:
                return False
        return True

    if missed_core and not _is_bill_only_miss(missed_core):
        core_match_level = "low"
    elif missed_core and _is_bill_only_miss(missed_core):
        core_match_level = "medium"
    elif partial_core:
        core_match_level = "medium"
    else:
        core_match_level = "high"

    return {
        "core_match_level": core_match_level,
        "matched_core_items": matched_core,
        "missed_core_items": missed_core,
        "partial_core_items": partial_core,
    }


def evaluate_recommendation_risk(
    house: dict[str, Any],
    explain_v2: dict[str, Any] | None = None,
    risks: list[str] | None = None,
) -> dict[str, Any]:
    """
    推荐层风险（非合同法律风险）：结合 explain 的未匹配、妥协与 legacy risks。
    """
    ev2 = explain_v2 or {}
    rlist = list(risks or [])
    unmatched = list(ev2.get("unmatched_preferences") or [])
    tradeoffs = list(ev2.get("tradeoffs") or [])

    risk_count = len(rlist) + len(unmatched)
    major_risks: list[str] = []
    major_risks.extend(rlist[:3])
    for u in unmatched[:2]:
        if u not in major_risks:
            major_risks.append(u)

    severe_kw = ("超预算", "预算上限", "不一致", "明显", "不符", "超出")
    severe = any(any(k in str(x) for k in severe_kw) for x in unmatched + tradeoffs)

    if risk_count >= 3 or severe or len(unmatched) >= 2:
        risk_level = "high"
    elif risk_count >= 1 or len(unmatched) == 1:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "risk_level": risk_level,
        "risk_count": min(risk_count, 20),
        "major_risks": _dedupe_preserve(major_risks)[:5],
    }


def _confidence_from_context(
    sq: dict[str, Any],
    house: dict[str, Any],
    partial_core: list[str],
    core_level: str,
) -> str:
    """数据缺失多、或用户关注安全/安静但样本无字段时，降低 confidence。"""
    h = house or {}
    missing_fields = 0
    if _house_rent(h) is None:
        missing_fields += 1
    if h.get("bedrooms") is None and not (h.get("property_type") or "").strip():
        missing_fields += 1
    if h.get("commute_minutes") is None and h.get("commute_mins") is None:
        missing_fields += 1

    low_data = missing_fields >= 2 or len(partial_core) >= 3
    safety_uncertain = bool(sq.get("safety_priority") or sq.get("quiet_priority"))

    if safety_uncertain or low_data or core_level == "low":
        return "low"
    if partial_core or core_level == "medium" or missing_fields == 1:
        return "medium"
    return "high"


def _decision_factors_good_bad(
    core: dict[str, Any],
    explain_v2: dict[str, Any],
    why_not: list[str] | None,
) -> tuple[list[str], list[str]]:
    good: list[str] = []
    good.extend((core.get("matched_core_items") or [])[:3])
    for x in (explain_v2.get("matched_preferences") or [])[:2]:
        if x not in good:
            good.append(x)
    good = _dedupe_preserve(good)[:4]

    bad: list[str] = []
    bad.extend((core.get("missed_core_items") or [])[:2])
    bad.extend((explain_v2.get("unmatched_preferences") or [])[:2])
    for t in (explain_v2.get("tradeoffs") or [])[:2]:
        if t not in bad:
            bad.append(t)
    for w in (why_not or [])[:2]:
        if w not in bad:
            bad.append(w)
    bad = _dedupe_preserve(bad)[:5]
    return good, bad


def _human_decision_summary(
    label: str,
    good: list[str],
    bad: list[str],
    core_level: str,
    risk_level: str,
) -> str:
    """顾问口吻的一小段总结。"""
    L = (label or "").upper()
    if L == "RECOMMENDED":
        return (
            "这套房整体较符合你的核心需求，尤其在 %s 方面匹配较好，当前没有明显硬伤。"
            % ("、".join(good[:2]) if good else "预算与房型")
        )[:220]
    if L == "CAUTION":
        return (
            "这套房可以考虑，但在 %s 等方面存在一定妥协或需核实，建议确认账单、通勤与房型细节后再决定。"
            % ("、".join(bad[:2]) if bad else "预算或配套")
        )[:220]
    return (
        "这套房与核心需求匹配度较低，尤其在 %s 方面偏差明显，不建议优先考虑。"
        % ("、".join(bad[:2]) if bad else "预算或位置")
    )[:220]


def build_decision_v2(
    house: dict[str, Any],
    structured_query: dict[str, Any],
    explain_v2: dict[str, Any],
    base_scores: dict[str, Any] | None = None,
    risks: list[str] | None = None,
    why_not: list[str] | None = None,
) -> dict[str, Any]:
    """
    综合 final_score、核心匹配、风险层、explain_v2 未匹配/妥协，输出 decision_v2。
    base_scores 预留与维度分相关微调，本阶段轻量使用。
    """
    sq = structured_query or {}
    ev2 = explain_v2 or {}
    h = house or {}

    core = evaluate_core_match(h, sq, ev2)
    re = evaluate_recommendation_risk(h, ev2, risks)
    core_level = core.get("core_match_level") or "medium"
    risk_level = re.get("risk_level") or "medium"

    score = h.get("final_score")
    try:
        fs = float(score) if score is not None else 0.0
    except (TypeError, ValueError):
        fs = 0.0

    um = ev2.get("unmatched_preferences") or []
    missed = core.get("missed_core_items") or []

    # --- 决策规则：不只看 final_score -----------------------------------------
    label = "CAUTION"

    severe_budget = any(
        any(
            k in str(x)
            for k in (
                "超出预算",
                "高于预算",
                "明显高于",
                "超出预算上限",
                "租金超出",
            )
        )
        for x in um
    )
    severe_type = any("Studio" in str(x) or "房型" in str(x) or "卧室" in str(x) for x in missed)

    bill_only_missed = bool(missed) and all(
        "bill" in str(x).lower() or "账单" in str(x) for x in missed
    )

    not_recommended = False
    if missed and (severe_budget or severe_type or len(missed) >= 2):
        not_recommended = True
    elif missed and len(missed) == 1 and bill_only_missed:
        # 仅 bill 不符：按产品定位为妥协，默认 CAUTION，不因单项直接 NOT（除非分数与风险极差）
        not_recommended = bool(risk_level == "high" and fs < 5.5 and len(um) >= 2)
    elif core_level == "low" and (risk_level == "high" or len(um) >= 2):
        not_recommended = True
    elif risk_level == "high" and fs < 6.0 and len(um) >= 1 and not bill_only_missed:
        not_recommended = True
    elif severe_budget and fs < 6.5:
        not_recommended = True

    recommended = False
    if (
        not not_recommended
        and core_level == "high"
        and risk_level in ("low", "medium")
        and not missed
        and len(um) == 0
        and fs >= 6.5
    ):
        recommended = True
    if (
        not not_recommended
        and core_level == "high"
        and risk_level == "low"
        and len(um) == 0
        and fs >= 7.5
    ):
        recommended = True

    if not_recommended:
        label = "NOT_RECOMMENDED"
    elif recommended:
        label = "RECOMMENDED"
    else:
        label = "CAUTION"

    good, bad = _decision_factors_good_bad(core, ev2, why_not)
    conf = _confidence_from_context(sq, h, core.get("partial_core_items") or [], core_level)

    # 维度分过低时倾向保守（不单独否决，但与 confidence 联动）
    dim_avg: float | None = None
    if base_scores and isinstance(base_scores, dict):
        nums = []
        for k in ("price_score", "commute_score", "bills_score", "bedrooms_score", "area_score"):
            v = base_scores.get(k)
            if isinstance(v, (int, float)):
                nums.append(float(v))
        if nums:
            dim_avg = sum(nums) / len(nums)
            if dim_avg < 42 and fs < 7.0 and label == "RECOMMENDED":
                label = "CAUTION"

    # 数据缺失多 / 安全安静不可核：confidence 低时不给「强烈推荐」
    if conf == "low" and label == "RECOMMENDED":
        label = "CAUTION"

    summary = _human_decision_summary(label, good, bad, core_level, risk_level)

    must_check = _pick_focus(
        sq,
        ev2.get("partial_matches") or [],
        ev2.get("unmatched_preferences") or [],
        h,
    )
    for r in (risks or [])[:2]:
        if "押金" in r and r not in must_check and len(must_check) < 3:
            must_check.append("核对押金与最短租期条款")
    must_check = _dedupe_preserve(must_check)[:3]

    # decision_reason 与顶层 recommendation 字段对齐，便于契约兼容
    out: dict[str, Any] = {
        "decision_label": label,
        "confidence": conf,
        "core_match_level": core_level,
        "risk_level": risk_level,
        "decision_summary": summary,
        "decision_reason": summary,
        "decision_factors_good": good,
        "decision_factors_bad": bad,
        "must_check_before_sign": must_check,
        "core_match": {
            "core_match_level": core_level,
            "matched_core_items": core.get("matched_core_items") or [],
            "missed_core_items": core.get("missed_core_items") or [],
            "partial_core_items": core.get("partial_core_items") or [],
        },
        "risk_eval": {
            "risk_level": risk_level,
            "risk_count": re.get("risk_count", 0),
            "major_risks": re.get("major_risks") or [],
        },
    }
    _ = base_scores  # 预留与维度分联动
    return out


def build_top_decision_summary(
    recommendations: list[dict[str, Any]],
    structured_query: dict[str, Any],
) -> dict[str, Any]:
    """ai-analyze 顶层：基于首条 recommendation 的 decision_v2。"""
    if not recommendations:
        return {
            "top_decision": "CAUTION",
            "top_decision_reason": "当前无推荐条目，请放宽查询条件或更换数据源后重试。",
            "selection_note": "可尝试降低房型约束或扩大预算范围。",
        }
    top = recommendations[0]
    dv2 = top.get("decision_v2") if isinstance(top.get("decision_v2"), dict) else {}
    label = dv2.get("decision_label") or top.get("decision") or "CAUTION"
    reason = dv2.get("decision_summary") or top.get("decision_reason") or ""
    note = "建议优先查看排名前 2 条，并对照 explain_v2 中的账单、通勤与签约前核对项。"
    sq = structured_query or {}
    if (sq.get("bills_included") is True) or (sq.get("budget_max")):
        note = "样本中部分房源可能在 bill 或预算边界上需额外确认；签约前务必核实月支出与合同条款。"
    return {
        "top_decision": label,
        "top_decision_reason": (reason or "请结合逐条 decision_v2 查看。")[:300],
        "selection_note": note,
    }
