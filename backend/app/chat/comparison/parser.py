"""
Extract comparison entities from free text (rules only; no NLP models).
"""

from __future__ import annotations

import re
from typing import Any

from ..location.uk_cities import KNOWN_UK_CITIES

_UK_POSTCODE_RE = re.compile(
    r"\b([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})\b",
    re.I,
)

_COMPARISON_SIGNALS = (
    "compare",
    "comparison",
    "versus",
    " vs ",
    " vs. ",
    "better than",
    "which is better",
    "this one or that one",
    "current place",
    "current flat",
    "current house",
    "the one i live in now",
    "this property",
    "that property",
    "side by side",
    "which property",
    "which flat",
    "which house",
)

_PRICE_IN_SEGMENT = re.compile(
    r"£\s*(\d{3,5})|(\d{3,5})\s*(?:pcm|per month|/month|a month)\b",
    re.I,
)


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _empty_side() -> dict[str, Any]:
    return {
        "source": "user_input",
        "address_or_label": None,
        "postcode": None,
        "city": None,
        "mentioned_price": None,
        "bills_included": None,
        "features": [],
    }


def _extract_postcodes(text: str) -> list[str]:
    return [m.group(1).upper().replace("  ", " ").strip() for m in _UK_POSTCODE_RE.finditer(text)]


def _extract_price(fragment: str) -> int | None:
    m = _PRICE_IN_SEGMENT.search(fragment)
    if not m:
        m2 = re.search(r"\b(\d{3,5})\b", fragment)
        if m2:
            v = int(m2.group(1))
            if 300 <= v <= 20000:
                return v
        return None
    g = m.group(1) or m.group(2)
    return int(g) if g else None


def _extract_city(fragment: str) -> str | None:
    low = _normalize(fragment)
    for loc in KNOWN_UK_CITIES:
        if loc in low:
            return loc.title() if " " not in loc else " ".join(w.title() for w in loc.split())
    return None


def _extract_features(fragment: str) -> list[str]:
    low = _normalize(fragment)
    out: list[str] = []
    if any(x in low for x in ("near station", "close to station", "near the station", "near tube", "near train")):
        out.append("near station")
    if "near work" in low or "close to work" in low or "commute" in low:
        out.append("commute")
    if any(x in low for x in ("safe", "safer", "quiet area")):
        out.append("safe area")
    if any(x in low for x in ("good area", "nice neighbourhood", "nice neighborhood", "city centre", "city center")):
        out.append("area quality")
    if "bills included" in low or "include bills" in low or "all bills" in low:
        out.append("bills included")
    seen: set[str] = set()
    return [x for x in out if x not in seen and not seen.add(x)]


def _bills_included(fragment: str) -> bool | None:
    low = _normalize(fragment)
    if "bills included" in low or "include bills" in low or "all bills" in low:
        return True
    if "bills not" in low or "excluding bills" in low:
        return False
    return None


def _split_two_segments(user_text: str) -> tuple[str, str] | None:
    raw = user_text.strip()
    low = _normalize(raw)
    # 1) vs / versus
    for sep in (r"\s+versus\s+", r"\s+vs\.?\s+"):
        parts = re.split(sep, raw, maxsplit=1, flags=re.I)
        if len(parts) == 2 and parts[0].strip() and parts[1].strip():
            return parts[0].strip(), parts[1].strip()
    # 2) "... , with this property ..." (common in compare prompts)
    if re.search(r"\bcompare\b", low):
        m = re.search(r",\s*with\s+", raw, re.I)
        if m:
            left, right = raw[: m.start()].strip(), raw[m.end() :].strip()
            if left and right:
                return left, right
        m2 = re.search(
            r"\bcompare\s+(.+?)\s+with\s+(.+)$",
            raw,
            re.I | re.S,
        )
        if m2:
            a, b = m2.group(1).strip(), m2.group(2).strip()
            if a and b:
                return a, b
    # 3) which is better ... or ...
    m3 = re.search(r"which\s+is\s+better\s*,?\s*(.+)", raw, re.I)
    if m3:
        rest = m3.group(1).strip()
        if " or " in rest.lower():
            a, b = rest.split(" or ", 1)
            if a.strip() and b.strip():
                return a.strip(), b.strip().rstrip("?")
    return None


