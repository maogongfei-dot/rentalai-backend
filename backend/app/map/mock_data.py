"""
Mock location dataset for Phase 3 map bootstrap (no external map APIs).
"""

from __future__ import annotations

from typing import Any

MOCK_LOCATION_RECORDS: list[dict[str, Any]] = [
    {
        "normalized_address": "22 Orchard Road, Bristol",
        "postcode": "BS1 5TR",
        "city": "Bristol",
        "nearby_points": ["Temple Meads station", "Local supermarket", "Primary school"],
        "transport_hint": "12 min walk to the nearest major station",
    },
    {
        "normalized_address": "12 Maple Court, Manchester",
        "postcode": "M1 4AB",
        "city": "Manchester",
        "nearby_points": ["Piccadilly station", "City centre supermarket", "Bus hub"],
        "transport_hint": "10 min walk to station",
    },
    {
        "normalized_address": "45 King Street, Leeds",
        "postcode": "LS1 2HQ",
        "city": "Leeds",
        "nearby_points": ["Leeds station", "Shopping area", "Secondary school"],
        "transport_hint": "8 min walk to station",
    },
]

