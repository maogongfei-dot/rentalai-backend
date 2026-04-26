"""
Lightweight map utility for address/postcode location insight (mocked data only).
"""

from __future__ import annotations

import re
from typing import Any

from .mock_data import MOCK_LOCATION_RECORDS

_UK_POSTCODE_RE = re.compile(r"\b([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})\b", re.I)


def _normalize(text: str) -> str:
    return " ".join((text or "").lower().split())


def _empty_unknown() -> dict[str, Any]:
    return {
        "normalized_address": "Unknown",
        "postcode": "Unknown",
        "city": "Unknown",
        "nearby_points": [],
        "transport_hint": "Unknown",
        "status": "unknown",
    }


def _extract_postcode(text: str) -> str | None:
    m = _UK_POSTCODE_RE.search(text or "")
    if not m:
        return None
    return m.group(1).upper().replace("  ", " ").strip()


def get_location_info(address_or_postcode: str) -> dict[str, Any]:
    """
    Resolve a mocked location profile from address/postcode text.

    If no entry is matched, returns Unknown values and no fabricated nearby points.
    """
    query_raw = (address_or_postcode or "").strip()
    if not query_raw:
        return _empty_unknown()

    query = _normalize(query_raw)
    query_pc = _extract_postcode(query_raw)
    best: dict[str, Any] | None = None
    best_score = 0
    for item in MOCK_LOCATION_RECORDS:
        addr = _normalize(str(item.get("normalized_address") or ""))
        pc = _normalize(str(item.get("postcode") or ""))
        city = _normalize(str(item.get("city") or ""))
        score = 0
        if query_pc and query_pc.lower() == pc:
            score += 5
        if query == addr:
            score += 4
        if query in addr:
            score += 3
        if query in city and query:
            score += 1
        if score > best_score:
            best = item
            best_score = score

    if not best:
        return _empty_unknown()

    return {
        "normalized_address": str(best.get("normalized_address") or "Unknown"),
        "postcode": str(best.get("postcode") or "Unknown"),
        "city": str(best.get("city") or "Unknown"),
        "nearby_points": list(best.get("nearby_points") or []),
        "transport_hint": str(best.get("transport_hint") or "Unknown"),
        "status": "ok",
    }

