"""Landlord flow: create short-term listings and persist via JSON storage."""

import uuid
from datetime import datetime, timezone

from backend.models.short_rent_model import ShortRentListing
from backend.storage.short_rent_storage import (
    add_short_rent_listing,
    load_short_rent_listings,
)


def create_short_rent_listing(data: dict) -> dict:
    raw = data or {}
    listing_id = f"short_{uuid.uuid4().hex}"
    created_at = datetime.now(timezone.utc).isoformat()

    listing = ShortRentListing(
        id=listing_id,
        title=str(raw.get("title", "")),
        location=str(raw.get("location", "")),
        postcode=str(raw.get("postcode", "")),
        price_per_day=float(raw.get("price_per_day", 0.0)),
        available_dates=list(raw.get("available_dates", [])),
        min_days=int(raw.get("min_days", 0)),
        max_days=int(raw.get("max_days", 0)),
        landlord_id=str(raw.get("landlord_id", "")),
        description=str(raw.get("description", "")),
        created_at=created_at,
    )
    add_short_rent_listing(listing)
    return listing.to_dict()


def check_availability(listing: ShortRentListing, requested_dates: list) -> bool:
    allowed = set(listing.available_dates or [])
    for day in requested_dates or []:
        if day not in allowed:
            return False
    return True


def filter_available_listings(listings: list, requested_dates: list) -> list:
    out = []
    for listing in listings or []:
        if check_availability(listing, requested_dates):
            out.append(listing)
    return out


def _matches_filters(listing: ShortRentListing, filters: dict) -> bool:
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


def get_short_rent_listings(filters: dict = None) -> list:
    filters = dict(filters) if filters else {}
    rows = load_short_rent_listings()
    out = []
    for listing in rows:
        if not filters or _matches_filters(listing, filters):
            out.append(listing.to_dict())
    return out


def get_recommended_short_rent(filters: dict = None) -> list:
    items = get_short_rent_listings(filters)
    sorted_items = sorted(items, key=lambda x: float(x.get("price_per_day") or 0))
    return sorted_items[:5]
