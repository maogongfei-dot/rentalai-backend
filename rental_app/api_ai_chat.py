"""
Phase 1 Step 6 — AI Chat 占位接口（规则模拟回复，不接真实 LLM）。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AIChatIntent = Literal[
    "property_search",
    "contract_help",
    "area_info",
    "dispute_help",
    "landlord_help",
    "general",
]


class AIChatRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    message: str = Field(..., min_length=1)


class AIChatResponse(BaseModel):
    answer: str
    intent: AIChatIntent
    suggested_next_actions: list[str]


_PROPERTY_KEYWORDS = ("rent", "property", "house", "flat", "房子", "租房")
_CONTRACT_KEYWORDS = ("contract", "tenancy", "deposit", "clause", "合同", "押金")
_LANDLORD_KEYWORDS = ("landlord", "listing", "short rent", "host", "房东", "发布房源")


def _contains_keyword(text: str, keywords: tuple[str, ...]) -> bool:
    low = text.lower()
    return any(kw in low or kw in text for kw in keywords)


def build_ai_chat_response(message: str) -> AIChatResponse:
    """Rule-based intent routing and canned replies (no LLM)."""
    text = (message or "").strip()
    if not text:
        return AIChatResponse(
            answer=(
                "I understand your question. RentalAI will guide you through property, "
                "contract, landlord, and rental risk analysis."
            ),
            intent="general",
            suggested_next_actions=[
                "Ask about a property",
                "Ask about a contract",
                "Ask about landlord tools",
            ],
        )

    if _contains_keyword(text, _PROPERTY_KEYWORDS):
        return AIChatResponse(
            answer=(
                "I can help you compare rental properties by rent, area, commute, "
                "bills, and risk score."
            ),
            intent="property_search",
            suggested_next_actions=[
                "Compare a property",
                "Check rent affordability",
                "Analyse location",
            ],
        )

    if _contains_keyword(text, _CONTRACT_KEYWORDS):
        return AIChatResponse(
            answer=(
                "I can help you review tenancy agreements, explain risky clauses, "
                "and identify deposit-related issues."
            ),
            intent="contract_help",
            suggested_next_actions=[
                "Review a contract",
                "Check deposit risk",
                "Explain a clause",
            ],
        )

    if _contains_keyword(text, _LANDLORD_KEYWORDS):
        return AIChatResponse(
            answer=(
                "I can help landlords create listings, improve property descriptions, "
                "and understand short-rent operations."
            ),
            intent="landlord_help",
            suggested_next_actions=[
                "Create a listing",
                "Improve listing content",
                "Understand landlord tools",
            ],
        )

    return AIChatResponse(
        answer=(
            "I understand your question. RentalAI will guide you through property, "
            "contract, landlord, and rental risk analysis."
        ),
        intent="general",
        suggested_next_actions=[
            "Ask about a property",
            "Ask about a contract",
            "Ask about landlord tools",
        ],
    )
