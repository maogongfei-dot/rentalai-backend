"""
Rule-based housing preference signals from user text (no LLM; for ranking / UX later).
"""

from __future__ import annotations

import re
from typing import Any

# UK cities / areas (lowercase substring match on normalized text).
_KNOWN_LOCATIONS: tuple[str, ...] = (
    "london",
    "manchester",
    "birmingham",
    "leeds",
    "glasgow",
    "liverpool",
    "bristol",
    "sheffield",
    "edinburgh",
    "cardiff",
    "belfast",
    "newcastle",
    "nottingham",
    "southampton",
    "leicester",
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

# (priority_key, tuple of substrings to search in lowercased text)
_PRICE_PATTERNS: tuple[str, ...] = (
    "cheap",
    "cheaper",
    "budget",
    "affordable",
    "low cost",
    "not expensive",
    "save money",
    "low rent",
    "inexpensive",
    "under ",
)

_SAFETY_PATTERNS: tuple[str, ...] = (
    "safe",
    "safer",
    "secure",
    "quiet area",
    "not dangerous",
)

_COMMUTE_PATTERNS: tuple[str, ...] = (
    "near station",
    "near the station",
    "close to station",
    "close to the station",
    "close to work",
    "commute",
    "easy transport",
    "near tube",
    "near train",
    "near bus",
    "walking distance",
)

_AREA_PATTERNS: tuple[str, ...] = (
    "good area",
    "nice neighbourhood",
    "nice neighborhood",
    "city centre",
    "city center",
    "town centre",
    "town center",
    "local area",
    "nearby shops",
    "local facilities",
)

_BILLS_PATTERNS: tuple[str, ...] = (
    "bills included",
    "include bills",
    "all bills",
    "council tax",
    "utilities",
    "utility bills",
    "electricity",
    "gas bill",
    "water bill",
)

_SPACE_PATTERNS: tuple[str, ...] = (
    "bigger",
    "spacious",
    "more space",
    "large room",
    "storage",
    "large flat",
    "large apartment",
)

_FAMILY_PATTERNS: tuple[str, ...] = (
    "family",
    "kids",
    "child",
    "children",
)

_STUDENT_PATTERNS: tuple[str, ...] = (
    "student",
    "university",
    "campus",
)

# Shared "school" — map to family if not clearly student context
_SCHOOL_PATTERN = "school"

# Budget: capture integers; prefer explicit budget / max / under phrases.
_BUDGET_RES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"budget\s*(?:is|of|:)?\s*£?\s*(\d{3,6})", re.I), "budget"),
    (re.compile(r"(?:under|below|max|maximum|up to|no more than)\s*£?\s*(\d{3,6})", re.I), "cap"),
    (re.compile(r"£\s*(\d{3,6})\s*(?:pcm|per month|/month|a month)?", re.I), "gbp"),
    (re.compile(r"(\d{3,6})\s*(?:pcm|per month|/month|a month)\b", re.I), "pcm"),
)

_PRIORITY_KEY_ORDER: tuple[str, ...] = (
    "price",
    "safety",
    "commute",
    "area",
    "bills",
    "space",
    "family",
    "student",
)


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _first_hit_positions(low: str, patterns: tuple[str, ...]) -> int | None:
    best: int | None = None
    for p in patterns:
        i = low.find(p)
        if i >= 0 and (best is None or i < best):
            best = i
    return best


def _empty_result() -> dict[str, Any]:
    return {
        "price_priority": False,
        "safety_priority": False,
        "commute_priority": False,
        "area_priority": False,
        "bills_priority": False,
        "space_priority": False,
        "family_priority": False,
        "student_priority": False,
        "raw_budget": None,
        "mentioned_locations": [],
        "mentioned_features": [],
        "priority_order": [],
    }


def _extract_budget_and_pos(user_text: str, low: str) -> tuple[int | None, int | None]:
    """Return (amount, char index of amount in user_text) for priority ordering."""
    for rx, _kind in _BUDGET_RES:
        m = rx.search(user_text)
        if m:
            try:
                val = int(m.group(1))
                return val, m.start(1)
            except (ValueError, IndexError):
                continue
    if any(w in low for w in ("budget", "under", "max", "pcm", "rent", "cheap")):
        m2 = re.search(r"\b(\d{3,5})\b", user_text)
        if m2:
            try:
                v = int(m2.group(1))
                if 300 <= v <= 20000:
                    return v, m2.start(1)
            except ValueError:
                pass
    return None, None


def _student_first_pos(low: str) -> int | None:
    best = _first_hit_positions(low, _STUDENT_PATTERNS)
    m = re.search(r"\buni\b", low)
    if m:
        u = m.start()
        if best is None or u < best:
            best = u
    return best


