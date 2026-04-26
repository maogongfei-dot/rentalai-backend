"""
Rule-based detection of property-related input: URLs, UK postcodes, addresses, listing keywords.
No scraping; output is for router, comparison, and future modules.
"""

from __future__ import annotations

import re
from typing import Any

from ..location.uk_cities import KNOWN_UK_CITIES

_URL_RE = re.compile(r"https?://[^\s<>\]\"']+", re.I)
_UK_POSTCODE_RE = re.compile(
    r"\b([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})\b",
    re.I,
)

# Street-style line: number + name + street-type word
_ADDRESS_LINE_RE = re.compile(
    r"\b(\d+\w?)\s+([\w'\-]+(?:\s+[\w'\-]+){0,4})\s+"
    r"(street|road|avenue|lane|close|drive|way|place|crescent|gardens|terrace|mews|square|row)\b",
    re.I,
)

_PROPERTY_KEYWORDS = (
    "rent",
    "rental",
    "pcm",
    "per month",
    "flat",
    "house",
    "studio",
    "apartment",
    "bedroom",
    "bed ",
    " beds",
    "bills included",
    "furnished",
    "unfurnished",
    "near station",
    "city centre",
    "town centre",
)

_BED_RE = re.compile(
    r"\b(\d)\s*(?:bed|beds|bedroom|bedrooms)\b",
    re.I,
)

_PRICE_RE = re.compile(
    r"£\s*(\d{3,5})|(\d{3,5})\s*(?:pcm|per month|/month|a month)\b",
    re.I,
)


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _empty_parse(raw: str) -> dict[str, Any]:
    return {
        "input_type": "unknown",
        "raw_text": raw,
        "detected_links": [],
        "detected_postcodes": [],
        "detected_addresses": [],
        "detected_locations": [],
        "detected_price": None,
        "bills_included": None,
        "furnished": None,
        "bedrooms": None,
        "property_signals": [],
        "is_property_reference": False,
    }


def _extract_urls(text: str) -> list[str]:
    found = _URL_RE.findall(text)
    return list(dict.fromkeys(found))


