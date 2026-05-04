"""Homepage structure definition for the platform (data only, no UI)."""


def get_homepage_structure() -> dict:
    """Return the canonical homepage layout for downstream UI."""
    return {
        "hero_section": {
            "title": "RentalAI",
            "subtitle": "Find your next home smarter with AI",
        },
        "ai_entry": {
            "placeholder": "Describe what you are looking for...",
            "examples": [
                "£1200 budget in London",
                "short rent near Manchester",
                "2 bedroom near station",
            ],
        },
        "main_buttons": [
            {"name": "Find Long Rent", "route": "/long-rent"},
            {"name": "Find Short Rent", "route": "/short-rent"},
            {"name": "Map Search", "route": "/map"},
            {"name": "AI Search", "route": "/ai"},
            {"name": "List Your Property", "route": "/landlord"},
        ],
        "mode_switch": [
            {"name": "Tenant", "route": "/tenant"},
            {"name": "Landlord", "route": "/landlord"},
        ],
        "navigation": [
            "Home",
            "Long Rent",
            "Short Rent",
            "Map",
            "Landlord",
            "Contract",
            "Profile",
        ],
    }
