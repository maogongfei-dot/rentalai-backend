"""
Phase 1 Part 9: structured display text for chat results (layout only; no new analysis).
"""

from __future__ import annotations

import re
from typing import Any

from modules.decision.decision_engine import build_decision_result
from modules.followup.followup_engine import build_followup_questions
from modules.missing_info.missing_info_engine import build_missing_info_items
from modules.output.response_formatter import build_final_response_text

# Section titles — keep stable for CLI and future UI mapping.
TITLE_SUMMARY = "【Conclusion】"
TITLE_DECISION = "【Decision】"
TITLE_FOUND = "【What I Found】"
TITLE_KEY = "【Key Points】"
TITLE_NEXT = "【Next Step】"
TITLE_FOLLOW = "【You Can Also Ask】"
TITLE_INSTEAD = "【What I Can Help With Instead】"
TITLE_RISK_CLAUSES = "【Risk Clauses】"
TITLE_NEED_CONFIRM = "【Need To Confirm】"
TITLE_ASK_LANDLORD = "【Questions To Ask Landlord】"
TITLE_FINAL_RECOMMENDATION = "【Final Recommendation】"
TITLE_WHY = "【Why】"
TITLE_MAIN_RISKS = "【Main Risks】"
TITLE_WHAT_TO_DO_NEXT = "【What To Do Next】"
TITLE_BEST_OPTION = "【Best Option】"
TITLE_CHEAPEST_OPTION = "【Cheapest Option】"
TITLE_LOWEST_RISK_OPTION = "【Lowest Risk Option】"
TITLE_WATCH_OUT = "【Watch Out】"
TITLE_FINAL_ADVICE = "【Final Advice】"
TITLE_REPUTATION_CHECK = "【Reputation Check】"
TITLE_LOCATION_INSIGHT = "【Location Insight】"

NO_MAJOR_RISK_TEXT = (
    "No major risk was found from the available text, but you should still confirm rent, "
    "deposit, bills, repair responsibility, and break clause before signing."
)
SINGLE_PROPERTY_COMPARE_TEXT = (
    "I only have one property to review, so I can assess it but cannot compare it against alternatives yet."
)
COMPARE_NEED_MORE_TEXT = (
    "To compare properties better, please share rent, postcode, bills, bedroom count, and commute preference."
)
NO_REPUTATION_DATA_TEXT = (
    "No reputation data is available yet for this address, building, or agency."
)
LIMITED_LOCATION_TEXT = "Location detail is limited. Sharing a postcode can help improve the analysis."


def _clean_str(x: Any) -> str:
    if x is None:
        return ""
    s = str(x).strip()
    return s


def _first_sentence(text: str, max_len: int = 320) -> str:
    t = " ".join(text.split())
    if not t:
        return ""
    m = re.match(r"([^.!?]+[.!?]|[^.!?]+$)", t)
    chunk = (m.group(1) if m else t).strip()
    if len(chunk) > max_len:
        return chunk[: max_len - 1].rstrip() + "…"
    return chunk


def _split_bullets(text: str) -> list[str]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return lines[:12]


