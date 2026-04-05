"""
Guided follow-up suggestions for the chat router (no LLM; template-based).
"""

from __future__ import annotations

from typing import Any

from ..legal.phase0_unified_display import normalize_raw_risk_level

# Stable capability ids for clients / future orchestration.
CAPABILITIES_LEGAL = [
    "contract_review",
    "property_comparison",
    "bills_estimate",
    "area_check",
]
CAPABILITIES_PROPERTY = [
    "property_comparison",
    "area_check",
    "bills_estimate",
    "contract_review",
]
CAPABILITIES_AREA = [
    "area_check",
    "transport_check",
    "property_comparison",
    "postcode_compare",
]
CAPABILITIES_BILLS = [
    "bills_estimate",
    "total_monthly_cost",
    "property_comparison",
    "contract_review",
]
CAPABILITIES_COMPARE = [
    "property_comparison",
    "bills_estimate",
    "area_check",
]
CAPABILITIES_GENERAL = [
    "contract_review",
    "property_comparison",
    "bills_estimate",
    "area_check",
]


def extract_risk_tier(source_result: dict[str, Any] | None) -> str:
    """Derive high | medium | low | unknown from a Phase 0 bundle."""
    if not isinstance(source_result, dict):
        return "unknown"
    rl = source_result.get("risk_level")
    if rl is None and isinstance(source_result.get("normalized_result"), dict):
        rl = source_result["normalized_result"].get("raw_level")
    return normalize_raw_risk_level(str(rl) if rl is not None else "")


def _unique_suggestions(candidates: list[str], limit: int = 3) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for s in candidates:
        t = s.strip()
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(t)
        if len(out) >= limit:
            break
    return out


def _legal_suggestions(tier: str) -> list[str]:
    if tier == "high":
        return _unique_suggestions(
            [
                "Before moving forward, it may be worth reviewing the contract wording in more detail.",
                "You may also want to compare this with a safer alternative property when you are ready.",
                "Later, I can help estimate bills or check area conditions for the homes you shortlist.",
            ]
        )
    if tier == "medium":
        return _unique_suggestions(
            [
                "I can also help review the contract wording more closely if you paste a fuller clause.",
                "If you want, I can compare this with another property later.",
                "I can also help estimate bills or area conditions next.",
            ]
        )
    if tier == "low":
        return _unique_suggestions(
            [
                "If you want, I can compare this with another property when you have a second listing.",
                "I can also help estimate typical bills or check area conditions for shortlisted areas.",
                "Feel free to paste another clause if you want a second pass.",
            ]
        )
    return _unique_suggestions(
        [
            "I can help review contract wording if you paste more detail.",
            "If you want, I can compare this with another property later.",
            "I can also help estimate bills or area checks next.",
        ]
    )


def _property_suggestions() -> list[str]:
    return _unique_suggestions(
        [
            "When it is connected, I will be able to score listings in more depth.",
            "If you want, we can later compare this with another property side by side.",
            "I can also help estimate bills or area conditions once those modules are live.",
        ]
    )


def _area_suggestions() -> list[str]:
    return _unique_suggestions(
        [
            "When available, I can summarise local facilities and transport links for a postcode.",
            "You could also compare two postcodes for commute or amenities later.",
            "I can tie area notes back to contract risks once you share a clause.",
        ]
    )


def _bills_suggestions() -> list[str]:
    return _unique_suggestions(
        [
            "Later, I can help compare total monthly costs across properties.",
            "I can also relate bills back to contract clauses when the module is ready.",
            "If you want, we can still review tenancy risks in plain English today.",
        ]
    )


def _comparison_suggestions() -> list[str]:
    return _unique_suggestions(
        [
            "When comparison is live, I will line up key terms and costs side by side.",
            "I can also help estimate bills for each home once that module exists.",
            "You can still ask for a contract risk check on either listing in the meantime.",
        ]
    )


def _general_suggestions() -> list[str]:
    return _unique_suggestions(
        [
            "I may be able to help if this is related to renting, contracts, deposits, bills, or area comparisons.",
            "Try a short question about your tenancy agreement, deposit, notice, or landlord behaviour.",
        ]
    )


