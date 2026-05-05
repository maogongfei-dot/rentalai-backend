"""External short-term rent search: unified service over JSON-backed mock listings.

Real platform adapters (SpareRoom, OpenRent, Rightmove) can be added later; this layer
keeps filter semantics and response shape stable.
"""

from backend.models.external_short_rent_model import ExternalShortRentListing
from backend.storage.external_short_rent_storage import load_external_short_rent_listings


def _matches_filters(listing: ExternalShortRentListing, filters: dict) -> bool:
    loc = filters.get("location")
    if loc is not None and str(loc).strip():
        if str(loc).lower() not in str(listing.location or "").lower():
            return False
    mn = filters.get("min_price")
    if mn is not None:
        if listing.price_per_day < float(mn):
            return False
    mx = filters.get("max_price")
    if mx is not None:
        if listing.price_per_day > float(mx):
            return False
    return True


def search_external_short_rent(filters: dict = None) -> list:
    filters = dict(filters) if filters else {}
    rows = load_external_short_rent_listings()
    out = []
    for listing in rows:
        if not filters or _matches_filters(listing, filters):
            out.append(listing.to_dict())
    return out


def get_external_short_rent_recommendations(filters: dict = None) -> list:
    items = search_external_short_rent(filters)
    sorted_items = sorted(items, key=lambda x: float(x.get("price_per_day") or 0))
    return sorted_items[:10]
