"""Landlord listing normalization and validation (no database or uploads)."""

import uuid
from typing import Any


_LISTING_KEYS = (
    "id",
    "landlord_id",
    "owner_user_id",
    "listing_mode",
    "source_type",
    "title",
    "description",
    "location",
    "postcode",
    "monthly_price",
    "price_per_night",
    "deposit",
    "bills_included",
    "bedrooms",
    "min_stay_nights",
    "cleaning_fee",
    "availability_status",
    "image_urls",
    "video_url",
    "virtual_tour_url",
)


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def create_landlord_listing(data: dict) -> dict:
    """Normalize raw landlord input into a full listing-shaped dict."""
    raw = dict(data) if data else {}
    listing = {key: raw.get(key) for key in _LISTING_KEYS}

    listing_mode = listing.get("listing_mode")
    if _is_blank(listing_mode):
        listing_mode = "long_rent"

    availability_status = listing.get("availability_status")
    if _is_blank(availability_status):
        availability_status = "available"

    listing_id = listing.get("id")
    if _is_blank(listing_id):
        listing_id = f"landlord_{uuid.uuid4().hex}"

    listing["id"] = listing_id
    listing["listing_mode"] = listing_mode
    listing["availability_status"] = availability_status
    listing["source_type"] = "platform"
    return listing


def validate_landlord_listing(listing: dict) -> dict:
    """Check required landlord listing fields; return validity and gaps."""
    missing_fields: list[str] = []
    errors: list[str] = []

    if _is_blank(listing.get("landlord_id")):
        missing_fields.append("landlord_id")
    if _is_blank(listing.get("title")):
        missing_fields.append("title")
    if _is_blank(listing.get("location")):
        missing_fields.append("location")
    if _is_blank(listing.get("listing_mode")):
        missing_fields.append("listing_mode")

    mode = listing.get("listing_mode")
    if mode == "long_rent" and _is_blank(listing.get("monthly_price")):
        missing_fields.append("monthly_price")
    if mode == "short_rent" and _is_blank(listing.get("price_per_night")):
        missing_fields.append("price_per_night")

    is_valid = not missing_fields and not errors
    return {
        "is_valid": is_valid,
        "missing_fields": missing_fields,
        "errors": errors,
    }


def prepare_landlord_listing_for_save(data: dict) -> dict:
    """Build listing from input and attach validation result."""
    listing = create_landlord_listing(data)
    validation = validate_landlord_listing(listing)
    return {
        "listing": listing,
        "validation": validation,
    }


def update_listing_status(listing: dict, new_status: str) -> dict:
    """
    Update landlord listing availability status.
    Allowed status: available, rented, paused, unknown
    """
    allowed_statuses = ["available", "rented", "paused", "unknown"]
    if new_status not in allowed_statuses:
        return {
            "listing": listing,
            "success": False,
            "error": "invalid_status",
        }
    listing["availability_status"] = new_status
    return {
        "listing": listing,
        "success": True,
        "error": None,
    }
