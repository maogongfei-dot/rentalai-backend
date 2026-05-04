"""Landlord dashboard page structure (data only; no database or real uploads)."""

_SECTIONS = [
    "dashboard_overview",
    "publish_property",
    "media_upload",
    "my_listings",
    "reviews",
    "account",
]

_PUBLISH_FORM_FIELDS = [
    "listing_mode",
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
]

_MEDIA_UPLOAD = {
    "image_upload": {},
    "video_upload": {},
    "virtual_tour_3d_upload": {},
}

_LISTING_MANAGEMENT = {
    "edit_listing": {},
    "delete_listing": {},
    "pause_listing": {},
    "mark_as_rented": {},
    "mark_as_available": {},
}

_REVIEW_MANAGEMENT = {
    "view_reviews": {},
    "landlord_rating": {},
    "reply_to_review": {},
}

_ACTIONS = [
    "Publish Property",
    "Save Draft",
    "Preview Listing",
]


def get_landlord_page_structure() -> dict:
    """Return the canonical landlord dashboard layout for downstream UI."""
    publish_form = {field: None for field in _PUBLISH_FORM_FIELDS}
    return {
        "page_type": "landlord_dashboard",
        "sections": list(_SECTIONS),
        "publish_form": publish_form,
        "media_upload": {k: dict(v) for k, v in _MEDIA_UPLOAD.items()},
        "listing_management": {k: dict(v) for k, v in _LISTING_MANAGEMENT.items()},
        "review_management": {k: dict(v) for k, v in _REVIEW_MANAGEMENT.items()},
        "actions": list(_ACTIONS),
    }
