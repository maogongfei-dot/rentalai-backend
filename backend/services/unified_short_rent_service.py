"""Unified short-term rent search: internal listings plus external mock platforms."""

from backend.services import external_short_rent_service
from backend.services import short_rent_service


def search_all_short_rent(filters: dict = None) -> dict:
    return {
        "internal": short_rent_service.get_recommended_short_rent(filters),
        "external": external_short_rent_service.get_external_short_rent_recommendations(
            filters
        ),
    }


def get_combined_short_rent_results(filters: dict = None) -> list:
    payload = search_all_short_rent(filters)
    out = []
    for item in payload["internal"]:
        out.append({"source_type": "internal", **item})
    for item in payload["external"]:
        out.append({"source_type": "external", **item})
    return out


def _price_per_day_sort_key(row: dict) -> float:
    v = row.get("price_per_day")
    if v is None:
        return 999999.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 999999.0


def get_ranked_short_rent_results(filters: dict = None) -> list:
    rows = get_combined_short_rent_results(filters)
    return sorted(rows, key=_price_per_day_sort_key)
