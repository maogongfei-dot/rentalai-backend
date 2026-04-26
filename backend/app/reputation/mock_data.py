"""
Mock reputation dataset for Phase 2 bootstrap (no external APIs, no crawling).
"""

from __future__ import annotations

from typing import Any

MOCK_REPUTATION_RECORDS: list[dict[str, Any]] = [
    {
        "name": "Maple Court",
        "address": "12 Maple Court, Manchester",
        "postcode": "M1 4AB",
        "entity_type": "building",
        "rating": 4.2,
        "review_count": 28,
        "risk_tags": ["slow_maintenance"],
        "summary": "Residents usually mention fair management, but repairs can be slow.",
        "source": "mock_seed",
    },
    {
        "name": "NorthBridge Lettings",
        "address": "45 King Street, Leeds",
        "postcode": "LS1 2HQ",
        "entity_type": "agency",
        "rating": 2.6,
        "review_count": 54,
        "risk_tags": ["deposit_dispute", "poor_communication"],
        "summary": "Multiple reviews mention delayed deposit returns and weak communication.",
        "source": "mock_seed",
    },
    {
        "name": "22 Orchard Road",
        "address": "22 Orchard Road, Bristol",
        "postcode": "BS1 5TR",
        "entity_type": "address",
        "rating": 3.5,
        "review_count": 11,
        "risk_tags": ["noise_complaints"],
        "summary": "Mixed feedback; transport is good but some tenants mention evening noise.",
        "source": "mock_seed",
    },
]

