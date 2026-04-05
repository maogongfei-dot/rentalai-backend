"""
Phase 1 Part 7: bridge property/area/comparison inputs to downstream analysis modules (no scraping).
"""

from __future__ import annotations

from typing import Any


def _decide_analysis_route_core(context: dict[str, Any]) -> dict[str, Any]:
    """
    Choose analysis path from intent, scope, property_input parse, and comparison payloads.

    Context keys: intent, scope_info, property_input_parsed, comparison_inputs,
    comparison_result, user_text (optional).
    """
    intent = context.get("intent") or "general_unknown"
    scope_info = context.get("scope_info") or {}
    scope = scope_info.get("scope") or ""
    pip = context.get("property_input_parsed") or {}
    cit = pip.get("input_type") or "unknown"
    comp_in = context.get("comparison_inputs") or {}
    comp_res = context.get("comparison_result") or {}
    low = " ".join((context.get("user_text") or "").lower().split())
    uk_ctx = context.get("uk_location_context") or {}

    # 1) Comparison — highest priority
    if intent == "property_comparison" or comp_in.get("is_comparison"):
        missing = list(comp_res.get("missing_information") or [])
        return {
            "route_type": "property_comparison",
            "route_reason": "Comparison intent or two-side comparison parse is active.",
            "route_confidence": 0.92,
            "analysis_ready": bool(comp_res.get("comparison_ready")),
            "missing_inputs": missing,
            "next_module_target": "comparison",
        }

    if scope == "out_of_scope":
        return {
            "route_type": "general_chat_only",
            "route_reason": "Query is outside the rental-focused scope.",
            "route_confidence": 0.35,
            "analysis_ready": False,
            "missing_inputs": [],
            "next_module_target": "none",
        }

    # Explicit intents from keyword router
    if intent == "area_info":
        return {
            "route_type": "area_analysis_candidate",
            "route_reason": "Message matches area / neighbourhood style routing.",
            "route_confidence": 0.8,
            "analysis_ready": False,
            "missing_inputs": [
                "Postcode or neighbourhood name for a tighter area read",
            ],
            "next_module_target": "area_analysis",
        }

    if intent == "property_analysis":
        return {
            "route_type": "property_analysis_candidate",
            "route_reason": "Message matches property analysis style routing.",
            "route_confidence": 0.82,
            "analysis_ready": False,
            "missing_inputs": _property_missing(pip),
            "next_module_target": "property_analysis",
        }

    # Property input classifier
    if cit in ("rightmove_link", "zoopla_link", "openrent_link"):
        miss = ["Live listing fields once a feed is connected"]
        miss.extend(_property_missing(pip))
        return {
            "route_type": "property_analysis_candidate",
            "route_reason": "A portal listing URL is present.",
            "route_confidence": 0.9,
            "analysis_ready": False,
            "missing_inputs": list(dict.fromkeys(miss))[:8],
            "next_module_target": "property_analysis",
        }

    if cit == "property_description":
        return {
            "route_type": "property_analysis_candidate",
            "route_reason": "Listing-style description text detected.",
            "route_confidence": 0.84,
            "analysis_ready": True,
            "missing_inputs": _property_missing(pip),
            "next_module_target": "property_analysis",
        }

    if cit == "address":
        return {
            "route_type": "property_analysis_candidate",
            "route_reason": "Street-style address detected.",
            "route_confidence": 0.83,
            "analysis_ready": False,
            "missing_inputs": ["Postcode or monthly rent if you want a fuller listing view"],
            "next_module_target": "property_analysis",
        }

    if cit == "postcode":
        if (
            uk_ctx.get("location_type") == "mixed"
            and uk_ctx.get("city")
            and uk_ctx.get("postcode")
        ):
            pc_reason = (
                "City and postcode together; suitable for area-level and local analysis."
            )
        else:
            pc_reason = "Postcode-only input suits area and surroundings review."
        return {
            "route_type": "area_analysis_candidate",
            "route_reason": pc_reason,
            "route_confidence": 0.78,
            "analysis_ready": False,
            "missing_inputs": [
                "Street or building context if you want block-level detail",
            ],
            "next_module_target": "area_analysis",
        }

    if cit == "location_text":
        return {
            "route_type": "area_analysis_candidate",
            "route_reason": "City or broad location without a full listing description.",
            "route_confidence": 0.72,
            "analysis_ready": False,
            "missing_inputs": ["Postcode to anchor transport and amenities"],
            "next_module_target": "area_analysis",
        }

    if cit == "mixed":
        if pip.get("detected_links") or pip.get("detected_addresses"):
            return {
                "route_type": "property_analysis_candidate",
                "route_reason": "Mixed input includes a link or address-like segment.",
                "route_confidence": 0.8,
                "analysis_ready": False,
                "missing_inputs": _property_missing(pip),
                "next_module_target": "property_analysis",
            }
        if pip.get("detected_postcodes") and (
            pip.get("detected_price") or _has_listing_words(low)
        ):
            return {
                "route_type": "property_analysis_candidate",
                "route_reason": "Postcode plus listing-style rent or room wording.",
                "route_confidence": 0.79,
                "analysis_ready": False,
                "missing_inputs": _property_missing(pip),
                "next_module_target": "property_analysis",
            }
        if pip.get("detected_postcodes"):
            return {
                "route_type": "area_analysis_candidate",
                "route_reason": "Mixed input is postcode-led for area-style review.",
                "route_confidence": 0.74,
                "analysis_ready": False,
                "missing_inputs": [
                    "Monthly rent or room details if you want listing-style analysis",
                ],
                "next_module_target": "area_analysis",
            }
        return {
            "route_type": "property_analysis_candidate",
            "route_reason": "Mixed property clues without a single dominant pattern.",
            "route_confidence": 0.65,
            "analysis_ready": False,
            "missing_inputs": _property_missing(pip),
            "next_module_target": "property_analysis",
        }

    # Area keywords without strong listing payload
    if _area_keywords(low) and not pip.get("is_property_reference"):
        return {
            "route_type": "area_analysis_candidate",
            "route_reason": "Area, transport, or neighbourhood wording detected.",
            "route_confidence": 0.68,
            "analysis_ready": False,
            "missing_inputs": ["Postcode or city name to anchor the map later"],
            "next_module_target": "area_analysis",
        }

    if pip.get("is_property_reference"):
        return {
            "route_type": "property_analysis_candidate",
            "route_reason": "Loose property-related signals without a clearer label.",
            "route_confidence": 0.55,
            "analysis_ready": False,
            "missing_inputs": ["A postcode, link, or clearer description"],
            "next_module_target": "property_analysis",
        }

    return {
        "route_type": "general_chat_only",
        "route_reason": "No dedicated listing, postcode-led area, or comparison target yet.",
        "route_confidence": 0.45,
        "analysis_ready": False,
        "missing_inputs": [
            "A property link, postcode, address, or short listing description",
        ],
        "next_module_target": "none",
    }