def _extract_postcodes(text: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for m in _UK_POSTCODE_RE.finditer(text):
        p = m.group(1).upper().replace("  ", " ").strip()
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def _extract_addresses(text: str) -> list[str]:
    out: list[str] = []
    for m in _ADDRESS_LINE_RE.finditer(text):
        frag = m.group(0).strip()
        if frag and frag not in out:
            out.append(frag)
    return out


def _extract_locations(low: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for loc in KNOWN_UK_CITIES:
        if loc in low:
            title = loc.title() if " " not in loc else " ".join(w.title() for w in loc.split())
            if title not in seen:
                seen.add(title)
                found.append(title)
    return found


def _bills_included(low: str) -> bool | None:
    if "bills included" in low or "include bills" in low or "all bills" in low:
        return True
    if "bills not" in low or "excluding bills" in low:
        return False
    return None


def _furnished(low: str) -> str | None:
    if "unfurnished" in low:
        return "unfurnished"
    if "part furnished" in low or "part-furnished" in low:
        return "part_furnished"
    if "furnished" in low:
        return "furnished"
    return None


def _bedrooms(low: str) -> int | None:
    m = _BED_RE.search(low)
    if m:
        return int(m.group(1))
    return None


def _extract_price(text: str) -> int | None:
    m = _PRICE_RE.search(text)
    if m:
        g = m.group(1) or m.group(2)
        if g:
            return int(g)
    m2 = re.search(r"\b(\d{3,5})\b", text)
    if m2:
        v = int(m2.group(1))
        if 300 <= v <= 20000:
            return v
    return None


def _property_signals(low: str) -> list[str]:
    sig: list[str] = []
    for kw in _PROPERTY_KEYWORDS:
        if kw.strip() in low:
            sig.append(kw.strip())
    # de-dupe preserve order
    return list(dict.fromkeys(sig))[:20]


def _link_platform(url: str) -> str | None:
    u = url.lower()
    if "rightmove.co.uk" in u and "/properties/" in u:
        return "rightmove"
    if "rightmove.co.uk" in u:
        return "rightmove"
    if "zoopla.co.uk" in u:
        return "zoopla"
    if "openrent.co.uk" in u:
        return "openrent"
    return None


def _classify_input_type(
    links: list[str],
    postcodes: list[str],
    addresses: list[str],
    locations: list[str],
    signals: list[str],
    low: str,
) -> str:
    """Pick a single primary input_type; mixed when several signal families overlap."""
    has_link = bool(links)
    has_pc = bool(postcodes)
    has_addr = bool(addresses)
    has_loc = bool(locations)
    has_prop_words = bool(signals)

    compare_words = any(
        x in low
        for x in (
            "compare",
            "versus",
            " vs ",
            " vs. ",
            "better than",
            "which is better",
        )
    )

    if has_link:
        if len(links) > 1:
            return "mixed"
        if has_pc or has_addr or compare_words:
            return "mixed"
        if has_pc and has_prop_words:
            return "mixed"
        u = links[0]
        plat = _link_platform(u)
        if plat == "rightmove":
            return "rightmove_link"
        if plat == "zoopla":
            return "zoopla_link"
        if plat == "openrent":
            return "openrent_link"
        return "mixed"

    if has_pc and (has_prop_words or has_addr or compare_words):
        return "mixed"
    if has_pc:
        return "postcode"
    if has_addr:
        return "address"
    if has_loc and not has_prop_words:
        return "location_text"
    if has_prop_words or has_loc:
        return "property_description"

    return "unknown"


def parse_property_input(user_text: str) -> dict[str, Any]:
    """
    Detect input shape: portal links, postcodes, address-like lines, listing keywords.

    Safe for empty input.
    """
    if not (user_text or "").strip():
        return _empty_parse("")

    raw = user_text.strip()
    low = _normalize(raw)

    links = _extract_urls(raw)
    postcodes = _extract_postcodes(raw)
    addresses = _extract_addresses(raw)
    locations = _extract_locations(low)
    price = _extract_price(raw)
    bills = _bills_included(low)
    furnished = _furnished(low)
    beds = _bedrooms(low)
    signals = _property_signals(low)

    input_type = _classify_input_type(
        links, postcodes, addresses, locations, signals, low
    )

    is_ref = bool(
        links
        or postcodes
        or addresses
        or (locations and any(k in low for k in ("rent", "flat", "house", "studio", "£")))
        or (signals and len(signals) >= 1)
    )
    if input_type in ("rightmove_link", "zoopla_link", "openrent_link", "postcode", "address", "mixed"):
        is_ref = True

    return {
        "input_type": input_type,
        "raw_text": raw,
        "detected_links": links,
        "detected_postcodes": postcodes,
        "detected_addresses": addresses,
        "detected_locations": locations,
        "detected_price": price,
        "bills_included": bills,
        "furnished": furnished,
        "bedrooms": beds,
        "property_signals": signals,
        "is_property_reference": is_ref,
    }


def assess_input_completeness(parsed: dict[str, Any], user_text: str) -> dict[str, Any]:
    """
    Lightweight completeness check for rental guidance gating.

    Key slots:
      - rent
      - location (city/address)
      - postcode
      - bills
      - contract
    """
    text = (user_text or "").strip()
    low = _normalize(text)
    has_rent = parsed.get("detected_price") is not None
    has_location = bool(parsed.get("detected_locations") or parsed.get("detected_addresses"))
    has_postcode = bool(parsed.get("detected_postcodes"))
    has_bills = parsed.get("bills_included") is not None or any(
        k in low for k in ("bills", "utility", "utilities", "council tax")
    )
    has_contract = any(
        k in low
        for k in (
            "contract",
            "tenancy agreement",
            "clause",
            "agreement",
            "section 21",
            "section 8",
            "landlord",
            "tenant",
            "deposit",
            "repairs",
            "eviction",
            "notice",
        )
    )
    fields = {
        "rent": has_rent,
        "location": has_location,
        "postcode": has_postcode,
        "bills": has_bills,
        "contract": has_contract,
    }
    missing = [k for k, v in fields.items() if not v]
    return {
        "fields_present": fields,
        "missing_fields": missing,
        "present_count": sum(1 for v in fields.values() if v),
    }


def build_property_reference(parsed: dict[str, Any]) -> dict[str, Any]:
    """
    Normalised listing reference for scrapers, comparison, and area modules.

    Fields may be null; ``raw_text`` always mirrors the user message when present.
    """
    it = parsed.get("input_type") or "unknown"
    links: list[str] = list(parsed.get("detected_links") or [])
    url = links[0] if links else None
    platform = "none"
    if url:
        platform = _link_platform(url) or "none"

    source_type = "unknown"
    if it in ("rightmove_link", "zoopla_link", "openrent_link"):
        source_type = "link"
    elif it == "postcode":
        source_type = "postcode"
    elif it == "address":
        source_type = "address"
    elif it in ("location_text", "property_description"):
        source_type = "description"
    elif it == "mixed":
        source_type = "mixed"
    elif parsed.get("is_property_reference"):
        source_type = "description"

    pcs = list(parsed.get("detected_postcodes") or [])
    addrs = list(parsed.get("detected_addresses") or [])
    locs = list(parsed.get("detected_locations") or [])

    features = list(dict.fromkeys(list(parsed.get("property_signals") or [])))
    if parsed.get("bills_included") is True:
        if not any("bills" in f.lower() for f in features):
            features.append("bills_included")
    if parsed.get("furnished"):
        features.append(parsed["furnished"])
    features = list(dict.fromkeys(features))[:24]

    city = locs[0] if locs else None

    return {
        "source_type": source_type,
        "platform": platform,
        "url": url,
        "postcode": pcs[0] if pcs else None,
        "address_text": addrs[0] if addrs else None,
        "city": city,
        "price": parsed.get("detected_price"),
        "bills_included": parsed.get("bills_included"),
        "bedrooms": parsed.get("bedrooms"),
        "features": features,
        "raw_text": parsed.get("raw_text") or "",
    }


def property_input_voice_line(parsed: dict[str, Any]) -> str:
    """Single short product line; empty if no notable reference."""
    if not parsed.get("is_property_reference"):
        return ""
    it = parsed.get("input_type") or "unknown"
    link_blob = " ".join(parsed.get("detected_links") or []).lower()
    if "rightmove" in link_blob or it == "rightmove_link":
        return (
            "This looks like a Rightmove property link, which can be used for listing analysis later."
        )
    if "zoopla" in link_blob or it == "zoopla_link":
        return (
            "This looks like a Zoopla link, which can be used for listing analysis later."
        )
    if "openrent" in link_blob or it == "openrent_link":
        return (
            "This looks like an OpenRent link, which can be used for listing analysis later."
        )
    if parsed.get("detected_postcodes"):
        return (
            "I detected a property reference (postcode or area), so this can later be analysed "
            "as a listing or area check."
        )
    if parsed.get("detected_addresses"):
        return (
            "I detected what looks like a street address, which can later tie into listing or area checks."
        )
    if it in ("property_description", "location_text"):
        return (
            "I picked up some listing-style details, which can feed into comparison or analysis later."
        )
    return ""