def build_next_step_prompt(intent: str, tier: str) -> str:
    """Single line for API consumers (distinct from individual bullets)."""
    if intent == "legal_risk":
        if tier == "high":
            return (
                "Next, consider a careful read of the wording, then compare options or check bills and area when you are ready."
            )
        if tier in ("medium", "unknown"):
            return (
                "I can also help with contract review, property comparison, bills, or area checks when you are ready."
            )
        return (
            "You can also ask me to review more wording, compare with another property, or check bills and area later."
        )
    if intent == "property_analysis":
        return "When connected, I can go deeper on listings and tie in comparison, area, and bills."
    if intent == "area_info":
        return "Area facilities and transport summaries are planned; comparison across postcodes will follow."
    if intent == "bills_cost":
        return "Total cost views are planned; you can still ask for contract risk checks in plain English."
    if intent == "property_comparison":
        return "Side-by-side comparison is planned; contract review is available today if you paste a clause."
    return "Tell me if your question is about renting, contracts, deposits, bills, or comparing places."


def build_response_closing(intent: str, tier: str) -> str:
    """Short footer appended to response_text (product tone, not a second essay)."""
    if intent == "legal_risk":
        if tier == "high":
            return (
                "Take your time with the wording above. When you are ready, you can also ask me to compare "
                "this with another property or think about bills and area."
            )
        return (
            "You can also ask me to review more contract wording, compare this with another property, "
            "or check likely bill costs when those tools are connected."
        )
    if intent == "property_analysis":
        return (
            "If you want, keep a second listing handy—I can help compare or review contract risks once those pieces are live."
        )
    if intent == "area_info":
        return "When area insights launch, we can layer them next to your shortlist and any contract questions."
    if intent == "bills_cost":
        return "For now, a contract risk check can still highlight wording that affects what you pay."
    if intent == "property_comparison":
        return "Until comparison is wired, you can still paste clauses from each property for a quick risk read."
    return "If this touches renting or a home search, describe it in one sentence and I will route it."


def build_chat_followup_bundle(
    intent: str,
    *,
    source_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build follow-up suggestions, a summary prompt, capability ids, and response footer line.

    Uses intent plus Phase 0 ``risk_level`` / ``normalized_result.raw_level`` when present.
    """
    tier = extract_risk_tier(source_result) if intent == "legal_risk" else "unknown"

    if intent == "legal_risk":
        suggestions = _legal_suggestions(tier)
        capabilities = list(CAPABILITIES_LEGAL)
    elif intent == "property_analysis":
        suggestions = _property_suggestions()
        capabilities = list(CAPABILITIES_PROPERTY)
    elif intent == "area_info":
        suggestions = _area_suggestions()
        capabilities = list(CAPABILITIES_AREA)
    elif intent == "bills_cost":
        suggestions = _bills_suggestions()
        capabilities = list(CAPABILITIES_BILLS)
    elif intent == "property_comparison":
        suggestions = _comparison_suggestions()
        capabilities = list(CAPABILITIES_COMPARE)
    else:
        suggestions = _general_suggestions()
        capabilities = list(CAPABILITIES_GENERAL)

    nsp = build_next_step_prompt(intent, tier)
    closing = build_response_closing(intent, tier)

    return {
        "followup_suggestions": suggestions,
        "next_step_prompt": nsp,
        "available_capabilities": capabilities,
        "response_closing": closing,
        "risk_tier": tier if intent == "legal_risk" else None,
    }


def append_guidance_footer(body: str, closing: str) -> str:
    """Append a short closing paragraph to the main analysis body."""
    body = (body or "").rstrip()
    closing = (closing or "").strip()
    if not closing:
        return body
    if not body:
        return closing
    return f"{body}\n\n{closing}"


def build_invalid_input_bundle() -> dict[str, Any]:
    """Follow-up shape for empty user input."""
    return {
        "followup_suggestions": [
            "Try a short question about your tenancy, deposit, or a single contract clause.",
        ],
        "next_step_prompt": "I need at least one line of text to route your request.",
        "available_capabilities": list(CAPABILITIES_GENERAL),
        "response_closing": "",
        "risk_tier": None,
    }
