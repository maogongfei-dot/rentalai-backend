"""Phase 5-C4: short-rent recommendations API.

Reads from the SQLite ``short_rent_listings`` table when available; otherwise
falls back to the existing JSON-backed pipeline so Phase 4 / 5-A behavior is
preserved when the database is empty.
"""

import json

from backend.db_services.short_rent_db_service import get_all_short_rents
from backend.services.unified_short_rent_service import (
    get_final_short_rent_recommendations,
)


def _parse_available_dates(raw) -> list:
    if raw is None or raw == "":
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            value = json.loads(raw)
        except (ValueError, TypeError):
            return []
        if isinstance(value, list):
            return value
        return []
    return []


def db_short_rent_to_dict(item) -> dict:
    """Convert a ``ShortRentDB`` ORM row into the dict shape consumed by the frontend."""
    return {
        "id": getattr(item, "id", ""),
        "source_type": "internal",
        "source": "RentalAI",
        "title": getattr(item, "title", ""),
        "location": getattr(item, "location", ""),
        "postcode": getattr(item, "postcode", ""),
        "price_per_day": getattr(item, "price_per_day", ""),
        "price_per_week": "",
        "available_from": "",
        "available_dates": _parse_available_dates(getattr(item, "available_dates", None)),
        "link": "",
        "description": getattr(item, "description", ""),
        "explanation": "",
    }


def get_short_rent_recommendations_api(filters: dict = None) -> dict:
    try:
        db_items = get_all_short_rents()
        if db_items:
            results = [db_short_rent_to_dict(row) for row in db_items]
        else:
            results = get_final_short_rent_recommendations(filters)
        return {
            "success": True,
            "data": results,
            "count": len(results),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": [],
            "count": 0,
        }
