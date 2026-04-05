"""
Build lightweight property snapshots and run a rule-based comparison (no scoring model).
"""

from __future__ import annotations

from typing import Any

_DIMS = ("price", "bills", "commute", "area", "safety")


def build_property_snapshot_from_side(side: dict[str, Any]) -> dict[str, Any]:
    """Map parser `property_a` / `property_b` into the unified snapshot shape."""
    feats = list(side.get("features") or [])
    commute_hint = ""
    area_hint = ""
    safety_hint = ""
    if any("station" in f or "commute" in f for f in feats):
        commute_hint = "near station / commute" if any("station" in f for f in feats) else "commute"
    if any("area" in f for f in feats):
        area_hint = "area quality"
    if any("safe" in f for f in feats):
        safety_hint = "safety"

    return {
        "label": side.get("address_or_label") or "Property",
        "source": side.get("source") or "user_input",
        "postcode": side.get("postcode"),
        "city": side.get("city"),
        "price": side.get("mentioned_price"),
        "bills_included": side.get("bills_included"),
        "commute_hint": commute_hint or None,
        "area_hint": area_hint or None,
        "safety_hint": safety_hint or None,
        "features": feats,
    }


def _winner_price(a: dict[str, Any], b: dict[str, Any]) -> tuple[str, str]:
    pa, pb = a.get("price"), b.get("price")
    if pa is not None and pb is not None:
        if pa < pb:
            return "A", f"Based on the figures given, A looks lower at £{pa} than B at £{pb}."
        if pb < pa:
            return "B", f"Based on the figures given, B looks lower at £{pb} than A at £{pa}."
        return "tie", "Both sides show the same rent figure."
    if pa is not None and pb is None:
        return "unknown", "Only one side has a rent figure so far."
    if pb is not None and pa is None:
        return "unknown", "Only one side has a rent figure so far."
    return "unknown", "No monthly rent figures were captured for both sides."


def _winner_bills(a: dict[str, Any], b: dict[str, Any]) -> tuple[str, str]:
    ba, bb = a.get("bills_included"), b.get("bills_included")
    if ba is True and bb is False:
        return "A", "Bills appear to be included for A but not for B."
    if bb is True and ba is False:
        return "B", "Bills appear to be included for B but not for A."
    if ba is True and bb is not True:
        return "A", "Bills appear to be included for A; confirming how B handles bills would help."
    if bb is True and ba is not True:
        return "B", "Bills appear to be included for B; confirming how A handles bills would help."
    if ba is True and bb is True:
        return "tie", "Both descriptions mention bills included."
    if ba is False and bb is False:
        return "tie", "Neither side clearly states bills included."
    return "unknown", "Bill arrangements are not clear for one or both sides."


def _winner_commute(a: dict[str, Any], b: dict[str, Any]) -> tuple[str, str]:
    def _has_commute(x: dict[str, Any]) -> bool:
        if x.get("commute_hint"):
            return True
        feats = x.get("features") or []
        return any("station" in f or "commute" in f for f in feats)

    ac = _has_commute(a)
    bc = _has_commute(b)
    if ac and not bc:
        return "A", "A has more commuting detail in what you shared."
    if bc and not ac:
        return "B", "B has more commuting detail in what you shared."
    if ac and bc:
        return "tie", "Both mention transport or commuting in some form."
    return "unknown", "Not enough commuting detail was provided for a side-by-side read."


def _winner_area(a: dict[str, Any], b: dict[str, Any]) -> tuple[str, str]:
    sa = (a.get("city") or "") + (a.get("postcode") or "") + (a.get("area_hint") or "")
    sb = (b.get("city") or "") + (b.get("postcode") or "") + (b.get("area_hint") or "")
    score_a = len(sa.strip()) + len(a.get("features") or [])
    score_b = len(sb.strip()) + len(b.get("features") or [])
    if score_a > score_b + 2:
        return "A", "A has a bit more location or area context in your message."
    if score_b > score_a + 2:
        return "B", "B has a bit more location or area context in your message."
    if a.get("postcode") and b.get("postcode") and a.get("postcode") != b.get("postcode"):
        return "tie", "Both sides have different postcodes; area trade-offs depend on your priorities."
    return "unknown", "Area and neighbourhood detail is still light on one or both sides."


