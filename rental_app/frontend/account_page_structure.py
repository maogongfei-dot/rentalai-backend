"""Account page structure for tenant and landlord (data only; no database or AI)."""

_PROFILE_KEYS = [
    "user_id",
    "user_name",
    "email",
    "user_type",
    "avatar_url",
]

_SHARED_SECTIONS = [
    "account_settings",
    "notification_settings",
    "privacy_settings",
]

_TENANT_SECTIONS = [
    "saved_properties",
    "search_history",
    "ai_analysis_history",
    "contract_analysis_history",
    "reviews_given",
]

_TENANT_ACTIONS = [
    "View Saved Properties",
    "View Search History",
    "Edit Profile",
]

_LANDLORD_SECTIONS = [
    "my_listings",
    "listing_performance",
    "reviews_received",
    "landlord_rating",
    "payment_settings",
]

_LANDLORD_ACTIONS = [
    "Manage Listings",
    "Publish New Property",
    "View Reviews",
]


def get_account_page_structure(user_type: str = "tenant") -> dict:
    """Return the canonical account page layout for downstream UI."""
    profile_section = {key: None for key in _PROFILE_KEYS}

    if user_type == "tenant":
        tenant_sections = list(_TENANT_SECTIONS)
        landlord_sections: list[str] = []
        actions = list(_TENANT_ACTIONS)
    elif user_type == "landlord":
        tenant_sections = []
        landlord_sections = list(_LANDLORD_SECTIONS)
        actions = list(_LANDLORD_ACTIONS)
    else:
        raise ValueError(
            f"Unsupported user_type: {user_type!r}; use 'tenant' or 'landlord'."
        )

    return {
        "page_type": user_type,
        "profile_section": profile_section,
        "tenant_sections": tenant_sections,
        "landlord_sections": landlord_sections,
        "shared_sections": list(_SHARED_SECTIONS),
        "actions": actions,
    }
