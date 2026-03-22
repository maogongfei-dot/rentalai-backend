# P10 Phase2: minimal helpers for favorites + compare from batch result rows.
from __future__ import annotations

from typing import Any


def batch_row_to_favorite_payload(row: dict[str, Any]) -> dict[str, Any]:
    """Build POST /favorites JSON from an analyze-batch result row."""
    row = row if isinstance(row, dict) else {}
    im = row.get("input_meta") if isinstance(row.get("input_meta"), dict) else {}
    url = im.get("source_url") or row.get("listing_url") or row.get("url")
    url = str(url).strip() if url else None
    idx = row.get("index")
    pid = im.get("property_id") or im.get("listing_id")
    if pid is not None:
        pid = str(pid).strip() or None
    if not url and not pid:
        pid = "batch_row_%s" % idx if idx is not None else None
    title = im.get("title") or row.get("title")
    if not title:
        title = "Listing %s" % idx if idx is not None else "Listing"
    rent = im.get("rent")
    if rent is None:
        rent = row.get("rent_pcm") or row.get("rent")
    try:
        price = float(rent) if rent is not None else None
    except (TypeError, ValueError):
        price = None
    pc = im.get("postcode") or row.get("postcode")
    pc = str(pc).strip() if pc else None
    out: dict[str, Any] = {
        "listing_url": url,
        "property_id": pid,
        "title": str(title)[:500],
        "price": price,
        "postcode": pc,
    }
    return out


def batch_row_compare_label(row: dict[str, Any]) -> str:
    """Short label for selectbox / multiselect."""
    row = row if isinstance(row, dict) else {}
    im = row.get("input_meta") if isinstance(row.get("input_meta"), dict) else {}
    idx = row.get("index")
    sc = row.get("score")
    pc = im.get("postcode") or row.get("postcode") or "—"
    return "Listing %s | score=%s | %s" % (idx, sc if sc is not None else "—", pc)
