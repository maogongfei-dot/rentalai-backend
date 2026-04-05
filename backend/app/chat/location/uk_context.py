"""
UK location context builder: cities, postcodes, area phrases (no geocoding).
"""

from __future__ import annotations

import re
from typing import Any

from .uk_cities import ALL_UK_CITIES_LOWERCASE, PRIMARY_UK_CITIES_SLUG, slug_to_display_name

_UK_POSTCODE_RE = re.compile(
    r"\b([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})\b",
    re.I,
)

_AREA_PHRASES: tuple[str, ...] = (
    "city centre",
    "city center",
    "town centre",
    "town center",
    "nice area",
    "good area",
    "local area",
)


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _extract_postcodes(text: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for m in _UK_POSTCODE_RE.finditer(text):
        p = m.group(1).upper().replace("  ", " ").strip()
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def _find_cities_in_text(low: str) -> list[str]:
    """Longest slugs first to prefer 'milton keynes' over shorter tokens."""
    slugs = sorted(ALL_UK_CITIES_LOWERCASE, key=len, reverse=True)
    found: list[str] = []
    seen_lower: set[str] = set()
    for slug in slugs:
        if slug in low and slug not in seen_lower:
            disp = slug_to_display_name(slug)
            if disp.lower() not in seen_lower:
                seen_lower.add(slug)
                seen_lower.add(disp.lower())
                found.append(disp)
    return found


def _extract_area_phrases(low: str) -> str | None:
    hits = [p for p in _AREA_PHRASES if p in low]
    if not hits:
        return None
    return ", ".join(hits[:3])


def _merge_city_lists(*lists: list[str | None]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for lst in lists:
        if not lst:
            continue
        for x in lst:
            if not x:
                continue
            k = str(x).strip().title()
            if k and k not in seen:
                seen.add(k)
                out.append(k)
    return out


def _cities_from_comparison_sides(comp: dict[str, Any] | None) -> list[str]:
    """Cities from property_a / property_b (no is_comparison gate)."""
    if not comp:
        return []
    cities: list[str] = []
    for side in ("property_a", "property_b"):
        s = comp.get(side) or {}
        c = s.get("city")
        if c:
            cities.append(str(c).strip().title())
        lab = (s.get("address_or_label") or "").lower()
        for slug in sorted(PRIMARY_UK_CITIES_SLUG + ALL_UK_CITIES_LOWERCASE, key=len, reverse=True):
            if slug in lab:
                cities.append(slug_to_display_name(slug))
                break
    return list(dict.fromkeys(cities))


def _postcodes_from_comparison_sides(comp: dict[str, Any] | None) -> list[str]:
    if not comp:
        return []
    pcs: list[str] = []
    for side in ("property_a", "property_b"):
        s = comp.get(side) or {}
        p = s.get("postcode")
        if p:
            pcs.append(str(p).upper().replace("  ", " ").strip())
    return list(dict.fromkeys(pcs))


def _cities_from_comparison(comp: dict[str, Any] | None) -> list[str]:
    if not comp or not comp.get("is_comparison"):
        return []
    return _cities_from_comparison_sides(comp)


def _postcodes_from_comparison(comp: dict[str, Any] | None) -> list[str]:
    if not comp or not comp.get("is_comparison"):
        return []
    return _postcodes_from_comparison_sides(comp)


def build_uk_location_context(
    user_text: str,
    *,
    property_input_parsed: dict[str, Any] | None = None,
    property_reference: dict[str, Any] | None = None,
    comparison_inputs: dict[str, Any] | None = None,
    comparison_result: dict[str, Any] | None = None,
    detected_preferences: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Merge free text, property_input, property_reference, comparison sides, and preferences.

    Safe for empty input.
    """
    empty = {
        "country": "UK",
        "city": None,
        "postcode": None,
        "area_text": None,
        "location_type": "unknown",
        "detected_cities": [],
        "detected_postcodes": [],
        "location_confidence": 0.0,
        "is_supported_uk_context": False,
    }
    if not (user_text or "").strip():
        return empty

    raw = user_text.strip()
    low = _normalize(raw)

    pip = property_input_parsed or {}
    pref_ref = property_reference or {}
    prefs = detected_preferences or {}

    pcs_text = _extract_postcodes(raw)
    pcs_pip = list(pip.get("detected_postcodes") or [])
    pcs_ref = [pref_ref["postcode"]] if pref_ref.get("postcode") else []
    pcs_comp = list(
        dict.fromkeys(
            [
                *_postcodes_from_comparison(comparison_inputs),
                *_postcodes_from_comparison_sides(comparison_result),
            ]
        )
    )
    all_pcs = list(dict.fromkeys([*pcs_text, *pcs_pip, *pcs_ref, *pcs_comp]))

    cities_text = _find_cities_in_text(low)
    cities_pip = list(pip.get("detected_locations") or [])
    city_ref = [pref_ref["city"]] if pref_ref.get("city") else []
    cities_ment = list(prefs.get("mentioned_locations") or [])
    cities_comp = list(
        dict.fromkeys(
            [
                *_cities_from_comparison(comparison_inputs),
                *_cities_from_comparison_sides(comparison_result),
            ]
        )
    )
    all_cities = _merge_city_lists(
        cities_text,
        cities_pip,
        city_ref,
        cities_ment,
        cities_comp,
    )

    area_bits = _extract_area_phrases(low)

    # Primary single fields for router shortcuts
    city_primary = all_cities[0] if all_cities else None
    pc_primary = all_pcs[0] if all_pcs else None

    if city_primary and pc_primary:
        loc_type = "mixed"
        conf = 0.92
    elif city_primary:
        loc_type = "city"
        conf = 0.85
    elif pc_primary:
        loc_type = "postcode"
        conf = 0.82
    elif area_bits:
        loc_type = "unknown"
        conf = 0.45
    else:
        loc_type = "unknown"
        conf = 0.0

    supported = bool(all_cities or all_pcs or area_bits)

    return {
        "country": "UK",
        "city": city_primary,
        "postcode": pc_primary,
        "area_text": area_bits,
        "location_type": loc_type,
        "detected_cities": all_cities,
        "detected_postcodes": all_pcs,
        "location_confidence": round(min(0.95, conf), 2),
        "is_supported_uk_context": supported,
    }


def empty_uk_location_context() -> dict[str, Any]:
    return build_uk_location_context("")
