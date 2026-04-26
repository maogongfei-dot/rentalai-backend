"""
Query scope classification for RentalAI (rule-based; no LLM).

Distinguishes rental_core vs rental_related vs out_of_scope before intent routing.
"""

from __future__ import annotations

import re
from typing import Any

# --- Out-of-scope phrases (check before generic "property" core hits) -----------------
_OOS_PHRASES: tuple[str, ...] = (
    "investment property",
    "buying a house",
    "buy a house",
    "buying a home",
    "buy a home",
    "purchase a house",
    "purchase a home",
    "property investment",
    "stock market",
    "day trading",
)

# Strong OOS tokens (word-boundary where short)
_OOS_WORDS: tuple[str, ...] = (
    "mortgage",
    "mortgages",
    "remortgage",
    "cryptocurrency",
    "crypto",
    "bitcoin",
    "ethereum",
    "nft",
    "nfts",
    "coding",
    "programming",
    "javascript",
    "typescript",
    "react",
    "django",
    "leetcode",
)

# --- Rental core (tenancy / listing / costs) ----------------------------------------
_CORE_PHRASES: tuple[str, ...] = (
    "council tax",
    "tenancy agreement",
    "rent increase",
    "section 21",
    "section 8",
    "assured shorthold",
    "break clause",
    "deposit protection",
)

_CORE_WORDS: tuple[str, ...] = (
    "rent",
    "renting",
    "rental",
    "tenancy",
    "contract",
    "deposit",
    "landlord",
    "tenant",
    "eviction",
    "notice",
    "agreement",
    "bills",
    "utilities",
    "flat",
    "apartment",
    "lease",
    "letting",
    "hmo",
    "roommate",
    "lodger",
)

# --- Rental related (supports decisions but not core tenancy law) -------------------
_RELATED_PHRASES: tuple[str, ...] = (
    "cost of living",
    "living in uk",
    "living in the uk",
    "area safety",
    "public transport",
    "crime rate",
)

_RELATED_WORDS: tuple[str, ...] = (
    "moving",
    "relocation",
    "relocate",
    "transport",
    "commute",
    "neighbourhood",
    "neighborhood",
    "cost of living",
)


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _find_phrases(low: str, phrases: tuple[str, ...]) -> list[str]:
    found: list[str] = []
    for p in phrases:
        if p in low:
            found.append(p)
    return found


def _find_word_hits(low: str, words: tuple[str, ...]) -> list[str]:
    found: list[str] = []
    for w in words:
        if re.search(rf"(?<![\w]){re.escape(w)}(?![\w])", low):
            found.append(w)
    return found


def _core_hits(low: str) -> list[str]:
    hits = _find_phrases(low, _CORE_PHRASES)
    hits.extend(_find_word_hits(low, _CORE_WORDS))
    if "property" in low and "investment property" not in low:
        hits.append("property")
    # de-dupe preserve order
    seen: set[str] = set()
    out: list[str] = []
    for h in hits:
        if h not in seen:
            seen.add(h)
            out.append(h)
    return out


def _oos_hits(low: str) -> list[str]:
    hits = _find_phrases(low, _OOS_PHRASES)
    hits.extend(_find_word_hits(low, _OOS_WORDS))
    seen: set[str] = set()
    out: list[str] = []
    for h in hits:
        if h not in seen:
            seen.add(h)
            out.append(h)
    return out


def _related_hits(low: str) -> list[str]:
    hits = _find_phrases(low, _RELATED_PHRASES)
    hits.extend(_find_word_hits(low, _RELATED_WORDS))
    seen: set[str] = set()
    out: list[str] = []
    for h in hits:
        if h not in seen:
            seen.add(h)
            out.append(h)
    return out


def _confidence_for(scope: str, n_matches: int) -> float:
    if scope == "invalid":
        return 0.0
    base = 0.45 + 0.12 * min(n_matches, 5)
    if scope == "rental_core":
        base += 0.05
    return round(min(0.95, base), 2)


def classify_query_scope(user_text: str) -> dict[str, Any]:
    """
    Classify whether the query is in rental scope.

    Returns:
        scope: rental_core | rental_related | out_of_scope | invalid
        confidence: 0.0–1.0
        matched_keywords: keywords that supported the label
    """
    if not (user_text or "").strip():
        return {"scope": "invalid", "confidence": 0.0, "matched_keywords": []}

    low = _normalize(user_text)

    core = _core_hits(low)
    oos = _oos_hits(low)
    related = _related_hits(low)

    # Core always wins if we have tenancy/rent signals (even if "mortgage" appears in a compare sentence)
    if core:
        return {
            "scope": "rental_core",
            "confidence": _confidence_for("rental_core", len(core)),
            "matched_keywords": core,
        }

    # No explicit core: compare related vs OOS
    if oos and not related:
        return {
            "scope": "out_of_scope",
            "confidence": _confidence_for("out_of_scope", len(oos)),
            "matched_keywords": oos,
        }

    if related and not oos:
        return {
            "scope": "rental_related",
            "confidence": _confidence_for("rental_related", len(related)),
            "matched_keywords": related,
        }

    if related and oos:
        merged = list(dict.fromkeys(related + oos))
        return {
            "scope": "rental_related",
            "confidence": _confidence_for("rental_related", len(merged)),
            "matched_keywords": merged,
        }

    # No keyword hits: gentle default — still invite rental topics
    return {
        "scope": "rental_related",
        "confidence": 0.35,
        "matched_keywords": [],
    }


def scope_handling_label(scope: str) -> str:
    """Stable label for router / clients."""
    if scope == "rental_core":
        return "full_pipeline"
    if scope == "rental_related":
        return "light_guidance"
    if scope == "out_of_scope":
        return "soft_redirect"
    return "invalid_input"


def build_scope_message(scope: str, matched_keywords: list[str]) -> str:
    """
    User-facing copy for this scope (may be empty for rental_core).

    Tone: warm boundary, no "cannot help" / "not supported".
    """
    if scope == "rental_core":
        return ""
    if scope == "invalid":
        return "I could not understand the request."
    if scope == "rental_related":
        return "I can help from a rental perspective, but I may need a bit more detail."

    return (
        "I mainly help with renting, housing, and contracts. "
        "If you have a rental question, I can give you a detailed answer."
    )