def _join_route_reason(base: str, suffix: str) -> str:
    b = (base or "").strip()
    if not b:
        return suffix
    if b.endswith("."):
        return f"{b} {suffix}"
    return f"{b}. {suffix}"


def _enhance_route_with_uk(route: dict[str, Any], uk: dict[str, Any] | None) -> dict[str, Any]:
    if not uk or uk.get("location_type") == "unknown":
        return dict(route)
    r = dict(route)
    lt = uk.get("location_type")
    city = uk.get("city")
    pc = uk.get("postcode")
    base = (r.get("route_reason") or "").strip()
    if lt == "mixed" and city and pc:
        r["route_reason"] = _join_route_reason(
            base,
            "Both city and postcode context were detected, "
            "which is useful for more precise local analysis later.",
        )
    elif lt == "city" and city:
        r["route_reason"] = _join_route_reason(
            base,
            f"A UK city context ({city}) was detected, "
            "so this can later be used for area-level analysis.",
        )
    elif lt == "postcode" and pc:
        r["route_reason"] = _join_route_reason(
            base,
            f"A UK postcode ({pc}) was detected, "
            "so this can later be used for more targeted area analysis.",
        )
    else:
        return r
    rc = float(r.get("route_confidence") or 0.5)
    r["route_confidence"] = round(min(0.95, rc + 0.02), 2)
    return r


def decide_analysis_route(context: dict[str, Any]) -> dict[str, Any]:
    uk = context.get("uk_location_context") or {}
    route = _decide_analysis_route_core(context)
    return _enhance_route_with_uk(route, uk)


def _property_missing(pip: dict[str, Any]) -> list[str]:
    miss: list[str] = []
    if pip.get("detected_price") is None:
        miss.append("Monthly rent")
    if pip.get("bills_included") is None:
        miss.append("Bill details")
    return miss


def _has_listing_words(low: str) -> bool:
    return any(
        w in low
        for w in (
            "flat",
            "house",
            "studio",
            "bed",
            "pcm",
            "rent",
            "bills",
            "furnished",
        )
    )


def _area_keywords(low: str) -> bool:
    return any(
        x in low
        for x in (
            "neighbourhood",
            "neighborhood",
            "local area",
            "crime",
            "transport",
            "commute",
            "school catchment",
            "nearby shops",
            "facilities",
        )
    )


