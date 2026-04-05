"""
Keyword-based intent labels for the chat router (upgradeable to ML later).

Order matters: first matching group wins (see ``classify_intent``).
"""

from __future__ import annotations

# Phrases / tokens (lowercased substring match unless noted).
INTENT_PROPERTY_COMPARISON = (
    "compare properties",
    "compare these",
    "which property",
    "which flat",
    "which house",
    "side by side",
    " versus ",
    " vs ",
    "better deal",
)

INTENT_LEGAL_RISK = (
    "contract",
    "tenancy",
    "tenancy agreement",
    "clause",
    "deposit",
    "landlord",
    "tenant",
    "legal",
    "illegal",
    "notice",
    "eviction",
    "section 21",
    "section 8",
    "rent increase",
    "unsafe",
    "rights",
    "breach",
    "assured shorthold",
    "ast",
    "break clause",
    "termination",
    "repairs",
    "access",
    "possession",
    "evict",
)

INTENT_BILLS_COST = (
    "council tax",
    "utility",
    "utilities",
    "energy bill",
    "electricity bill",
    "gas bill",
    "water bill",
    "broadband cost",
    "monthly bills",
)

INTENT_PROPERTY_ANALYSIS = (
    "property analysis",
    "analyse this property",
    "analyze this property",
    "is this listing",
    "worth it",
    "rental yield",
    "market rent",
    "listing quality",
)

INTENT_AREA_INFO = (
    "neighbourhood",
    "neighborhood",
    "crime rate",
    "school catchment",
    "commute time",
    "transport links",
    "local area",
    "what is the area like",
)

INTENT_ORDER: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("property_comparison", INTENT_PROPERTY_COMPARISON),
    ("legal_risk", INTENT_LEGAL_RISK),
    ("bills_cost", INTENT_BILLS_COST),
    ("property_analysis", INTENT_PROPERTY_ANALYSIS),
    ("area_info", INTENT_AREA_INFO),
)


def classify_intent(user_text: str) -> str:
    """Return intent id or ``general_unknown``."""
    low = " ".join(user_text.lower().split())
    for intent_id, patterns in INTENT_ORDER:
        for p in patterns:
            if p in low:
                return intent_id
    return "general_unknown"
