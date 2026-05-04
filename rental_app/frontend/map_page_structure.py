"""Map search page structure (data only; no map API or database)."""

_SUPPORTED_LISTING_MODES = [
    "long_rent",
    "short_rent",
    "external_short_rent",
]

_FILTERS = [
    "location",
    "max_price",
    "listing_mode",
    "bedrooms",
    "check_in_date",
    "check_out_date",
    "availability_status",
]

_MARKER_CARD_FIELDS = [
    "title",
    "price",
    "price_per_night",
    "location",
    "image_urls",
    "listing_mode",
    "source_type",
    "availability_status",
]

_SIDE_PANEL = {
    "enabled": True,
    "show_listing_cards": True,
    "show_filters": True,
}

_ACTIONS = [
    "View Details",
    "Save Property",
    "Open Original Listing",
]


def get_map_page_structure() -> dict:
    """Return the canonical map search page layout for downstream UI."""
    return {
        "page_type": "map_search",
        "map_provider": "mapbox_or_google_maps",
        "supported_listing_modes": list(_SUPPORTED_LISTING_MODES),
        "filters": list(_FILTERS),
        "marker_card_fields": list(_MARKER_CARD_FIELDS),
        "side_panel": dict(_SIDE_PANEL),
        "actions": list(_ACTIONS),
    }
