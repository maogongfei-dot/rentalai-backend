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
from .query_scope import (
    build_scope_message,
    classify_query_scope,
    scope_handling_label,
)
from .comparison import (
    build_comparison_response_text,
    build_property_snapshot_from_side,
    coerce_comparison_inputs,
    extract_property_comparison_inputs,
    run_basic_property_comparison,
)
from .property_input import (
    build_property_reference,
    parse_property_input,
    property_input_voice_line,
)
from .analysis_route import (
    build_analysis_entry_result,
    compute_analysis_readiness,
    decide_analysis_route,
    empty_analysis_entry,
    empty_analysis_route,
)
from .location import build_uk_location_context, empty_uk_location_context
from .presentation import build_chat_display_bundle

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


def _scope_fields(scope_info: dict[str, Any]) -> dict[str, Any]:
    sc = scope_info.get("scope") or "rental_related"
    return {
        "scope": sc,
        "scope_handling": scope_handling_label(sc),
        "scope_message": build_scope_message(sc, list(scope_info.get("matched_keywords") or [])),
        "scope_confidence": scope_info.get("confidence"),
        "matched_scope_keywords": list(scope_info.get("matched_keywords") or []),
    }


def _merge_scope_into(base: dict[str, Any], scope_info: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    out.update(_scope_fields(scope_info))
    return out


def _with_preferences(
    result: dict[str, Any],
    trimmed: str,
    pref_det: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Attach structured preferences; optional one-line acknowledgement in response_text."""
    det = pref_det if pref_det is not None else detect_user_preferences(trimmed)
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
    invalid_scope = classify_query_scope("")
    scope_block = _scope_fields(invalid_scope)
    pi_empty = parse_property_input("")
    pi_ref_empty = build_property_reference(pi_empty)
    empty_result: dict[str, Any] = {
        "module": MODULE_ID,
        "success": False,
        "intent": "invalid_input",
        "input_text": "",
        "response_text": "I could not understand the request.",
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
        "comparison_inputs": None,
        "comparison_result": None,
        "property_input_detected": pi_empty.get("is_property_reference", False),
        "property_input_parsed": pi_empty,
        "property_reference": pi_ref_empty,
        "analysis_route": empty_analysis_route(),
        "analysis_entry_result": empty_analysis_entry(),
        "analysis_readiness": "pending",
        "next_analysis_action": "",
        "route_based_response_text": "",
        "uk_location_context": empty_uk_location_context(),
        "city_context": "",
        "postcode_context": "",
        "supports_uk_wide_routing": True,
        **scope_block,
    }
    disp = build_chat_display_bundle(empty_result)
    empty_result["display_text"] = disp["display_text"]
    empty_result["display_sections"] = disp["display_sections"]
    return empty_result


def _prepend_related_lead(response: str, scope_info: dict[str, Any]) -> str:
    if scope_info.get("scope") != "rental_related":
        return response
    lead = build_scope_message("rental_related", list(scope_info.get("matched_keywords") or []))
    if not lead.strip():
        return response
    return f"{lead}\n\n{response.rstrip()}"


def _attach_property_input(
    base: dict[str, Any],
    pi_parsed: dict[str, Any],
    pi_ref: dict[str, Any],
) -> dict[str, Any]:
    out = dict(base)
    out["property_input_detected"] = pi_parsed.get("is_property_reference", False)
    out["property_input_parsed"] = pi_parsed
    out["property_reference"] = pi_ref
    return out


def _attach_uk_location(
    out: dict[str, Any],
    trimmed: str,
    pi_parsed: dict[str, Any],
    pi_ref: dict[str, Any],
    detected_preferences: dict[str, Any],
) -> dict[str, Any]:
    uk = build_uk_location_context(
        trimmed,
        property_input_parsed=pi_parsed,
        property_reference=pi_ref,
        comparison_inputs=out.get("comparison_inputs"),
        comparison_result=out.get("comparison_result"),
        detected_preferences=detected_preferences,
    )
    o = dict(out)
    o["uk_location_context"] = uk
    o["city_context"] = uk.get("city") or ""
    o["postcode_context"] = uk.get("postcode") or ""
    o["supports_uk_wide_routing"] = True
    return o


def _append_uk_location_hint(result: dict[str, Any]) -> dict[str, Any]:
    if result.get("intent") == "legal_risk" or result.get("scope") == "out_of_scope":
        return result
    uk = result.get("uk_location_context") or {}
    if not uk.get("is_supported_uk_context"):
        return result
    lt = uk.get("location_type")
    if lt == "unknown":
        return result
    city = uk.get("city")
    pc = uk.get("postcode")
    if lt == "city" and city:
        hint = (
            f"I noted a UK city context ({city}). "
            "That can later anchor area-level analysis across UK cities."
        )
    elif lt == "postcode" and pc:
        hint = (
            f"I noted postcode {pc}. "
            "That can work as a local anchor when area-level analysis is connected."
        )
    elif lt == "mixed" and city and pc:
        hint = (
            f"I noted {city} and {pc} together for more precise local context later."
        )
    else:
        hint = (
            "I noted UK location context for later area-level and cross-city use."
        )
    rt_body = (result.get("response_text") or "").rstrip()
    if hint in rt_body:
        return result
    out = dict(result)
    out["response_text"] = f"{rt_body}\n\n{hint}" if rt_body else hint
    nsp = (out.get("next_step_prompt") or "").strip()
    if nsp and hint not in nsp:
        out["next_step_prompt"] = f"{nsp}\n{hint}"
    return out


def _append_property_hint(result: dict[str, Any], pi_parsed: dict[str, Any]) -> dict[str, Any]:
    if result.get("intent") == "property_comparison":
        return result
    ar = result.get("analysis_route") or {}
    if ar.get("route_type") in ("property_analysis_candidate", "area_analysis_candidate"):
        if (result.get("route_based_response_text") or "").strip():
            return result
    rb = (result.get("route_based_response_text") or "").strip()
    rt_body = result.get("response_text") or ""
    if rb and rb in rt_body:
        return result
    hint = property_input_voice_line(pi_parsed)
    if not hint:
        return result
    if hint in rt_body:
        return result
    out = dict(result)
    out["response_text"] = f"{rt_body.rstrip()}\n\n{hint}"
    return out


def _apply_analysis_route(
    out: dict[str, Any],
    trimmed: str,
    pi_parsed: dict[str, Any],
    pi_ref: dict[str, Any],
    scope_info: dict[str, Any],
) -> dict[str, Any]:
    """Attach analysis_route / entry result and prepend route-based copy when appropriate."""
    ctx: dict[str, Any] = {
        "intent": out.get("intent"),
        "scope_info": scope_info,
        "property_input_parsed": pi_parsed,
        "property_reference": pi_ref,
        "comparison_inputs": out.get("comparison_inputs"),
        "comparison_result": out.get("comparison_result"),
        "user_text": trimmed,
        "uk_location_context": out.get("uk_location_context") or {},
    }
    route = decide_analysis_route(ctx)
    entry = build_analysis_entry_result(route, ctx, pi_ref)
    readiness = compute_analysis_readiness(route, entry, out.get("comparison_result"))
    o = dict(out)
    o["analysis_route"] = route
    o["analysis_entry_result"] = entry
    o["analysis_readiness"] = readiness
    o["next_analysis_action"] = entry.get("next_analysis_action") or ""
    o["route_based_response_text"] = entry.get("route_based_response_text") or ""

    rtxt = (entry.get("route_based_response_text") or "").strip()
    intent = o.get("intent")
    scope = o.get("scope")
    body = (o.get("response_text") or "").strip()

    if intent == "legal_risk" or scope == "out_of_scope":
        return o
    if not rtxt or rtxt in body:
        return o

    rt = route.get("route_type")
    if rt in (
        "property_analysis_candidate",
        "area_analysis_candidate",
        "property_comparison",
    ):
        o["response_text"] = f"{rtxt}\n\n{body}".strip()
    return o

def _build_decision_block(result: dict[str, Any]) -> dict[str, Any]:
    intent = result.get("intent") or "general_unknown"
    scope = result.get("scope") or "rental_related"
    readiness = result.get("analysis_readiness") or "pending"
    route = result.get("analysis_route") or {}
    route_type = route.get("route_type") or "general_chat_only"
    missing_inputs = list(route.get("missing_inputs") or [])
    next_analysis_action = str(result.get("next_analysis_action") or "").strip()
    suggested_followup = str(result.get("suggested_followup") or "").strip()
    next_step_prompt = str(result.get("next_step_prompt") or "").strip()

    def pick_action(*values: str) -> str:
        for value in values:
            text = str(value or "").strip()
            if text:
                return text
        return ""

    if scope == "out_of_scope":
        return {
            "decision_status": "redirect",
            "decision_title": "Outside RentalAI Focus",
            "decision_summary": "This request is outside the main rental workflow.",
            "decision_action": pick_action(
                suggested_followup,
                next_step_prompt,
                "Ask about renting, tenancy, deposits, bills, or comparing rental options.",
            ),
        }

    if intent == "legal_risk":
        source_result = result.get("source_result") or {}
        risk_level = str(source_result.get("risk_level") or "").lower()

        if risk_level == "high":
            return {
                "decision_status": "caution",
                "decision_title": "High Legal Risk Detected",
                "decision_summary": "The wording suggests a higher-risk tenancy issue.",
                "decision_action": pick_action(
                    suggested_followup,
                    next_step_prompt,
                    "Review the clause carefully and prepare the next legal or evidence step.",
                ),
            }

        if risk_level == "medium":
            return {
                "decision_status": "review",
                "decision_title": "Review Recommended",
                "decision_summary": "Some tenancy wording may need closer review.",
                "decision_action": pick_action(
                    suggested_followup,
                    next_step_prompt,
                    "Check the clause details and clarify any missing context.",
                ),
            }

        if risk_level == "low":
            return {
                "decision_status": "proceed_lightly",
                "decision_title": "Low Immediate Risk",
                "decision_summary": "No strong legal warning is visible from the current rule-based check.",
                "decision_action": pick_action(
                    suggested_followup,
                    next_step_prompt,
                    "You can continue reviewing details or compare with another property.",
                ),
            }

        return {
            "decision_status": "review",
            "decision_title": "Legal Review Started",
            "decision_summary": "A tenancy-related check was completed, but more detail may improve confidence.",
            "decision_action": pick_action(
                suggested_followup,
                next_step_prompt,
                "Share more contract wording if you want a stronger review.",
            ),
        }

    if route_type == "property_comparison":
        comp = result.get("comparison_result") or {}
        missing = list(comp.get("missing_information") or [])

        if missing:
            return {
                "decision_status": "partial_compare",
                "decision_title": "Partial Comparison Ready",
                "decision_summary": "A side-by-side comparison is available, but some important details are still missing.",
                "decision_action": pick_action(
                    next_analysis_action,
                    suggested_followup,
                    next_step_prompt,
                    "Add the missing rent, bills, or postcode details to improve the comparison.",
                ),
            }

        return {
            "decision_status": "comparison_ready",
            "decision_title": "Comparison Ready",
            "decision_summary": "The comparison route is active and usable from the details already shared.",
            "decision_action": pick_action(
                next_analysis_action,
                suggested_followup,
                next_step_prompt,
                "Review the differences and decide which property fits your priorities better.",
            ),
        }

    if route_type == "property_analysis_candidate":
        if readiness == "ready":
            return {
                "decision_status": "ready",
                "decision_title": "Property Analysis Ready",
                "decision_summary": "The current input is strong enough to move into property-style analysis.",
                "decision_action": pick_action(
                    next_analysis_action,
                    next_step_prompt,
                    suggested_followup,
                    "Proceed with deeper property review when that module is connected.",
                ),
            }

        if readiness == "partial":
            fallback = (
                "Add " + ", ".join(missing_inputs[:3]) + "."
                if missing_inputs else
                "Add a bit more property detail to strengthen the next step."
            )
            return {
                "decision_status": "needs_more_input",
                "decision_title": "Property Analysis Partially Ready",
                "decision_summary": "This already looks like a property case, but a few key inputs are still missing.",
                "decision_action": pick_action(
                    next_analysis_action,
                    next_step_prompt,
                    suggested_followup,
                    fallback,
                ),
            }

    if route_type == "area_analysis_candidate":
        if readiness == "ready":
            return {
                "decision_status": "ready",
                "decision_title": "Area Analysis Ready",
                "decision_summary": "The current input is suitable for postcode or area-level analysis.",
                "decision_action": pick_action(
                    next_analysis_action,
                    next_step_prompt,
                    suggested_followup,
                    "Proceed with deeper area review when that module is connected.",
                ),
            }

        if readiness == "partial":
            fallback = (
                "Add " + ", ".join(missing_inputs[:3]) + "."
                if missing_inputs else
                "Add a postcode or clearer area detail."
            )
            return {
                "decision_status": "needs_more_input",
                "decision_title": "Area Analysis Partially Ready",
                "decision_summary": "Area routing is working, but one or two location details would improve the result.",
                "decision_action": pick_action(
                    next_analysis_action,
                    next_step_prompt,
                    suggested_followup,
                    fallback,
                ),
            }

    if readiness == "pending":
        return {
            "decision_status": "pending",
            "decision_title": "More Context Needed",
            "decision_summary": "The request is still too broad for a stronger rental decision.",
            "decision_action": pick_action(
                next_analysis_action,
                next_step_prompt,
                suggested_followup,
                "Share a postcode, address, listing text, or contract clause.",
            ),
        }

    if readiness == "partial":
        fallback = (
            "Add " + ", ".join(missing_inputs[:3]) + "."
            if missing_inputs else
            "Add more specific rental details."
        )
        return {
            "decision_status": "needs_more_input",
            "decision_title": "Partially Ready",
            "decision_summary": "The workflow has identified a likely path, but more detail would improve the next step.",
            "decision_action": pick_action(
                next_analysis_action,
                next_step_prompt,
                suggested_followup,
                fallback,
            ),
        }

    return {
        "decision_status": "ready",
        "decision_title": "Ready For Next Step",
        "decision_summary": "The request has enough structure to continue through the rental workflow.",
        "decision_action": pick_action(
            next_analysis_action,
            next_step_prompt,
            suggested_followup,
            "Continue with the next recommended rental step.",
        ),
    }

def _build_product_output(result: dict[str, Any]) -> dict[str, Any]:
    decision = result.get("decision") or {}
    display_sections = result.get("display_sections") or {}
    analysis_route = result.get("analysis_route") or {}

    out: dict[str, Any] = {
        "status": "ok" if result.get("success") else "error",
        "intent": result.get("intent") or "",
        "scope": result.get("scope") or "",
        "scope_handling": result.get("scope_handling") or "",
        "analysis_readiness": result.get("analysis_readiness") or "",
        "route_type": analysis_route.get("route_type") or "",
        "route_confidence": analysis_route.get("route_confidence"),
        "decision": {
            "status": decision.get("decision_status") or "",
            "title": decision.get("decision_title") or "",
            "summary": decision.get("decision_summary") or "",
            "action": decision.get("decision_action") or "",
        },
        "sections": {
            "summary": display_sections.get("summary") or "",
            "decision": list(display_sections.get("decision") or []),
            "what_i_found": list(display_sections.get("what_i_found") or []),
            "key_points": list(display_sections.get("key_points") or []),
            "next_steps": list(display_sections.get("next_steps") or []),
            "followups": list(display_sections.get("followups") or []),
            "alternative_help": list(display_sections.get("alternative_help") or []),
        },
        "next_actions": list(display_sections.get("next_steps") or []),
        "followups": list(display_sections.get("followups") or []),
        "meta": {
            "module": result.get("module") or "",
            "source_module": result.get("source_module") or "",
            "available_next_modules": list(result.get("available_next_modules") or []),
            "available_capabilities": list(result.get("available_capabilities") or []),
        },
    }
    er = result.get("explain_result")
    if isinstance(er, dict):
        out["explain_result"] = er
    return out

def _finish_chat_response(
    base: dict[str, Any],
    scope_info: dict[str, Any],
    bundle: dict[str, Any],
    trimmed: str,
    pi_parsed: dict[str, Any],
    pi_ref: dict[str, Any],
) -> dict[str, Any]:
    out = _merge_followup(_merge_scope_into(base, scope_info), bundle)
    out = _attach_property_input(out, pi_parsed, pi_ref)
    pref_det = detect_user_preferences(trimmed)
    out = _attach_uk_location(out, trimmed, pi_parsed, pi_ref, pref_det)
    out = _apply_analysis_route(out, trimmed, pi_parsed, pi_ref, scope_info)
    out = _with_preferences(out, trimmed, pref_det)
    out = _append_uk_location_hint(out)
    out = _append_property_hint(out, pi_parsed)
    out["decision"] = _build_decision_block(out)
    disp = build_chat_display_bundle(out)
    out["display_text"] = disp["display_text"]
    out["display_sections"] = disp["display_sections"]
    out["display_order"] = disp.get("display_order") or []
    out["display_meta"] = disp.get("display_meta") or {}
    out["product_output"] = _build_product_output(out)
    return out

def handle_chat_request(user_text: str) -> dict[str, Any]:
    """
    Single entry for the chat orchestrator. Routes to Phase 0 for legal/contract queries.

    Flow: scope → intent → modules. Out-of-scope queries skip Phase 0.
    """
    trimmed = (user_text or "").strip()
    if not trimmed:
        return _failure_empty()

    pi_parsed = parse_property_input(trimmed)
    pi_ref = build_property_reference(pi_parsed)

    scope_info = classify_query_scope(trimmed)
    scope = scope_info.get("scope") or "rental_related"

    if scope == "out_of_scope":
        sm = build_scope_message("out_of_scope", list(scope_info.get("matched_keywords") or []))
        bundle = build_chat_followup_bundle("general_unknown", source_result=None)
        base = {
            "module": MODULE_ID,
            "success": True,
            "intent": "out_of_scope",
            "input_text": trimmed,
            "response_text": sm,
            "source_module": None,
            "source_result": None,
            "comparison_inputs": None,
            "comparison_result": None,
            "suggested_followup": (
                "Ask about renting, tenancy agreements, deposits, or bills if you would like to continue."
            ),
            "available_next_modules": AVAILABLE_NEXT_MODULES,
        }
        return _finish_chat_response(base, scope_info, bundle, trimmed, pi_parsed, pi_ref)

    intent = classify_intent(trimmed)

    if intent == "property_comparison":
        inputs = extract_property_comparison_inputs(trimmed)
        if not inputs["is_comparison"]:
            inputs = coerce_comparison_inputs(trimmed)
        sa = build_property_snapshot_from_side(inputs["property_a"])
        sb = build_property_snapshot_from_side(inputs["property_b"])
        prefs = detect_user_preferences(trimmed)
        comp = run_basic_property_comparison(sa, sb, prefs)
        response = build_comparison_response_text(comp)
        bundle = build_chat_followup_bundle("property_comparison", source_result=None)
        response = append_guidance_footer(response, str(bundle.get("response_closing") or ""))
        response = _prepend_related_lead(response, scope_info)
        base = {
            "module": MODULE_ID,
            "success": True,
            "intent": "property_comparison",
            "input_text": trimmed,
            "response_text": response,
            "source_module": "property_comparison",
            "source_result": comp,
            "comparison_inputs": inputs,
            "comparison_result": comp,
            "suggested_followup": str(comp.get("next_step_hint") or ""),
            "available_next_modules": AVAILABLE_NEXT_MODULES,
        }
        return _finish_chat_response(base, scope_info, bundle, trimmed, pi_parsed, pi_ref)

    if intent == "legal_risk":
        p0 = run_phase0_analysis(trimmed)
        response = p0.get("display_text") or ""
        if not p0.get("success"):
            response = response or str(p0.get("error") or "Analysis could not be completed.")
        follow = str(p0.get("suggested_followup") or "")
        bundle = build_chat_followup_bundle("legal_risk", source_result=p0)
        response = append_guidance_footer(response, str(bundle.get("response_closing") or ""))
        response = _prepend_related_lead(response, scope_info)
        base = {
            "module": MODULE_ID,
            "success": True,
            "intent": "legal_risk",
            "input_text": trimmed,
            "response_text": response,
            "source_module": "phase0_legal_risk",
            "source_result": p0,
            "comparison_inputs": None,
            "comparison_result": None,
            "suggested_followup": follow,
            "available_next_modules": AVAILABLE_NEXT_MODULES,
        }
        return _finish_chat_response(base, scope_info, bundle, trimmed, pi_parsed, pi_ref)

    msg = _PLACEHOLDER_COPY.get(intent, _PLACEHOLDER_COPY["general_unknown"])
    bundle = build_chat_followup_bundle(intent, source_result=None)
    msg = append_guidance_footer(msg, str(bundle.get("response_closing") or ""))
    msg = _prepend_related_lead(msg, scope_info)
    base = {
        "module": MODULE_ID,
        "success": True,
        "intent": intent,
        "input_text": trimmed,
        "response_text": msg,
        "source_module": None,
        "source_result": None,
        "comparison_inputs": None,
        "comparison_result": None,
        "suggested_followup": (
            "Ask about a contract clause or deposit if you want a rules-based check today."
        ),
        "available_next_modules": AVAILABLE_NEXT_MODULES,
    }
    return _finish_chat_response(base, scope_info, bundle, trimmed, pi_parsed, pi_ref)
