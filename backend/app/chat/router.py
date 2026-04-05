"""
Phase 1 chat router skeleton: intent routing + Phase 0 legal hook (no LLM).
"""

from __future__ import annotations

from typing import Any

from ..legal.phase0_entry import run_phase0_analysis

from .followup_builder import (
    append_guidance_footer,
    build_chat_followup_bundle,
    build_invalid_input_bundle,
)
from .intent_rules import classify_intent
from .preference_detection import (
    build_user_signals_summary,
    detect_user_preferences,
    preference_voice_line,
)

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


def _merge_followup(base: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    out["followup_suggestions"] = bundle.get("followup_suggestions") or []
    out["next_step_prompt"] = bundle.get("next_step_prompt") or ""
    out["available_capabilities"] = bundle.get("available_capabilities") or []
    out["risk_tier"] = bundle.get("risk_tier")
    return out


def _with_preferences(result: dict[str, Any], trimmed: str) -> dict[str, Any]:
    """Attach structured preferences; optional one-line acknowledgement in response_text."""
    det = detect_user_preferences(trimmed)
    po: list[str] = list(det.get("priority_order") or [])
    summary = build_user_signals_summary(po)
    out = dict(result)
    out["detected_preferences"] = det
    out["priority_order"] = po
    out["user_signals_summary"] = summary
    if po:
        voice = preference_voice_line(po)
        rt = out.get("response_text") or ""
        if voice and voice not in rt:
            out["response_text"] = f"{rt.rstrip()}\n\n{voice}"
    return out


def _failure_empty() -> dict[str, Any]:
    inv = build_invalid_input_bundle()
    pref_empty = detect_user_preferences("")
    po_empty: list[str] = list(pref_empty.get("priority_order") or [])
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
        "suggested_followup": inv["next_step_prompt"],
        "available_next_modules": AVAILABLE_NEXT_MODULES,
        "followup_suggestions": inv["followup_suggestions"],
        "next_step_prompt": inv["next_step_prompt"],
        "available_capabilities": inv["available_capabilities"],
        "risk_tier": inv.get("risk_tier"),
        "detected_preferences": pref_empty,
        "priority_order": po_empty,
        "user_signals_summary": build_user_signals_summary(po_empty),
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
        bundle = build_chat_followup_bundle("legal_risk", source_result=p0)
        response = append_guidance_footer(response, str(bundle.get("response_closing") or ""))
        base = {
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
        return _with_preferences(_merge_followup(base, bundle), trimmed)

    msg = _PLACEHOLDER_COPY.get(intent, _PLACEHOLDER_COPY["general_unknown"])
    bundle = build_chat_followup_bundle(intent, source_result=None)
    msg = append_guidance_footer(msg, str(bundle.get("response_closing") or ""))
    base = {
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
    return _with_preferences(_merge_followup(base, bundle), trimmed)
