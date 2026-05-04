"""Listing detail page structure for long, short, and external short rent (data only, no UI)."""

_SECTIONS = [
    "overview",
    "media",
    "price",
    "location",
    "ai_analysis",
    "reviews",
    "landlord",
]

_MEDIA_SECTION = {
    "image_gallery": {},
    "video": {},
    "virtual_tour_3d": {},
}

_AI_ANALYSIS_SECTION = {
    "final_score": None,
    "explain_summary": None,
    "risk_flags": None,
    "area_summary": None,
    "availability_status": None,
}

_REVIEW_SECTION = {
    "landlord_rating": None,
    "review_count": None,
    "review_list": None,
}

_LANDLORD_SECTION = {
    "landlord_name": None,
    "landlord_rating": None,
    "landlord_profile_link": None,
}

_PRICE_LONG = {
    "monthly_price": None,
    "bills_included": None,
    "deposit": None,
}

_PRICE_SHORT = {
    "price_per_night": None,
    "cleaning_fee": None,
    "min_stay_nights": None,
    "total_price_estimate": None,
}

_ACTION_LONG = [
    "Contact Landlord",
    "Save Property",
    "Analyze Contract",
]

_ACTION_SHORT = [
    "Check Availability",
    "Book / Enquire",
    "Save Property",
]

_ACTION_EXTERNAL = [
    "View Original Listing",
    "Save Property",
]


def get_listing_detail_structure(listing_mode: str = "long_rent") -> dict:
    """Return the canonical listing detail page layout for downstream UI."""
    if listing_mode == "long_rent":
        price_section = dict(_PRICE_LONG)
        action_buttons = list(_ACTION_LONG)
    elif listing_mode in ("short_rent", "external_short_rent"):
        price_section = dict(_PRICE_SHORT)
        if listing_mode == "short_rent":
            action_buttons = list(_ACTION_SHORT)
        else:
            action_buttons = list(_ACTION_EXTERNAL)
    else:
        raise ValueError(
            f"Unsupported listing_mode: {listing_mode!r}; "
            "use 'long_rent', 'short_rent', or 'external_short_rent'."
        )

    return {
        "page_type": listing_mode,
        "sections": list(_SECTIONS),
        "media_section": {k: dict(v) for k, v in _MEDIA_SECTION.items()},
        "price_section": price_section,
        "ai_analysis_section": dict(_AI_ANALYSIS_SECTION),
        "review_section": dict(_REVIEW_SECTION),
        "landlord_section": dict(_LANDLORD_SECTION),
        "action_buttons": action_buttons,
    }