def _comparison_point_lines(comp: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for p in comp.get("comparison_points") or []:
        if not isinstance(p, dict):
            continue
        dim = _clean_str(p.get("dimension"))
        note = _clean_str(p.get("note"))
        w = _clean_str(p.get("winner"))
        if dim and note:
            tag = f" ({w})" if w else ""
            out.append(f"{dim}{tag}: {note}")
        elif note:
            out.append(note)
    return out[:8]


def _property_ref_bullets(pref: dict[str, Any], pip: dict[str, Any]) -> list[str]:
    out: list[str] = []
    if pref.get("postcode"):
        out.append(f"📍 Postcode noted: {pref['postcode']}")
    if pref.get("city"):
        out.append(f"📍 City / area: {pref['city']}")
    if pref.get("url"):
        out.append("Listing link detected.")
    if pref.get("address_text"):
        out.append("Address text detected.")
    sig = pip.get("property_signals") or []
    if isinstance(sig, list) and sig:
        out.append(f"Listing signals: {', '.join(str(s) for s in sig[:5])}")
    return out


def _uk_bullets(uk: dict[str, Any]) -> list[str]:
    out: list[str] = []
    if not uk.get("is_supported_uk_context"):
        return out
    lt = uk.get("location_type")
    if lt == "mixed" and uk.get("city") and uk.get("postcode"):
        out.append(f"📍 UK context: {uk['city']} · {uk['postcode']}")
    elif uk.get("city"):
        out.append(f"📍 UK city context: {uk['city']}")
    elif uk.get("postcode"):
        out.append(f"📍 UK postcode: {uk['postcode']}")
    if uk.get("area_text"):
        out.append(f"Area wording: {uk['area_text']}")
    return out


def _route_brief(ar: dict[str, Any]) -> str:
    return _clean_str(ar.get("route_reason"))


def _clean_list(items: Any, limit: int = 10) -> list[str]:
    if not isinstance(items, list):
        return []
    out: list[str] = []
    for x in items:
        t = _clean_str(x)
        if t:
            out.append(t)
        if len(out) >= limit:
            break
    return out


def _risk_conclusion_line(raw_level: str) -> str:
    rl = _clean_str(raw_level).lower()
    if rl == "high":
        return "Overall this looks high risk from a rental-contract perspective."
    if rl == "medium":
        return "Overall this looks medium risk and needs careful checks before signing."
    if rl == "low":
        return "Overall this looks low risk from the wording provided."
    return "Overall risk needs further confirmation from the available wording."


def _clean_legal_list(items: Any, *, drop_prefixes: tuple[str, ...] = ()) -> list[str]:
    out: list[str] = []
    for raw in items or []:
        t = _clean_str(raw)
        if not t:
            continue
        low = t.lower()
        if any(low.startswith(p.lower()) for p in drop_prefixes):
            continue
        if t not in out:
            out.append(t)
    return out


def _build_landlord_questions(need_to_confirm: list[str], risk_clauses: list[str]) -> list[str]:
    questions: list[str] = []
    for item in need_to_confirm[:4]:
        q = item.rstrip(".?")
        questions.append(f"Can you confirm in writing: {q}?")
    if not questions:
        for item in risk_clauses[:2]:
            q = item.rstrip(".?")
            questions.append(f"Could you clarify this clause in writing: {q}?")
    return questions[:5]


def _final_recommendation_label(r: dict[str, Any]) -> str:
    scope = _clean_str(r.get("scope"))
    intent = _clean_str(r.get("intent"))
    readiness = _clean_str(r.get("analysis_readiness"))
    decision = r.get("decision") if isinstance(r.get("decision"), dict) else {}
    ds = _clean_str(decision.get("decision_status")).lower()
    risk_level = _clean_str(
        ((r.get("source_result") or {}).get("risk_level"))
        or (((r.get("source_result") or {}).get("normalized_result") or {}).get("raw_level"))
    ).lower()
    if scope == "out_of_scope":
        return "Need More Information"
    if intent in ("invalid_input", "half_related", "insufficient_info"):
        return "Need More Information"
    if risk_level == "high" or ds in ("caution", "redirect"):
        return "Not Recommended"
    if risk_level == "medium" or ds in ("review", "needs_more_input", "partial_compare", "pending", "proceed_lightly"):
        return "Caution"
    if readiness in ("pending", "partial"):
        return "Need More Information"
    if risk_level == "low" or ds in ("ready", "comparison_ready"):
        return "Recommended"
    return "Need More Information"


def _extract_main_risks(r: dict[str, Any], sections: dict[str, Any]) -> list[str]:
    risks: list[str] = []
    txt = " ".join(
        [
            _clean_str(r.get("response_text")).lower(),
            " ".join(_clean_list((r.get("analysis_route") or {}).get("missing_inputs") or [], limit=20)).lower(),
            " ".join(_clean_list((r.get("missing_key_fields") or []), limit=20)).lower(),
        ]
    )
    if "rent" in txt and ("missing" in txt or "light on" in txt):
        risks.append("rent too high or not confirmed")
    if "bill" in txt or "utility" in txt or "council tax" in txt:
        risks.append("bills unclear")
    if _clean_str(r.get("intent")) == "legal_risk":
        risks.append("contract risk")
    if "postcode" in txt or "city" in txt or "area" in txt:
        risks.append("location uncertainty")
    if "repair" in txt or "maintenance" in txt:
        risks.append("repair responsibility unclear")

    legal_risks = _clean_list(sections.get("risk_clauses") or [], limit=6)
    for lr in legal_risks:
        if NO_MAJOR_RISK_TEXT.lower() in lr.lower():
            continue
        short = _first_sentence(lr, 120)
        if short and short not in risks:
            risks.append(short)
    if not risks and _clean_str(r.get("analysis_readiness")) in ("pending", "partial"):
        risks.append("not enough confirmed rental details yet")
    return risks[:6]


def _build_final_summary_fields(r: dict[str, Any], sections: dict[str, Any]) -> dict[str, Any]:
    label = _final_recommendation_label(r)
    why: list[str] = []
    scope = _clean_str(r.get("scope"))
    readiness = _clean_str(r.get("analysis_readiness"))
    route_reason = _clean_str((r.get("analysis_route") or {}).get("route_reason"))
    if scope == "out_of_scope":
        why.append("The question is outside the rental-focused workflow.")
    elif label == "Need More Information":
        why.append("The current details are not enough for a reliable recommendation.")
    elif label == "Not Recommended":
        why.append("There are strong risk signals that should be resolved first.")
    elif label == "Caution":
        why.append("There are unresolved points that need written confirmation.")
    elif label == "Recommended":
        why.append("No major blocker appears from the available rental details.")
    if route_reason:
        why.append(_first_sentence(route_reason, 140))
    if readiness in ("pending", "partial") and "not enough detail" not in " ".join(why).lower():
        why.append("Some key inputs are still missing.")
    location_info = r.get("location_info") if isinstance(r.get("location_info"), dict) else {}
    loc_status = _clean_str(location_info.get("status")).lower()
    if loc_status == "ok":
        transport = _clean_str(location_info.get("transport_hint"))
        nearby = _clean_list(location_info.get("nearby_points") or [], limit=3)
        if transport and "unknown" not in transport.lower():
            why.append(f"Location suggests decent commute convenience ({transport}).")
        if nearby:
            why.append("Nearby facilities look practical for daily living.")
    else:
        why.append("Potential location risk remains uncertain without clearer postcode-level detail.")
    why = list(dict.fromkeys([w for w in why if w]))[:4]

    main_risks = _extract_main_risks(r, sections)
    what_to_do_next = _clean_list(sections.get("next_steps") or [], limit=6)
    if not what_to_do_next:
        what_to_do_next = [
            "ask landlord about bills",
            "confirm deposit protection",
            "compare another property",
            "upload contract wording",
        ]
    return {
        "final_recommendation": label,
        "why": why,
        "main_risks": main_risks,
        "what_to_do_next": what_to_do_next,
    }


def _reputation_lines(reputation_result: Any) -> list[str]:
    if not isinstance(reputation_result, dict):
        return []
    level = _clean_str(reputation_result.get("reputation_level")) or "Unknown"
    summary = _clean_str(reputation_result.get("summary"))
    tags = _clean_list(reputation_result.get("risk_tags") or [], limit=6)
    action = _clean_str(reputation_result.get("suggested_action"))
    if level == "Unknown":
        summary = NO_REPUTATION_DATA_TEXT
    lines = [f"Reputation level: {level}"]
    if summary:
        lines.append(f"Summary: {summary}")
    if tags:
        lines.append("Risk tags: " + ", ".join(tags))
    else:
        lines.append("Risk tags: none identified yet")
    if action:
        lines.append(f"Suggested action: {action}")
    return lines


def _location_lines(location_info: Any) -> list[str]:
    if not isinstance(location_info, dict):
        return [LIMITED_LOCATION_TEXT]
    status = _clean_str(location_info.get("status")).lower()
    if status != "ok":
        return [LIMITED_LOCATION_TEXT]
    addr = _clean_str(location_info.get("normalized_address"))
    pc = _clean_str(location_info.get("postcode"))
    city = _clean_str(location_info.get("city"))
    nearby = _clean_list(location_info.get("nearby_points") or [], limit=5)
    transport = _clean_str(location_info.get("transport_hint"))
    lines = []
    if addr and addr != "Unknown":
        lines.append(f"Address context: {addr}")
    if city and city != "Unknown":
        lines.append(f"City: {city}")
    if pc and pc != "Unknown":
        lines.append(f"Postcode: {pc}")
    if nearby:
        lines.append("Nearby points: " + ", ".join(nearby))
    if transport and transport != "Unknown":
        lines.append(f"Transport: {transport}")
    if not lines:
        lines.append(LIMITED_LOCATION_TEXT)
    return lines


def _build_legal_sections(r: dict[str, Any]) -> dict[str, Any]:
    p0 = r.get("source_result") or {}
    norm = p0.get("normalized_result") or {}
    raw_level = _clean_str(norm.get("raw_level") or p0.get("risk_level") or "unknown")
    summary_line = _clean_str(norm.get("summary"))
    conclusion = _risk_conclusion_line(raw_level)
    if summary_line:
        summary = f"{conclusion} {summary_line}"
    else:
        summary = conclusion

    reasons = _clean_legal_list(norm.get("key_reasons") or [])
    risk_clauses = _clean_legal_list(reasons, drop_prefixes=("Flag:",))
    if summary_line and summary_line in risk_clauses:
        risk_clauses = [x for x in risk_clauses if x != summary_line]
    if not risk_clauses and raw_level == "low":
        risk_clauses = [NO_MAJOR_RISK_TEXT]
    elif not risk_clauses:
        risk_clauses = ["I need a bit more specific clause wording to identify clear risk clauses."]

    need_to_confirm = _clean_legal_list(norm.get("legal_basis") or [])
    if len(need_to_confirm) < 3:
        for line in _clean_legal_list(norm.get("recommended_actions") or []):
            if line not in need_to_confirm:
                need_to_confirm.append(line)
    if len(need_to_confirm) < 5:
        for fallback in (
            "Confirm monthly rent amount and payment date in writing.",
            "Confirm deposit amount and protection scheme details.",
            "Confirm which bills are included or excluded.",
            "Confirm repair and maintenance responsibility.",
            "Confirm break clause and notice terms.",
        ):
            if fallback not in need_to_confirm:
                need_to_confirm.append(fallback)
            if len(need_to_confirm) >= 5:
                break

    questions = _build_landlord_questions(need_to_confirm, risk_clauses)

    next_steps: list[str] = []
    next_steps.append("Ask the landlord or agent to confirm the points above in writing.")
    next_steps.append("Update the draft wording before you sign anything.")
    next_steps.append("If any clause still looks unclear or one-sided, get independent housing advice.")
    sf = _clean_str(p0.get("suggested_followup") or r.get("suggested_followup"))
    if sf and sf not in next_steps:
        next_steps.append(sf)

    return {
        "layout": "legal_contract_advisor",
        "summary": summary,
        "risk_clauses": risk_clauses[:6],
        "need_to_confirm": need_to_confirm[:6],
        "questions_to_ask_landlord": questions[:6],
        "what_i_found": risk_clauses[:6],
        "key_points": need_to_confirm[:6],
        "next_steps": next_steps[:8],
        "followups": [],
        "alternative_help": [],
    }


def _winner_for(points: list[dict[str, Any]], dim: str) -> str:
    for p in points:
        if _clean_str(p.get("dimension")) == dim:
            w = _clean_str(p.get("winner"))
            return w if w in ("A", "B", "tie") else "unknown"
    return "unknown"


def _label_for_side(comp: dict[str, Any], side: str) -> str:
    if side == "A":
        return _clean_str(((comp.get("property_a") or {}).get("label"))) or "Property A"
    if side == "B":
        return _clean_str(((comp.get("property_b") or {}).get("label"))) or "Property B"
    return "both options"


def _is_single_property_case(comp: dict[str, Any]) -> bool:
    a = comp.get("property_a") or {}
    b = comp.get("property_b") or {}
    b_label = _clean_str(b.get("label")).lower()
    b_has_details = any(
        [
            b.get("price") is not None,
            bool(b.get("postcode") or b.get("city")),
            b.get("bills_included") is not None,
            bool(b.get("features") or []),
        ]
    )
    return (not b_has_details) and (b_label in ("the other property", "property b", ""))


def _build_comparison_advisor_fields(comp: dict[str, Any]) -> dict[str, Any]:
    points = list(comp.get("comparison_points") or [])
    missing = _clean_list(comp.get("missing_information") or [], limit=8)
    summary = _clean_str(comp.get("comparison_summary"))
    single_case = _is_single_property_case(comp)

    if single_case:
        return {
            "best_option": SINGLE_PROPERTY_COMPARE_TEXT,
            "cheapest_option": "Not enough data to identify a cheapest alternative.",
            "lowest_risk_option": "Not enough data to identify a lower-risk alternative.",
            "watch_out": ["Only one property has usable details right now."],
            "final_advice": SINGLE_PROPERTY_COMPARE_TEXT,
        }

    insufficient = len(missing) >= 3
    if insufficient:
        return {
            "best_option": COMPARE_NEED_MORE_TEXT,
            "cheapest_option": "Price comparison is still incomplete.",
            "lowest_risk_option": "Risk comparison is still incomplete.",
            "watch_out": [COMPARE_NEED_MORE_TEXT],
            "final_advice": "Hold recommendation until key comparison details are complete.",
        }

    price_w = _winner_for(points, "price")
    bills_w = _winner_for(points, "bills")
    commute_w = _winner_for(points, "commute")
    area_w = _winner_for(points, "area")
    safety_w = _winner_for(points, "safety")

    a_score = 0
    b_score = 0
    for w in (price_w, bills_w, commute_w, area_w, safety_w):
        if w == "A":
            a_score += 1
        elif w == "B":
            b_score += 1

    if a_score > b_score:
        best_side = "A"
    elif b_score > a_score:
        best_side = "B"
    else:
        best_side = "unknown"

    lowest_risk_side = "unknown"
    risk_a = 0
    risk_b = 0
    if bills_w == "A":
        risk_b += 1
    elif bills_w == "B":
        risk_a += 1
    if safety_w == "A":
        risk_b += 1
    elif safety_w == "B":
        risk_a += 1
    if area_w == "A":
        risk_b += 1
    elif area_w == "B":
        risk_a += 1
    if risk_a < risk_b:
        lowest_risk_side = "A"
    elif risk_b < risk_a:
        lowest_risk_side = "B"

    watch_out: list[str] = []
    for m in missing[:4]:
        watch_out.append(f"Missing detail: {m}")
    if price_w == "unknown":
        watch_out.append("Rent comparison is still unclear.")
    if bills_w == "unknown":
        watch_out.append("Bills setup is still unclear for one or both options.")

    best_option = (
        f"{_label_for_side(comp, best_side)} is the most recommended on current details."
        if best_side in ("A", "B")
        else "Both options are close on current details."
    )
    if summary:
        best_option = f"{best_option} {summary}"

    cheapest_option = (
        f"{_label_for_side(comp, price_w)} looks cheapest from the shared rent figures."
        if price_w in ("A", "B")
        else "Cheapest option is unclear from current rent details."
    )
    lowest_risk_option = (
        f"{_label_for_side(comp, lowest_risk_side)} looks lower risk on bills/safety/location context."
        if lowest_risk_side in ("A", "B")
        else "Lowest risk option is still unclear from current details."
    )

    caution_side = "unknown"
    if lowest_risk_side == "A":
        caution_side = "B"
    elif lowest_risk_side == "B":
        caution_side = "A"
    if caution_side in ("A", "B"):
        watch_out.insert(0, f"{_label_for_side(comp, caution_side)} needs more caution before deciding.")
    if not watch_out:
        watch_out = ["No major warning found, but confirm bills and contract terms in writing."]

    final_advice = (
        f"Prioritise {_label_for_side(comp, best_side)} first, then verify bills, contract wording, and commute fit."
        if best_side in ("A", "B")
        else "Both options need a bit more detail before a clear priority call."
    )
    return {
        "best_option": best_option,
        "cheapest_option": cheapest_option,
        "lowest_risk_option": lowest_risk_option,
        "watch_out": watch_out[:6],
        "final_advice": final_advice,
    }


def _build_comparison_sections(r: dict[str, Any]) -> dict[str, Any]:
    comp = r.get("comparison_result") or {}
    ar = r.get("analysis_route") or {}
    summary = _clean_str(comp.get("comparison_summary")) or _first_sentence(
        r.get("response_text") or ""
    )
    if not summary:
        summary = "A side-by-side comparison was prepared from what you shared."
    advisor = _build_comparison_advisor_fields(comp)

    found = [
        _route_brief(ar),
        _first_sentence(_clean_str(r.get("response_text")), 280),
    ]
    found = [x for x in found if x][:3]

    key_pts = _comparison_point_lines(comp)
    miss = comp.get("missing_information") or []
    if isinstance(miss, list):
        for m in miss[:4]:
            t = _clean_str(m)
            if t:
                key_pts.append(f"Still light on: {t}")

    next_steps: list[str] = []
    nh = _clean_str(comp.get("next_step_hint"))
    if nh:
        next_steps.append(nh)
    na = _clean_str(r.get("next_analysis_action"))
    if na:
        next_steps.append(na)
    sf = _clean_str(r.get("suggested_followup"))
    if sf and sf not in next_steps:
        next_steps.append(sf)

    follow = [_clean_str(x) for x in (r.get("followup_suggestions") or []) if _clean_str(x)]

    return {
        "layout": "property_comparison_advisor",
        "summary": summary,
        "best_option": advisor.get("best_option") or "",
        "cheapest_option": advisor.get("cheapest_option") or "",
        "lowest_risk_option": advisor.get("lowest_risk_option") or "",
        "watch_out": list(advisor.get("watch_out") or []),
        "final_advice": advisor.get("final_advice") or "",
        "what_i_found": found,
        "key_points": key_pts[:10],
        "next_steps": next_steps[:8],
        "followups": follow[:10],
        "alternative_help": [],
    }


def _build_analysis_candidate_sections(r: dict[str, Any]) -> dict[str, Any]:
    ar = r.get("analysis_route") or {}
    entry = r.get("analysis_entry_result") or {}
    pref = r.get("property_reference") or {}
    pip = r.get("property_input_parsed") or {}
    uk = r.get("uk_location_context") or {}

    rb = _clean_str(entry.get("route_based_response_text"))
    summary = _first_sentence(rb) if rb else _first_sentence(r.get("response_text") or "")
    if not summary:
        summary = "Your message was read as property or area context for a future deeper review."

    found = [_route_brief(ar)]
    na = _clean_str(entry.get("next_analysis_action"))
    if na:
        found.append(na)
    found = [x for x in found if x][:4]

    key_pts: list[str] = []
    key_pts.extend(_uk_bullets(uk))
    key_pts.extend(_property_ref_bullets(pref, pip))
    us = _clean_str(r.get("user_signals_summary"))
    if us:
        key_pts.append(f"Preferences: {us}")
    if not key_pts:
        key_pts.append("No major extra details were identified yet.")

    next_steps: list[str] = []
    if na:
        next_steps.append(na)
    miss = ar.get("missing_inputs") or []
    if isinstance(miss, list):
        for m in miss[:4]:
            t = _clean_str(m)
            if t:
                next_steps.append(t)
    if not next_steps:
        next_steps.append("You can provide more property details for a deeper review when modules are connected.")

    follow = [_clean_str(x) for x in (r.get("followup_suggestions") or []) if _clean_str(x)]

    return {
        "summary": summary,
        "what_i_found": found,
        "key_points": key_pts[:10],
        "next_steps": next_steps[:8],
        "followups": follow[:10],
        "alternative_help": [],
    }


def _build_out_of_scope_sections(r: dict[str, Any]) -> dict[str, Any]:
    sm = _clean_str(r.get("scope_message")) or _clean_str(r.get("response_text"))
    summary = _first_sentence(sm) if sm else "This question is outside what RentalAI covers in this version."

    alt = [
        "RentalAI focuses on renting in the UK: tenancy agreements, deposits, notices, bills, and property comparisons.",
        "Try asking about a contract clause, deposit protection, or comparing two rental options in plain English.",
    ]

    return {
        "summary": summary,
        "what_i_found": [],
        "key_points": [],
        "next_steps": [],
        "followups": [],
        "alternative_help": alt,
    }


def _build_fallback_sections(r: dict[str, Any]) -> dict[str, Any]:
    summary = _clean_str(r.get("response_text")) or "I need a bit more detail to help."
    miss = _clean_list(r.get("missing_key_fields") or [], limit=5)
    next_steps = []
    if miss:
        next_steps.append(f"Share: {', '.join(miss)}.")
    next_steps.append("Add one rental scenario and I will answer directly.")
    return {
        "summary": _first_sentence(summary, 420),
        "what_i_found": [],
        "key_points": [],
        "next_steps": next_steps[:3],
        "followups": [],
        "alternative_help": [],
    }


def _build_default_sections(r: dict[str, Any]) -> dict[str, Any]:
    ar = r.get("analysis_route") or {}
    intent = _clean_str(r.get("intent")) or "general"
    us = _clean_str(r.get("user_signals_summary"))
    summary = us or _first_sentence(r.get("response_text") or "")
    if not summary:
        summary = "Here is a concise read on your message."

    found = [
        f"Intent: {intent}.",
        _route_brief(ar) if ar.get("route_reason") else "",
    ]
    found = [x for x in found if x][:3]

    key_pts: list[str] = []
    po = r.get("priority_order") or []
    if isinstance(po, list) and po:
        key_pts.append(f"Signals: {', '.join(str(p) for p in po[:5])}")
    key_pts.extend(_uk_bullets(r.get("uk_location_context") or {}))
    if not key_pts:
        key_pts.append("No major extra details were identified yet.")

    next_steps: list[str] = []
    na = _clean_str(r.get("next_analysis_action"))
    if na:
        next_steps.append(na)
    nsp = _clean_str(r.get("next_step_prompt"))
    if nsp:
        next_steps.append(nsp)
    if not next_steps:
        next_steps.append("Share a postcode, link, or short listing line if you want a sharper next step.")

    follow = [_clean_str(x) for x in (r.get("followup_suggestions") or []) if _clean_str(x)]

    return {
        "summary": summary,
        "what_i_found": found,
        "key_points": key_pts[:10],
        "next_steps": next_steps[:8],
        "followups": follow[:10],
        "alternative_help": [],
    }


def _pick_branch(r: dict[str, Any]) -> str:
    if r.get("scope") == "out_of_scope":
        return "out_of_scope"
    intent = r.get("intent") or ""
    if intent in ("half_related", "insufficient_info", "invalid_input"):
        return "fallback"
    if intent == "legal_risk":
        return "legal_risk"
    if intent == "property_comparison":
        return "property_comparison"
    rt = (r.get("analysis_route") or {}).get("route_type") or ""
    if rt in ("area_analysis_candidate", "property_analysis_candidate"):
        return "analysis_candidate"
    return "default"


def build_display_sections(chat_result: dict[str, Any]) -> dict[str, Any]:
    """
    Map router payload fields into a stable section dict (lists for bullets; summary string).
    Empty lists mean “skip rendering that block” in the formatted text.
    """
    branch = _pick_branch(chat_result)
    decision_lines = _build_decision_lines(chat_result)

    if branch == "out_of_scope":
        out = _build_out_of_scope_sections(chat_result)
        out["decision"] = decision_lines
        out.update(_build_final_summary_fields(chat_result, out))
        return out

    if branch == "legal_risk":
        out = _build_legal_sections(chat_result)
        out["decision"] = decision_lines
        out.update(_build_final_summary_fields(chat_result, out))
        return out

    if branch == "fallback":
        out = _build_fallback_sections(chat_result)
        out["decision"] = decision_lines
        out.update(_build_final_summary_fields(chat_result, out))
        return out

    if branch == "property_comparison":
        out = _build_comparison_sections(chat_result)
        out["decision"] = decision_lines
        out.update(_build_final_summary_fields(chat_result, out))
        return out

    if branch == "analysis_candidate":
        out = _build_analysis_candidate_sections(chat_result)
        out["decision"] = decision_lines
        out.update(_build_final_summary_fields(chat_result, out))
        return out

    out = _build_default_sections(chat_result)
    out["decision"] = decision_lines
    out.update(_build_final_summary_fields(chat_result, out))
    return out


def _format_explain_result_block_zh(er: Any) -> str:
    """Format ``modules.explain``-shaped explain_result for chat display (Chinese labels)."""
    if not isinstance(er, dict):
        return ""
    chunks: list[str] = []

    sm = er.get("summary")
    chunks.append("总结：\n" + (str(sm).strip() if sm is not None else ""))

    pros_lines: list[str] = ["优点："]
    pros = er.get("pros")
    if isinstance(pros, list):
        for item in pros:
            t = str(item).strip() if item is not None else ""
            if t:
                pros_lines.append(f"- {t}")
    chunks.append("\n".join(pros_lines))

    cons_lines: list[str] = ["需要注意："]
    cons = er.get("cons")
    if isinstance(cons, list):
        for item in cons:
            t = str(item).strip() if item is not None else ""
            if t:
                cons_lines.append(f"- {t}")
    chunks.append("\n".join(cons_lines))

    rec = er.get("recommendation")
    chunks.append("建议：\n" + (str(rec).strip() if rec is not None else ""))

    return "\n\n".join(chunks).strip()


def render_display_text(sections: dict[str, Any]) -> str:
    """Join sections with fixed advisor-style titles and natural fallbacks."""
    if _clean_str(sections.get("layout")) == "property_comparison_advisor":
        best = _clean_str(sections.get("best_option")) or "Best option is unclear from current details."
        cheap = _clean_str(sections.get("cheapest_option")) or "Cheapest option is unclear."
        low_risk = _clean_str(sections.get("lowest_risk_option")) or "Lowest risk option is unclear."
        watch = _clean_list(sections.get("watch_out") or [], limit=8)
        advice = _clean_str(sections.get("final_advice")) or "Share more detail before making a final pick."
        if not watch:
            watch = ["No major warning found yet, but confirm key costs and terms in writing."]
        rep_lines = _reputation_lines(sections.get("reputation_result"))
        loc_lines = _location_lines(sections.get("location_info"))
        parts = [
            f"{TITLE_BEST_OPTION}\n{best}",
            f"{TITLE_CHEAPEST_OPTION}\n{cheap}",
            f"{TITLE_LOWEST_RISK_OPTION}\n{low_risk}",
            f"{TITLE_WATCH_OUT}\n" + "\n".join(f"- {x}" for x in watch),
            f"{TITLE_FINAL_ADVICE}\n{advice}",
            (
                f"{TITLE_REPUTATION_CHECK}\n" + "\n".join(f"- {x}" for x in rep_lines)
                if rep_lines else ""
            ),
            (
                f"{TITLE_LOCATION_INSIGHT}\n" + "\n".join(f"- {x}" for x in loc_lines)
                if loc_lines else ""
            ),
            f"{TITLE_SUMMARY}\n{_clean_str(sections.get('summary'))}",
        ]
        return "\n\n".join(p for p in parts if p.strip()).strip()

    if _clean_str(sections.get("layout")) == "legal_contract_advisor":
        summary = _clean_str(sections.get("summary")) or "Overall risk needs further confirmation."
        risk_clauses = _clean_list(sections.get("risk_clauses") or [], limit=8)
        need_confirm = _clean_list(sections.get("need_to_confirm") or [], limit=8)
        ask_landlord = _clean_list(sections.get("questions_to_ask_landlord") or [], limit=8)
        next_steps = _clean_list(sections.get("next_steps") or [], limit=8)

        if not risk_clauses:
            risk_clauses = [NO_MAJOR_RISK_TEXT]
        if not need_confirm:
            need_confirm = [
                "Confirm rent, deposit, bills, repair responsibility, and break clause in writing."
            ]
        if not ask_landlord:
            ask_landlord = ["Can you confirm all key tenancy terms in writing before I sign?"]
        if not next_steps:
            next_steps = [
                "Collect written confirmations first, then review the final draft before signing."
            ]
        final_label = _clean_str(sections.get("final_recommendation")) or "Need More Information"
        why = _clean_list(sections.get("why") or [], limit=6)
        main_risks = _clean_list(sections.get("main_risks") or [], limit=8)
        what_to_do_next = _clean_list(sections.get("what_to_do_next") or [], limit=8)
        if not why:
            why = ["The recommendation is based on available contract wording only."]
        if not main_risks:
            main_risks = [NO_MAJOR_RISK_TEXT]
        if not what_to_do_next:
            what_to_do_next = next_steps
        rep_lines = _reputation_lines(sections.get("reputation_result"))
        loc_lines = _location_lines(sections.get("location_info"))

        parts = [
            f"{TITLE_FINAL_RECOMMENDATION}\n{final_label}",
            f"{TITLE_WHY}\n" + "\n".join(f"- {x}" for x in why),
            f"{TITLE_MAIN_RISKS}\n" + "\n".join(f"- {x}" for x in main_risks),
            f"{TITLE_WHAT_TO_DO_NEXT}\n" + "\n".join(f"- {x}" for x in what_to_do_next),
            (
                f"{TITLE_REPUTATION_CHECK}\n" + "\n".join(f"- {x}" for x in rep_lines)
                if rep_lines else ""
            ),
            (
                f"{TITLE_LOCATION_INSIGHT}\n" + "\n".join(f"- {x}" for x in loc_lines)
                if loc_lines else ""
            ),
            f"{TITLE_SUMMARY}\n{summary}",
            f"{TITLE_RISK_CLAUSES}\n" + "\n".join(f"- {x}" for x in risk_clauses),
            f"{TITLE_NEED_CONFIRM}\n" + "\n".join(f"- {x}" for x in need_confirm),
            f"{TITLE_ASK_LANDLORD}\n" + "\n".join(f"- {x}" for x in ask_landlord),
            f"{TITLE_NEXT}\n" + "\n".join(f"{i}. {x}" for i, x in enumerate(next_steps, 1)),
        ]
        return "\n\n".join(p for p in parts if p.strip()).strip()

    parts: list[str] = []
    final_label = _clean_str(sections.get("final_recommendation")) or "Need More Information"
    why = _clean_list(sections.get("why") or [], limit=6)
    main_risks = _clean_list(sections.get("main_risks") or [], limit=8)
    what_to_do_next = _clean_list(sections.get("what_to_do_next") or [], limit=8)
    if not why:
        why = ["I need a bit more detail to give a stronger recommendation."]
    if not main_risks:
        main_risks = ["No major risk identified yet from the available details."]
    if not what_to_do_next:
        what_to_do_next = ["Share rent, postcode, bills, or contract wording."]
    rep_lines = _reputation_lines(sections.get("reputation_result"))
    loc_lines = _location_lines(sections.get("location_info"))

    parts.append(f"{TITLE_FINAL_RECOMMENDATION}\n{final_label}")
    parts.append(f"{TITLE_WHY}\n" + "\n".join(f"- {x}" for x in why))
    parts.append(f"{TITLE_MAIN_RISKS}\n" + "\n".join(f"- {x}" for x in main_risks))
    parts.append(f"{TITLE_WHAT_TO_DO_NEXT}\n" + "\n".join(f"- {x}" for x in what_to_do_next))
    if rep_lines:
        parts.append(f"{TITLE_REPUTATION_CHECK}\n" + "\n".join(f"- {x}" for x in rep_lines))
    if loc_lines:
        parts.append(f"{TITLE_LOCATION_INSIGHT}\n" + "\n".join(f"- {x}" for x in loc_lines))

    s = _clean_str(sections.get("summary"))
    decision_lines = _clean_list(sections.get("decision") or [], limit=3)
    if not s and decision_lines:
        s = decision_lines[0]
    if not s:
        s = "I do not have enough detail yet."
    parts.append(f"{TITLE_SUMMARY}\n{s}")

    found = _clean_list(sections.get("what_i_found") or [], limit=8)
    if not found and decision_lines:
        found = decision_lines
    if not found:
        found = ["I do not have enough detail yet."]
    parts.append(f"{TITLE_FOUND}\n" + "\n".join(f"- {x}" for x in found))

    keys = _clean_list(sections.get("key_points") or [], limit=10)
    if not keys:
        alt = _clean_list(sections.get("alternative_help") or [], limit=4)
        if alt:
            keys = alt
    if not keys:
        keys = [
            "You can share the rent, postcode, bills, or contract wording for a stronger answer."
        ]
    parts.append(f"{TITLE_KEY}\n" + "\n".join(f"- {x}" for x in keys))

    nxt = _clean_list(sections.get("next_steps") or [], limit=8)
    if not nxt:
        nxt = [
            "Share the rent, postcode, bills, or contract wording and I will give you a clearer recommendation."
        ]
    parts.append(f"{TITLE_NEXT}\n" + "\n".join(f"{i}. {x}" for i, x in enumerate(nxt, 1)))

    fol = _clean_list(sections.get("followups") or [], limit=10)
    if not fol:
        fol = [
            "Should I compare two rental options for you?",
            "Do you want me to check a contract clause?",
            "Do you want a quick risk check for your current plan?",
        ]
    parts.append(f"{TITLE_FOLLOW}\n" + "\n".join(f"- {x}" for x in fol))

    return "\n\n".join(parts).strip()

def _build_decision_lines(chat_result: dict[str, Any]) -> list[str]:
    decision = chat_result.get("decision") or {}
    if not isinstance(decision, dict) or not decision:
        return []

    lines: list[str] = []

    status = _clean_str(decision.get("decision_status"))
    title = _clean_str(decision.get("decision_title"))
    summary = _clean_str(decision.get("decision_summary"))
    action = _clean_str(decision.get("decision_action"))

    if title:
        if status:
            lines.append(f"{title} ({status})")
        else:
            lines.append(title)
    elif status:
        lines.append(status)

    if summary:
        lines.append(summary)

    if action:
        lines.append(f"Next: {action}")

    return lines[:3]

def build_chat_display_bundle(chat_result: dict[str, Any]) -> dict[str, Any]:
    """
    Build structured sections and a single display string for CLI / API consumers.
    Does not replace ``response_text``; add alongside it.
    """
    sections = build_display_sections(chat_result)
    sections["reputation_result"] = chat_result.get("reputation_result")
    sections["location_info"] = chat_result.get("location_info")
    display_text = render_display_text(sections)
    final_result = {
        "explain_result": chat_result.get("explain_result"),
        "summary": chat_result.get("summary") or chat_result.get("response_text") or chat_result.get("display_text"),
        "recommendation": ((chat_result.get("decision") or {}).get("decision_action") if isinstance(chat_result.get("decision"), dict) else None),
        "risks": ((chat_result.get("risk_result") or {}).get("risk_markers") if isinstance(chat_result.get("risk_result"), dict) else []),
        "reasons": ((chat_result.get("explanation_summary") or {}).get("key_positives") if isinstance(chat_result.get("explanation_summary"), dict) else []),
        "next_actions": list(sections.get("next_steps") or []),
    }
    final_result["followup_questions"] = build_followup_questions(final_result)
    final_result["missing_info_items"] = build_missing_info_items(final_result)
    final_result["decision_result"] = build_decision_result(final_result)
    # Keep final response generation for compatibility, but keep display_text
    # in the unified advisor-style structure from render_display_text.
    build_final_response_text(final_result)

    decision = chat_result.get("decision") or {}
    display_order = [
        "final_recommendation",
        "why",
        "main_risks",
        "what_to_do_next",
        "summary",
        "decision",
        "what_i_found",
        "key_points",
        "next_steps",
        "alternative_help",
        "followups",
    ]

    return {
        "display_text": display_text,
        "display_order": display_order,
        "display_sections": {
            "layout": sections.get("layout") or "",
            "best_option": sections.get("best_option") or "",
            "cheapest_option": sections.get("cheapest_option") or "",
            "lowest_risk_option": sections.get("lowest_risk_option") or "",
            "watch_out": list(sections.get("watch_out") or []),
            "final_advice": sections.get("final_advice") or "",
            "final_recommendation": sections.get("final_recommendation") or "",
            "why": list(sections.get("why") or []),
            "main_risks": list(sections.get("main_risks") or []),
            "what_to_do_next": list(sections.get("what_to_do_next") or []),
            "reputation_result": sections.get("reputation_result"),
            "location_info": sections.get("location_info"),
            "summary": sections.get("summary") or "",
            "risk_clauses": list(sections.get("risk_clauses") or []),
            "need_to_confirm": list(sections.get("need_to_confirm") or []),
            "questions_to_ask_landlord": list(sections.get("questions_to_ask_landlord") or []),
            "decision": list(sections.get("decision") or []),
            "what_i_found": list(sections.get("what_i_found") or []),
            "key_points": list(sections.get("key_points") or []),
            "next_steps": list(sections.get("next_steps") or []),
            "followups": list(sections.get("followups") or []),
            "alternative_help": list(sections.get("alternative_help") or []),
        },
        "display_meta": {
            "has_decision": bool(decision),
            "decision_status": _clean_str(decision.get("decision_status")),
            "decision_title": _clean_str(decision.get("decision_title")),
        },
    }