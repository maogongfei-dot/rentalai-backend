"""
Lightweight reputation analysis entry for address/building/agency entities.
"""

from __future__ import annotations

from typing import Any

from .mock_data import MOCK_REPUTATION_RECORDS

HIGH_RISK_TAGS = {
    "deposit_dispute",
    "unlicensed_hmo",
    "serious_safety_issue",
    "fraud_reports",
}
MEDIUM_RISK_TAGS = {
    "poor_communication",
    "slow_maintenance",
    "contract_complaints",
    "noise_complaints",
}


def _normalize(text: str) -> str:
    return " ".join((text or "").lower().split())


def _find_best_record(entity_name_or_address: str) -> dict[str, Any] | None:
    query = _normalize(entity_name_or_address)
    if not query:
        return None

    best: dict[str, Any] | None = None
    best_score = 0
    for item in MOCK_REPUTATION_RECORDS:
        name = _normalize(str(item.get("name") or ""))
        address = _normalize(str(item.get("address") or ""))
        postcode = _normalize(str(item.get("postcode") or ""))
        score = 0
        if query == name or query == address or (postcode and query == postcode):
            score += 4
        if query in name:
            score += 3
        if query in address:
            score += 2
        if postcode and query in postcode:
            score += 1
        if score > best_score:
            best = item
            best_score = score
    return best


def _reputation_level(record: dict[str, Any]) -> str:
    rating = record.get("rating")
    tags = {str(x).strip().lower() for x in (record.get("risk_tags") or [])}
    if tags & HIGH_RISK_TAGS:
        return "High Risk"
    if isinstance(rating, (int, float)):
        if float(rating) < 2.8:
            return "High Risk"
        if float(rating) < 3.6:
            return "Medium Risk"
    if tags & MEDIUM_RISK_TAGS:
        return "Medium Risk"
    if isinstance(rating, (int, float)) and float(rating) >= 3.6:
        return "Low Risk"
    return "Unknown"


def _suggested_action(level: str) -> str:
    if level == "High Risk":
        return "Treat this option carefully and request written confirmation on deposits, repairs, and contract terms."
    if level == "Medium Risk":
        return "Proceed with caution and clarify key tenancy points in writing before committing."
    if level == "Low Risk":
        return "This looks relatively safer, but still confirm rent, bills, and maintenance responsibility."
    return "I do not have enough verified reputation data yet; collect more details before deciding."


def analyze_reputation(entity_name_or_address: str) -> dict[str, Any]:
    """
    Return a lightweight reputation read for address/building/agency entities.

    When no match is found, returns Unknown without inventing data.
    """
    record = _find_best_record(entity_name_or_address)
    if not record:
        return {
            "entity": None,
            "reputation_level": "Unknown",
            "summary": "I do not have reputation data for this address, building, or agency yet.",
            "risk_tags": [],
            "suggested_action": _suggested_action("Unknown"),
            "source": "mock_seed",
        }

    level = _reputation_level(record)
    summary = str(record.get("summary") or "").strip()
    if not summary:
        summary = "Some reputation signals exist, but more context would improve confidence."
    return {
        "entity": {
            "name": record.get("name"),
            "address": record.get("address"),
            "postcode": record.get("postcode"),
            "entity_type": record.get("entity_type"),
            "rating": record.get("rating"),
            "review_count": record.get("review_count"),
        },
        "reputation_level": level,
        "summary": summary,
        "risk_tags": list(record.get("risk_tags") or []),
        "suggested_action": _suggested_action(level),
        "source": record.get("source") or "mock_seed",
    }

