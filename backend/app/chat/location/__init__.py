"""UK location context and city tables (no external APIs)."""

from __future__ import annotations

from .uk_cities import ALL_UK_CITIES_LOWERCASE, KNOWN_UK_CITIES, PRIMARY_UK_CITIES_DISPLAY
from .uk_context import build_uk_location_context, empty_uk_location_context

__all__ = [
    "ALL_UK_CITIES_LOWERCASE",
    "KNOWN_UK_CITIES",
    "PRIMARY_UK_CITIES_DISPLAY",
    "build_uk_location_context",
    "empty_uk_location_context",
]
