# P5 Phase3: AgentRentalRequest → analyze 表单 / analyze-batch 请求体（与 api_analysis.STANDARD_INPUT_KEYS 对齐）
from __future__ import annotations

from web_ui.rental_intent import AgentRentalRequest

# 与 web_bridge._WEB_FORM_DEFAULTS 一致，用于 intent 缺字段时的降级
_DEFAULT_RENT = 1200.0
_DEFAULT_BUDGET = 1500.0
_DEFAULT_COMMUTE = 30
_DEFAULT_BEDROOMS = 2


def merge_intent_metadata_for_area(intent: AgentRentalRequest) -> str:
    """
    property_type / furnished / source_preference / notes 后端单条 input 无独立字段时并入 area 展示。
    source_preference 仅作备注（引擎不消费）。
    """
    parts: list[str] = []
    if intent.preferred_area and str(intent.preferred_area).strip():
        parts.append(str(intent.preferred_area).strip())

    tags: list[str] = []
    if intent.property_type:
        tags.append("type:%s" % intent.property_type)
    if intent.furnished is True:
        tags.append("furnished")
    elif intent.furnished is False:
        tags.append("unfurnished")
    if intent.source_preference:
        tags.append("source_pref:%s (not used by engine)" % intent.source_preference)
    if intent.notes and str(intent.notes).strip():
        tags.append("notes:%s" % str(intent.notes).strip()[:120])

    if tags:
        parts.append("[%s]" % "; ".join(tags))
    return " · ".join(parts) if parts else ""


def build_batch_property_from_intent(intent: AgentRentalRequest) -> dict:
    """
    单条 `properties[]` 元素：仅含 API 允许字段；缺省用默认值保证可跑通 batch。
    """
    rent = float(intent.max_rent) if intent.max_rent is not None else _DEFAULT_RENT
    budget = rent * 1.15 if intent.max_rent is not None else _DEFAULT_BUDGET
    if budget < rent:
        budget = rent + 1.0

    commute = (
        int(intent.max_commute_minutes)
        if intent.max_commute_minutes is not None
        else _DEFAULT_COMMUTE
    )
    if intent.bedrooms is not None:
        bedrooms = int(intent.bedrooms)
    else:
        bedrooms = _DEFAULT_BEDROOMS

    bills = False if intent.bills_included is None else bool(intent.bills_included)

    area = merge_intent_metadata_for_area(intent)
    target_pc = (intent.target_postcode or "").strip() or None

    prop: dict = {
        "rent": rent,
        "budget": float(budget),
        "commute_minutes": commute,
        "bedrooms": bedrooms,
        "bills_included": bills,
    }
    if area:
        prop["area"] = area
    if target_pc:
        prop["target_postcode"] = target_pc
    return prop


def build_batch_request_from_intent(intent: AgentRentalRequest) -> dict:
    """POST /analyze-batch 请求体：当前调度固定为单条「需求场景」。"""
    return {"properties": [build_batch_property_from_intent(intent)]}


def build_analyze_raw_form_from_intent(intent: AgentRentalRequest) -> dict:
    """与 `collect_raw_form_from_session` 同结构；与 batch 单条 property 数值一致。"""
    p = build_batch_property_from_intent(intent)
    return {
        "rent": str(int(p["rent"])) if p["rent"] == int(p["rent"]) else str(p["rent"]),
        "budget": str(int(p["budget"])) if p["budget"] == int(p["budget"]) else str(p["budget"]),
        "commute_minutes": str(p["commute_minutes"]),
        "bedrooms": str(p["bedrooms"]),
        "distance": "",
        "bills_included": bool(p.get("bills_included", False)),
        "area": p.get("area") or "",
        "postcode": "",
        "target_postcode": p.get("target_postcode") or "",
    }