def _extract_locations(low: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for loc in _KNOWN_LOCATIONS:
        if loc in low:
            title = loc.title() if " " not in loc else " ".join(w.title() for w in loc.split())
            if title not in seen:
                seen.add(title)
                found.append(title)
    return found


def _collect_features(
    low: str,
    flags: dict[str, Any],
) -> list[str]:
    """Human-readable feature phrases for downstream UX (deduped, stable order)."""
    phrases: list[str] = []
    seen: set[str] = set()

    def add(label: str) -> None:
        if label not in seen:
            seen.add(label)
            phrases.append(label)

    if flags.get("commute") and any(
        p in low for p in ("station", "tube", "train", "bus", "commute", "work")
    ):
        if "station" in low or "tube" in low or "train" in low:
            add("near station / transport")
        elif "commute" in low or "work" in low:
            add("commute convenience")

    if flags.get("bills") and any(p in low for p in ("bills included", "include bills", "all bills")):
        add("bills included")
    elif flags.get("bills"):
        add("bills / utilities")

    if flags.get("area"):
        if "city centre" in low or "city center" in low or "town centre" in low or "town center" in low:
            add("city / town centre")
        elif "neighbourhood" in low or "neighborhood" in low or "good area" in low:
            add("neighbourhood quality")

    if flags.get("price") and flags.get("raw_budget"):
        add(f"budget around {flags['raw_budget']}")

    return phrases


def build_user_signals_summary(priority_order: list[str]) -> str:
    if not priority_order:
        return ""
    return "Detected priorities: " + ", ".join(priority_order)


def preference_voice_line(priority_order: list[str]) -> str:
    """One short product-style line; empty if no priorities."""
    if not priority_order:
        return ""
    labels = {
        "price": "price",
        "safety": "safety",
        "commute": "commuting convenience",
        "area": "the area and local amenities",
        "bills": "bills and running costs",
        "space": "space",
        "family": "family-friendly factors",
        "student": "student-friendly factors",
    }
    names = [labels.get(p, p) for p in priority_order[:3]]
    if len(names) == 1:
        return f"It sounds like {names[0]} is one of your main priorities."
    if len(names) == 2:
        return f"You seem to care most about {names[0]} and {names[1]}."
    return f"You seem to care most about {', '.join(names[:-1])}, and {names[-1]}."


def detect_user_preferences(user_text: str) -> dict[str, Any]:
    """
    Extract boolean priorities, optional budget, locations, features, and priority_order.

    Safe for empty input: returns an empty preference structure without raising.
    """
    if not (user_text or "").strip():
        return _empty_result()

    raw = user_text.strip()
    low = _normalize(raw)

    price_hit = _first_hit_positions(low, _PRICE_PATTERNS)
    safety_hit = _first_hit_positions(low, _SAFETY_PATTERNS)
    commute_hit = _first_hit_positions(low, _COMMUTE_PATTERNS)
    area_hit = _first_hit_positions(low, _AREA_PATTERNS)
    bills_hit = _first_hit_positions(low, _BILLS_PATTERNS)
    space_hit = _first_hit_positions(low, _SPACE_PATTERNS)
    family_hit = _first_hit_positions(low, _FAMILY_PATTERNS)
    school_hit = low.find(_SCHOOL_PATTERN) if _SCHOOL_PATTERN in low else -1
    if school_hit >= 0:
        if family_hit is None or school_hit < family_hit:
            family_hit = school_hit

    student_hit = _student_first_pos(low)

    raw_budget, budget_pos = _extract_budget_and_pos(raw, low)

    price_priority = price_hit is not None or raw_budget is not None
    safety_priority = safety_hit is not None
    commute_priority = commute_hit is not None
    area_priority = area_hit is not None
    bills_priority = bills_hit is not None
    space_priority = space_hit is not None
    family_priority = family_hit is not None
    student_priority = student_hit is not None

    if family_priority and student_priority and family_hit is not None and student_hit is not None:
        if family_hit < student_hit:
            student_priority = False
        elif student_hit < family_hit:
            family_priority = False
        elif "kids" in low or "children" in low:
            student_priority = False
        elif "university" in low or re.search(r"\buni\b", low):
            family_priority = False
        else:
            student_priority = False

    price_order_pos: int | None = None
    if price_hit is not None:
        price_order_pos = price_hit
    if budget_pos is not None:
        if price_order_pos is None or budget_pos < price_order_pos:
            price_order_pos = budget_pos

    positions: list[tuple[int, str]] = []
    checks: list[tuple[bool, int | None, str]] = [
        (price_priority, price_order_pos if price_priority else None, "price"),
        (safety_priority, safety_hit if safety_priority else None, "safety"),
        (commute_priority, commute_hit if commute_priority else None, "commute"),
        (area_priority, area_hit if area_priority else None, "area"),
        (bills_priority, bills_hit if bills_priority else None, "bills"),
        (space_priority, space_hit if space_priority else None, "space"),
        (family_priority, family_hit if family_priority else None, "family"),
        (student_priority, student_hit if student_priority else None, "student"),
    ]
    for active, pos, key in checks:
        if not active:
            continue
        # Use pattern position, or end of string for budget-only price
        order_pos = pos if pos is not None else len(low)
        positions.append((order_pos, key))

    positions.sort(
        key=lambda x: (
            x[0] if x[0] is not None else 10**9,
            _PRIORITY_KEY_ORDER.index(x[1]) if x[1] in _PRIORITY_KEY_ORDER else 99,
        )
    )
    priority_order: list[str] = []
    seen_k: set[str] = set()
    for _, k in positions:
        if k not in seen_k:
            seen_k.add(k)
            priority_order.append(k)

    mentioned_locations = _extract_locations(low)

    flags_for_features = {
        "commute": commute_priority,
        "bills": bills_priority,
        "area": area_priority,
        "price": price_priority,
        "raw_budget": raw_budget,
    }
    mentioned_features = _collect_features(low, flags_for_features)

    return {
        "price_priority": price_priority,
        "safety_priority": safety_priority,
        "commute_priority": commute_priority,
        "area_priority": area_priority,
        "bills_priority": bills_priority,
        "space_priority": space_priority,
        "family_priority": family_priority,
        "student_priority": student_priority,
        "raw_budget": raw_budget,
        "mentioned_locations": mentioned_locations,
        "mentioned_features": mentioned_features,
        "priority_order": priority_order,
    }
