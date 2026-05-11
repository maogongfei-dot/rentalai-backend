"""Phase 5-C4 / 5-D1 / 9-A4: short-rent recommendations + creation API.

* ``get_short_rent_recommendations_api`` reads from the ``short_rent_listings``
  table (PostgreSQL or SQLite per ``DATABASE_URL``) when non-empty; otherwise
  falls back to the JSON-backed pipeline.
* ``create_short_rent_listing_api`` inserts into ``short_rent_listings`` via
  SQLAlchemy and returns a frontend-friendly dict.
* ``get_short_rent_listings_from_db_api`` reads only persisted rows (no mock);
  used for DB verification (Phase 9-A4).
"""

import json

from backend.db_services.short_rent_db_service import (
    create_short_rent,
    get_all_short_rents,
)
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


def _created_short_rent_to_dict(item) -> dict:
    """Shape a freshly inserted ``ShortRentDB`` row for the create-API response.

    Mirrors the storage columns 1:1 (with ``available_dates`` parsed back to a
    list) and tags the source as the internal RentalAI platform.
    """
    return {
        "id": getattr(item, "id", ""),
        "source_type": "internal",
        "source": "RentalAI",
        "title": getattr(item, "title", ""),
        "location": getattr(item, "location", ""),
        "postcode": getattr(item, "postcode", ""),
        "price_per_day": getattr(item, "price_per_day", ""),
        "available_dates": _parse_available_dates(getattr(item, "available_dates", None)),
        "min_days": getattr(item, "min_days", ""),
        "max_days": getattr(item, "max_days", ""),
        "landlord_id": getattr(item, "landlord_id", ""),
        "description": getattr(item, "description", ""),
        "created_at": getattr(item, "created_at", ""),
    }


def create_short_rent_listing_api(data: dict) -> dict:
    try:
        created = create_short_rent(data)
        return {
            "success": True,
            "data": _created_short_rent_to_dict(created),
            "message": "Short rent listing created successfully.",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": None,
        }


def get_short_rent_listings_from_db_api() -> dict:
    """Return every row in ``short_rent_listings`` only (no JSON/mock fallback).

    Intended for Phase 9-A4 PostgreSQL persistence checks; response shape matches
    ``get_short_rent_recommendations_api`` ``data`` items where applicable.
    """
    try:
        db_items = get_all_short_rents()
        results = [db_short_rent_to_dict(row) for row in db_items]
        return {
            "success": True,
            "source": "database",
            "data": results,
            "count": len(results),
        }
    except Exception as e:
        return {
            "success": False,
            "source": "database",
            "error": str(e),
            "data": [],
            "count": 0,
        }
