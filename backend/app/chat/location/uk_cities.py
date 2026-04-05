"""
UK city allowlist for matching and routing (expandable; no API).

Tier-1 cities are the minimum supported set for UK-wide routing; extended cities
keep parity with earlier preference/property parsers.
"""

from __future__ import annotations

# Primary tier — minimum set for UK-wide product messaging (expand here first).
PRIMARY_UK_CITIES_DISPLAY: tuple[str, ...] = (
    "London",
    "Manchester",
    "Birmingham",
    "Leeds",
    "Liverpool",
    "Sheffield",
    "Bristol",
    "Nottingham",
    "Leicester",
    "Newcastle",
)

# Lowercase slugs for substring search (same order as display).
PRIMARY_UK_CITIES_SLUG: tuple[str, ...] = tuple(c.lower() for c in PRIMARY_UK_CITIES_DISPLAY)

# Additional UK places (same as legacy KNOWN_UK_CITIES minus duplicates).
_EXTENDED_SLUGS: tuple[str, ...] = (
    "glasgow",
    "edinburgh",
    "cardiff",
    "belfast",
    "southampton",
    "oxford",
    "cambridge",
    "brighton",
    "reading",
    "york",
    "bath",
    "norwich",
    "plymouth",
    "coventry",
    "swansea",
    "portsmouth",
    "bournemouth",
    "milton keynes",
    "aberdeen",
    "dundee",
)

# Single tuple for location matching (deduped, stable order: primary first).
def _merge_city_slugs() -> tuple[str, ...]:
    seen: set[str] = set()
    out: list[str] = []
    for s in list(PRIMARY_UK_CITIES_SLUG) + list(_EXTENDED_SLUGS):
        if s not in seen:
            seen.add(s)
            out.append(s)
    return tuple(out)


ALL_UK_CITIES_LOWERCASE: tuple[str, ...] = _merge_city_slugs()

# Back-compat alias for preference / property_input / comparison parsers.
KNOWN_UK_CITIES = ALL_UK_CITIES_LOWERCASE


def slug_to_display_name(slug: str) -> str:
    """Title-case a known slug; keeps 'Milton Keynes' style."""
    s = slug.strip().lower()
    for d in PRIMARY_UK_CITIES_DISPLAY:
        if d.lower() == s:
            return d
    return " ".join(w.title() for w in s.split())


def is_primary_city_display(name: str) -> bool:
    return name.strip().title() in {c.title() for c in PRIMARY_UK_CITIES_DISPLAY} or any(
        name.lower() == p.lower() for p in PRIMARY_UK_CITIES_DISPLAY
    )
