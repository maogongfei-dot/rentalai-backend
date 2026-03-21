# P5 Phase4：缺失条件识别 + 轻量追问建议（无 LLM）
from __future__ import annotations

from dataclasses import dataclass

from web_ui.rental_intent import AgentRentalRequest

# 缺失检测字段 id（与 UI / snippet 对应）
FIELD_MAX_RENT = "max_rent"
FIELD_LOCATION = "location"
FIELD_BEDROOMS = "bedrooms"
FIELD_PROPERTY_TYPE = "property_type"
FIELD_FURNISHED = "furnished"
FIELD_COMMUTE = "commute"
FIELD_BILLS = "bills_included"


@dataclass(frozen=True)
class RefinementSuggestion:
    field_id: str
    button_label: str
    question: str
    nl_snippet: str  # 追加到 Agent 文本框的建议句


def get_missing_intent_fields(intent: AgentRentalRequest) -> list[str]:
    """规则：未显式给出的偏好视为可补充（bool 已给 True/False 不算缺失）。"""
    missing: list[str] = []
    if intent.max_rent is None:
        missing.append(FIELD_MAX_RENT)
    if not (intent.preferred_area or "").strip() and not (intent.target_postcode or "").strip():
        missing.append(FIELD_LOCATION)
    if intent.bedrooms is None:
        missing.append(FIELD_BEDROOMS)
    if not (intent.property_type or "").strip():
        missing.append(FIELD_PROPERTY_TYPE)
    if intent.furnished is None:
        missing.append(FIELD_FURNISHED)
    if intent.max_commute_minutes is None:
        missing.append(FIELD_COMMUTE)
    if intent.bills_included is None:
        missing.append(FIELD_BILLS)
    return missing


def get_refinement_suggestions(intent: AgentRentalRequest) -> list[RefinementSuggestion]:
    """按缺失项生成可点击补充文案（非聊天）。"""
    miss = set(get_missing_intent_fields(intent))
    pool: list[RefinementSuggestion] = [
        RefinementSuggestion(
            FIELD_MAX_RENT,
            "Add budget",
            "What is your maximum monthly rent?",
            "My maximum rent is £1300 per month.",
        ),
        RefinementSuggestion(
            FIELD_LOCATION,
            "Add area",
            "Which area or postcode do you prefer?",
            "I prefer living near E14 or Canary Wharf.",
        ),
        RefinementSuggestion(
            FIELD_BEDROOMS,
            "Add bedrooms",
            "How many bedrooms do you need?",
            "I need a 2 bedroom flat.",
        ),
        RefinementSuggestion(
            FIELD_PROPERTY_TYPE,
            "Add property type",
            "Flat, house, studio, or room?",
            "I am looking for a furnished flat.",
        ),
        RefinementSuggestion(
            FIELD_FURNISHED,
            "Add furnishing",
            "Do you need furnished or unfurnished?",
            "I need a furnished property.",
        ),
        RefinementSuggestion(
            FIELD_COMMUTE,
            "Add commute",
            "What commute time is acceptable?",
            "My commute should be within 30 minutes.",
        ),
        RefinementSuggestion(
            FIELD_BILLS,
            "Add bills preference",
            "Should bills be included?",
            "I prefer bills included.",
        ),
    ]
    return [s for s in pool if s.field_id in miss]
