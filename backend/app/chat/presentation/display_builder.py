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


def _build_legal_sections(r: dict[str, Any]) -> dict[str, Any]:
    p0 = r.get("source_result") or {}
    norm = p0.get("normalized_result") or {}
    summary_line = _clean_str(norm.get("summary"))
    badge = _clean_str(norm.get("risk_badge")) or _clean_str(p0.get("risk_badge"))
    if summary_line and badge:
        summary = f"{badge} — {summary_line}"
    elif summary_line:
        summary = summary_line
    elif badge:
        summary = f"{badge} Deposit and tenancy rules were checked against the built-in rule set."
    else:
        summary = _first_sentence(r.get("response_text") or "") or (
            "Your clause was screened for common rental risk patterns."
        )

    found: list[str] = []
    for line in norm.get("key_reasons") or []:
        t = _clean_str(line)
        if t and t not in found:
            found.append(t)
    if not found:
        found = _split_bullets(p0.get("display_text") or "")[:4]
    if not found:
        found = [_first_sentence(r.get("response_text") or "", 400) or "See Summary for the headline view."]

    key_pts: list[str] = []
    for line in (norm.get("legal_basis") or [])[:5]:
        t = _clean_str(line)
        if t:
            key_pts.append(t)
    if len(key_pts) < 2:
        for line in (norm.get("recommended_actions") or [])[:3]:
            t = _clean_str(line)
            if t and t not in key_pts:
                key_pts.append(t)

    next_steps: list[str] = []
    for line in (norm.get("recommended_actions") or []):
        t = _clean_str(line)
        if t and t not in next_steps:
            next_steps.append(t)
    sf = _clean_str(p0.get("suggested_followup") or r.get("suggested_followup"))
    if sf and sf not in next_steps:
        next_steps.append(sf)
    nsp = _clean_str(r.get("next_step_prompt"))
    if nsp and nsp not in next_steps and len(next_steps) < 6:
        next_steps.append(nsp)

    follow = [_clean_str(x) for x in (r.get("followup_suggestions") or []) if _clean_str(x)]

    return {
        "summary": summary,
        "what_i_found": found[:5],
        "key_points": key_pts[:6] if key_pts else [],
        "next_steps": next_steps[:8],
        "followups": follow[:10],
        "alternative_help": [],
    }


def _build_comparison_sections(r: dict[str, Any]) -> dict[str, Any]:
    comp = r.get("comparison_result") or {}
    ar = r.get("analysis_route") or {}
    summary = _clean_str(comp.get("comparison_summary")) or _first_sentence(
        r.get("response_text") or ""
    )
    if not summary:
        summary = "A side-by-side comparison was prepared from what you shared."

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
        "summary": summary,
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
    if intent in ("half_related", "insufficient_info"):
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
        return out

    if branch == "legal_risk":
        out = _build_legal_sections(chat_result)
        out["decision"] = decision_lines
        return out

    if branch == "fallback":
        out = _build_fallback_sections(chat_result)
        out["decision"] = decision_lines
        return out

    if branch == "property_comparison":
        out = _build_comparison_sections(chat_result)
        out["decision"] = decision_lines
        return out

    if branch == "analysis_candidate":
        out = _build_analysis_candidate_sections(chat_result)
        out["decision"] = decision_lines
        return out

    out = _build_default_sections(chat_result)
    out["decision"] = decision_lines
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
    parts: list[str] = []

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
            "summary": sections.get("summary") or "",
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