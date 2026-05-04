"""Global top navigation structure (data only; no database or routing)."""

_NAV_ITEMS = [
    {"name": "Home", "route": "/"},
    {"name": "Long Rent", "route": "/long-rent"},
    {"name": "Short Rent", "route": "/short-rent"},
    {"name": "Map", "route": "/map"},
    {"name": "Contract Analysis", "route": "/contract"},
    {"name": "Landlord", "route": "/landlord"},
]

_USER_ACTIONS = [
    {"name": "Login", "route": "/login"},
    {"name": "Register", "route": "/register"},
    {"name": "Profile", "route": "/account"},
]

_MODE_SWITCH = [
    {"name": "Tenant Mode", "route": "/tenant"},
    {"name": "Landlord Mode", "route": "/landlord"},
]


def get_navigation_structure() -> dict:
    """Return the canonical top navigation layout for downstream UI."""
    return {
        "brand": "RentalAI",
        "nav_items": [dict(item) for item in _NAV_ITEMS],
        "user_actions": [dict(item) for item in _USER_ACTIONS],
        "mode_switch": [dict(item) for item in _MODE_SWITCH],
    }