def build_analysis_entry_result(
    route: dict[str, Any],
    context: dict[str, Any],
    property_reference: dict[str, Any],
) -> dict[str, Any]:
    """
    Human-readable entry payload: summaries, next action, and a short product line for UI.
    """
    rt = route.get("route_type") or "general_chat_only"
    missing = list(route.get("missing_inputs") or [])
    next_mod = route.get("next_module_target") or "none"
    pref = context.get("property_reference") or property_reference
    uk = context.get("uk_location_context") or {}

    next_action = ""
    if missing:
        next_action = (
            "You can share " + _nice_join(missing[:3]) + " to sharpen the next step."
        )

    if rt == "property_analysis_candidate":
        summary = {
            "recognized": _property_recognized(pref, context),
            "listing_analysis": "Can move into listing analysis when modules are connected.",
            "data_note": (
                "Full platform fields are not loaded yet; a text-first review is still possible."
                if pref.get("url")
                else "A partial review can start from the text you have already shared."
            ),
        }
        line = (
            "This looks like a property reference, so it can move into listing analysis. "
            "I can already do a partial review from what you typed, and this can later expand with full listing data."
        )
    elif rt == "area_analysis_candidate":
        summary = {
            "recognized": _area_recognized(pref, context),
            "area_analysis": "Can move into area analysis for transport, amenities, and rent context.",
            "data_note": "Map-backed detail can plug in later without changing this flow.",
        }
        line = (
            "This looks more like an area or postcode check, so it can move into area analysis. "
            "I can use this as a starting point for local area, transport, and nearby facilities review."
        )
    elif rt == "property_comparison":
        summary = {
            "comparison": "Handled as a two-sided property comparison.",
            "reuse": "Uses the existing comparison_result from this turn.",
        }
        line = "This request is best handled as a property comparison."
        comp = context.get("comparison_result") or {}
        if comp.get("missing_information"):
            next_action = (
                "You can share "
                + _nice_join(list(comp["missing_information"])[:3])
                + " to improve the comparison."
            )
    else:
        summary = {
            "chat": "Continue with normal rental guidance until a postcode, link, or description appears.",
        }
        line = ""

    route_based = line.strip()

    if uk.get("is_supported_uk_context"):
        summary["uk_location_context"] = {
            "city": uk.get("city"),
            "postcode": uk.get("postcode"),
            "location_type": uk.get("location_type"),
        }
        uk_extra = ""
        lt = uk.get("location_type")
        if lt == "mixed" and uk.get("city") and uk.get("postcode"):
            uk_extra = (
                "Both city and postcode context were detected, "
                "which is useful for more precise local analysis later."
            )
        elif lt == "city" and uk.get("city"):
            uk_extra = (
                "A UK city context was detected, so this can later be used for area-level analysis."
            )
        elif lt == "postcode" and uk.get("postcode"):
            uk_extra = (
                "A postcode was detected, so this can later be used for more targeted area analysis."
            )
        if uk_extra:
            if next_action:
                next_action = f"{next_action} {uk_extra}"
            else:
                next_action = uk_extra

    return {
        "route_summary": summary,
        "missing_inputs": missing,
        "next_module_target": next_mod,
        "next_analysis_action": next_action or route_based,
        "route_based_response_text": route_based,
    }


def _nice_join(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} or {items[1]}"
    return ", ".join(items[:-1]) + f", or {items[-1]}"


def _property_recognized(pref: dict[str, Any], context: dict[str, Any]) -> list[str]:
    out: list[str] = []
    if pref.get("url"):
        out.append("Listing URL")
    if pref.get("address_text"):
        out.append("Address line")
    if pref.get("postcode"):
        out.append("Postcode")
    if pref.get("city"):
        out.append("City or area")
    if pref.get("price"):
        out.append("Rent figure")
    pip = context.get("property_input_parsed") or {}
    if pip.get("property_signals"):
        out.append("Listing keywords")
    return out or ["Text clues only"]


def _area_recognized(pref: dict[str, Any], context: dict[str, Any]) -> list[str]:
    out: list[str] = []
    if pref.get("postcode"):
        out.append("Postcode")
    if pref.get("city"):
        out.append("Location")
    pip = context.get("property_input_parsed") or {}
    if pip.get("detected_locations"):
        out.extend(pip["detected_locations"][:2])
    return out or ["Area wording"]


def compute_analysis_readiness(
    route: dict[str, Any],
    entry: dict[str, Any],
    comparison_result: dict[str, Any] | None,
) -> str:
    """ready | partial | pending"""
    rt = route.get("route_type")
    if rt == "property_comparison":
        comp = comparison_result or {}
        if comp.get("missing_information"):
            return "partial"
        return "ready"
    if rt == "general_chat_only":
        return "pending"
    if route.get("missing_inputs"):
        return "partial"
    return "ready"


def empty_analysis_route() -> dict[str, Any]:
    return {
        "route_type": "general_chat_only",
        "route_reason": "No input to route.",
        "route_confidence": 0.0,
        "analysis_ready": False,
        "missing_inputs": [],
        "next_module_target": "none",
    }


def empty_analysis_entry() -> dict[str, Any]:
    return {
        "route_summary": {},
        "missing_inputs": [],
        "next_module_target": "none",
        "next_analysis_action": "",
        "route_based_response_text": "",
    }
