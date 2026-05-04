"""Listing page structure definition for long and short rent (data only, no UI)."""

_LIST_LAYOUT = {
    "view": "grid",
    "columns": 3,
    "show_map_preview": True,
}

_SORT_OPTIONS = [
    "recommended",
    "price_low_to_high",
    "price_high_to_low",
    "newest",
]


def get_listing_page_structure(mode: str = "long_rent") -> dict:
    """Return the canonical listing page layout for downstream UI."""
    if mode == "long_rent":
        return {
            "page_type": mode,
            "title": "Find Long Rent",
            "filters": [
                "location",
                "max_price",
                "bedrooms",
                "bills_included",
                "commute_time",
            ],
            "list_layout": dict(_LIST_LAYOUT),
            "card_fields": [
                "title",
                "price",
                "location",
                "bedrooms",
                "final_score",
                "explain_summary",
                "availability_status",
            ],
            "sort_options": list(_SORT_OPTIONS),
        }
    if mode == "short_rent":
        return {
            "page_type": mode,
            "title": "Find Short Rent",
            "filters": [
                "location",
                "max_price_per_night",
                "check_in_date",
                "check_out_date",
                "min_stay",
                "source_type",
            ],
            "list_layout": dict(_LIST_LAYOUT),
            "card_fields": [
                "title",
                "price_per_night",
                "location",
                "image_urls",
                "source_type",
                "availability_status",
            ],
            "sort_options": list(_SORT_OPTIONS),
        }
    raise ValueError(f"Unsupported mode: {mode!r}; use 'long_rent' or 'short_rent'.")
