"""
Phase 1 chat router skeleton: intent routing + Phase 0 legal hook (no LLM).
"""

from __future__ import annotations

from typing import Any

from ..legal.phase0_entry import run_phase0_analysis

from .intent_rules import classify_intent

MODULE_ID = "chat_router"

# Modules not wired in this version (for discovery / future orchestration).
AVAILABLE_NEXT_MODULES = [
    "property_analysis",
    "area_info",
    "bills_cost",
    "property_comparison",
]

_PLACEHOLDER_COPY: dict[str, str] = {
    "property_analysis": (
        "I can help with deeper property analysis later, but that module is not connected yet."
    ),
    "area_info": (
        "Area insights are planned next, but they are not available in this version yet."
    ),
    "bills_cost": (
        "Bill and running-cost estimates are on the roadmap, but that module is not connected yet."
    ),
    "property_comparison": (
        "I can help with property comparison later, but that module is not connected yet."
    ),
    "general_unknown": (
        "I am not sure how to help with that yet. Try asking about tenancy contracts, "
        "deposits, notices, or landlord behaviour in plain English."
    ),
}


def _failure_empty() -> dict[str, Any]:
    return {
        "module": MODULE_ID,
        "success": False,
        "intent": "invalid_input",
        "input_text": "",
        "response_text": (
            "I could not process the request because no valid input was provided."
        ),
        "source_module": None,
        "source_result": None,
        "suggested_followup": "Try pasting a short question about your tenancy or contract.",
        "available_next_modules": AVAILABLE_NEXT_MODULES,
    }


def handle_chat_request(user_text: str) -> dict[str, Any]:
    """
    Single entry for the chat orchestrator. Routes to Phase 0 for legal/contract queries.

    Example: ``result = handle_chat_request("Is my deposit protected?")``
    """
    trimmed = (user_text or "").strip()
    if not trimmed:
        return _failure_empty()

    intent = classify_intent(trimmed)

    if intent == "legal_risk":
        p0 = run_phase0_analysis(trimmed)
        response = p0.get("display_text") or ""
        if not p0.get("success"):
            response = response or str(p0.get("error") or "Analysis could not be completed.")
        follow = str(p0.get("suggested_followup") or "")
        return {
            "module": MODULE_ID,
            "success": True,
            "intent": "legal_risk",
            "input_text": trimmed,
            "response_text": response,
            "source_module": "phase0_legal_risk",
            "source_result": p0,
            "suggested_followup": follow,
            "available_next_modules": AVAILABLE_NEXT_MODULES,
        }

    msg = _PLACEHOLDER_COPY.get(intent, _PLACEHOLDER_COPY["general_unknown"])
    return {
        "module": MODULE_ID,
        "success": True,
        "intent": intent,
        "input_text": trimmed,
        "response_text": msg,
        "source_module": None,
        "source_result": None,
        "suggested_followup": (
            "Ask about a contract clause or deposit if you want a rules-based check today."
        ),
        "available_next_modules": AVAILABLE_NEXT_MODULES,
    }