def _label_for_segment(fragment: str, index: int) -> str:
    low = _normalize(fragment)
    if "this one" in low:
        return "this one"
    if "current" in low:
        if "flat" in low:
            return "my current flat"
        if "house" in low:
            return "my current house"
        if "place" in low:
            return "my current place"
    if "this property" in low or "this listing" in low:
        return "this property"
    if "that property" in low:
        return "that property"
    pcs = _extract_postcodes(fragment)
    if pcs:
        return pcs[0]
    city = _extract_city(fragment)
    if city:
        return f"place in {city}"
    return f"Property {'A' if index == 0 else 'B'}"


def _fill_side(fragment: str, index: int) -> dict[str, Any]:
    side = _empty_side()
    side["address_or_label"] = _label_for_segment(fragment, index)
    side["city"] = _extract_city(fragment)
    pcs = _extract_postcodes(fragment)
    if pcs:
        side["postcode"] = pcs[0]
    side["mentioned_price"] = _extract_price(fragment)
    side["bills_included"] = _bills_included(fragment)
    side["features"] = _extract_features(fragment)
    return side


def coerce_comparison_inputs(user_text: str) -> dict[str, Any]:
    """When intent is property_comparison but the parser found no signal, still build two sides."""
    base = extract_property_comparison_inputs(user_text)
    if base["is_comparison"]:
        return base
    raw = (user_text or "").strip()
    if not raw:
        return base
    return {
        "is_comparison": True,
        "property_a": _fill_side(raw, 0),
        "property_b": {
            **_empty_side(),
            "address_or_label": "the other property",
        },
        "comparison_signals": ["intent-led comparison"],
    }


def extract_property_comparison_inputs(user_text: str) -> dict[str, Any]:
    """
    Parse whether the user is comparing two homes and best-effort split + attributes.

    Returns keys: is_comparison, property_a, property_b, comparison_signals.
    """
    if not (user_text or "").strip():
        return {
            "is_comparison": False,
            "property_a": _empty_side(),
            "property_b": _empty_side(),
            "comparison_signals": [],
        }

    raw = user_text.strip()
    low = _normalize(raw)

    signals: list[str] = []
    for p in _COMPARISON_SIGNALS:
        if p.strip() in low or p in low:
            signals.append(p.strip())

    postcodes_all = _extract_postcodes(raw)
    has_two_postcodes = len(postcodes_all) >= 2

    has_vs = bool(re.search(r"\bvs\b", low))
    has_compare_word = bool(re.search(r"\bcompare\b", low))
    has_comparison_intent = bool(signals) or has_two_postcodes or has_compare_word or has_vs

    if not has_comparison_intent:
        return {
            "is_comparison": False,
            "property_a": _empty_side(),
            "property_b": _empty_side(),
            "comparison_signals": [],
        }

    split = _split_two_segments(raw)
    if split:
        left, right = split
    elif has_two_postcodes:
        # split text around second postcode occurrence
        ms = list(_UK_POSTCODE_RE.finditer(raw))
        if len(ms) >= 2:
            cut = ms[1].start()
            left, right = raw[:cut].strip().rstrip(","), raw[cut:].strip()
        else:
            left, right = raw, ""
    else:
        # single blob: put everything in A, leave B as "the other option"
        left, right = raw, "the other property"

    prop_a = _fill_side(left, 0)
    prop_b = _fill_side(right, 1)

    if not signals:
        signals = ["two-sided comparison"]
    if has_vs and "vs" not in signals:
        signals.insert(0, "vs")

    return {
        "is_comparison": True,
        "property_a": prop_a,
        "property_b": prop_b,
        "comparison_signals": list(dict.fromkeys(signals))[:12],
    }