def _winner_safety(a: dict[str, Any], b: dict[str, Any]) -> tuple[str, str]:
    af = any("safe" in f for f in (a.get("features") or []))
    bf = any("safe" in f for f in (b.get("features") or []))
    if af and not bf:
        return "A", "Only A mentions safety-related wording."
    if bf and not af:
        return "B", "Only B mentions safety-related wording."
    if af and bf:
        return "tie", "Both mention safety or a quiet area."
    return "unknown", "No clear safety or neighbourhood security hints for both sides yet."


def _collect_missing(a: dict[str, Any], b: dict[str, Any]) -> list[str]:
    miss: list[str] = []
    if a.get("price") is None:
        miss.append("Monthly rent for property A")
    if b.get("price") is None:
        miss.append("Monthly rent for property B")
    if not a.get("postcode") and not a.get("city"):
        miss.append("Postcode or city for property A")
    if not b.get("postcode") and not b.get("city"):
        miss.append("Postcode or city for property B")
    if a.get("bills_included") is None:
        miss.append("Whether bills are included for property A")
    if b.get("bills_included") is None:
        miss.append("Whether bills are included for property B")
    return list(dict.fromkeys(miss))[:8]


def _build_summary(
    points: list[dict[str, Any]],
    prefs: dict[str, Any] | None,
) -> str:
    prefs = prefs or {}
    order = list(prefs.get("priority_order") or [])
    lead: list[str] = []
    dim_map = {p["dimension"]: p for p in points}

    def add_dim(key: str, label: str) -> None:
        if key in dim_map and dim_map[key]["winner"] not in ("unknown", "tie"):
            w = dim_map[key]["winner"]
            if w in ("A", "B"):
                lead.append(f"{label}: side {w} looks stronger on what you shared so far")

    for pref in order:
        if pref == "price" and "price" in dim_map:
            add_dim("price", "Price")
        elif pref == "commute" and "commute" in dim_map:
            add_dim("commute", "Commuting")
        elif pref == "safety" and "safety" in dim_map:
            add_dim("safety", "Safety")
        elif pref == "bills" and "bills" in dim_map:
            add_dim("bills", "Bills")

    if not lead:
        for label, key in (
            ("Price", "price"),
            ("Bills", "bills"),
            ("Commute", "commute"),
            ("Area", "area"),
            ("Safety", "safety"),
        ):
            if key in dim_map and dim_map[key]["winner"] in ("A", "B"):
                lead.append(f"{label}: side {dim_map[key]['winner']} edges ahead on available detail")
                break

    if not lead:
        lead.append("The two sides look close on what you have shared so far")

    body = "; ".join(lead[:2]) + "."
    return f"Based on the information provided, {body}"


def run_basic_property_comparison(
    property_a: dict[str, Any],
    property_b: dict[str, Any],
    user_preferences: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Compare two snapshots on five dimensions; never raises on incomplete data.

    property_* should already be snapshot-shaped (see ``build_property_snapshot_from_side``).
    """
    a, b = property_a, property_b
    points: list[dict[str, Any]] = []

    w, note = _winner_price(a, b)
    points.append({"dimension": "price", "winner": w, "note": note})

    w, note = _winner_bills(a, b)
    points.append({"dimension": "bills", "winner": w, "note": note})

    w, note = _winner_commute(a, b)
    points.append({"dimension": "commute", "winner": w, "note": note})

    w, note = _winner_area(a, b)
    points.append({"dimension": "area", "winner": w, "note": note})

    w, note = _winner_safety(a, b)
    points.append({"dimension": "safety", "winner": w, "note": note})

    missing = _collect_missing(a, b)
    summary = _build_summary(points, user_preferences)

    next_hint = (
        "To make this more accurate, you can also share the postcode, rent, or bill details "
        "for the property that is still light on detail."
    )

    return {
        "comparison_ready": True,
        "property_a": a,
        "property_b": b,
        "comparison_summary": summary,
        "comparison_points": points,
        "missing_information": missing,
        "next_step_hint": next_hint,
    }


def build_comparison_response_text(comparison_result: dict[str, Any]) -> str:
    """Readable multi-paragraph reply (gentle tone; no failure wording)."""
    summary = comparison_result.get("comparison_summary") or ""
    parts = [
        "I can still make a partial comparison based on the details you provided.",
        summary,
    ]
    miss = comparison_result.get("missing_information") or []
    if miss:
        parts.append(
            "A few details would still help sharpen this: " + "; ".join(miss[:4]) + "."
        )
    parts.append(comparison_result.get("next_step_hint") or "")
    return "\n\n".join(p for p in parts if p.strip())
