"""Landlord flow: create short-term listings and persist via JSON storage."""

import uuid
from datetime import datetime, timezone

from backend.models.short_rent_model import ShortRentListing
from backend.storage.short_rent_storage import add_short_rent_listing


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
