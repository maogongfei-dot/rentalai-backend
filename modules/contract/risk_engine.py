"""
Contract risk engine (Phase 3 Part 2) — rule-based flags from parsed contract output.

Public API: ``analyze_contract_risks``.
"""

from __future__ import annotations

import json
from typing import Any

try:
    from .contract_parser import parse_contract_text
except ImportError:
    from contract_parser import parse_contract_text


def _empty_risk_result() -> dict[str, Any]:
    return {
        "risk_level": "low",
        "risks": [],
        "summary": {
            "total_risks": 0,
            "high_risks": 0,
            "medium_risks": 0,
            "low_risks": 0,
        },
    }


def _normalize_keywords(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [str(x) for x in raw if isinstance(x, str)]


def _normalize_entities(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    return raw


def _compute_summary(risks: list[dict[str, str]]) -> dict[str, int]:
    high = sum(1 for r in risks if r.get("level") == "high")
    medium = sum(1 for r in risks if r.get("level") == "medium")
    low = sum(1 for r in risks if r.get("level") == "low")
    return {
        "total_risks": len(risks),
        "high_risks": high,
        "medium_risks": medium,
        "low_risks": low,
    }


def _overall_risk_level(risks: list[dict[str, str]]) -> str:
    levels = {r.get("level") for r in risks}
    if "high" in levels:
        return "high"
    if "medium" in levels:
        return "medium"
    return "low"


def analyze_contract_risks(parsed_contract: dict) -> dict[str, Any]:
    """
    Apply simple keyword/entity rules to ``parse_contract_text`` output.

    Non-dict input returns an empty-shaped result (no exception).
    Missing ``keywords`` / ``entities`` are treated as empty.
    """
    if not isinstance(parsed_contract, dict):
        return _empty_risk_result()

    keywords = _normalize_keywords(parsed_contract.get("keywords"))
    entities = _normalize_entities(parsed_contract.get("entities"))

    risks: list[dict[str, str]] = []

    if entities.get("deposit"):
        risks.append(
            {
                "type": "deposit",
                "level": "medium",
                "message": "Deposit clause detected",
            }
        )

    if entities.get("term"):
        risks.append(
            {
                "type": "term",
                "level": "low",
                "message": "Fixed term detected",
            }
        )

    if "termination" in keywords or "notice" in keywords:
        risks.append(
            {
                "type": "termination",
                "level": "high",
                "message": "Termination clause detected",
            }
        )

    if "repair" in keywords or "maintenance" in keywords:
        risks.append(
            {
                "type": "maintenance",
                "level": "medium",
                "message": "Maintenance responsibility clause detected",
            }
        )

    summary = _compute_summary(risks)
    return {
        "risk_level": _overall_risk_level(risks),
        "risks": risks,
        "summary": summary,
    }


def run_contract_risk_test() -> None:
    sample = (
        "The deposit is £500. The term is 12 months. "
        "Termination notice period is 2 months. Repair and maintenance obligations apply."
    )
    parsed = parse_contract_text(sample)
    result = analyze_contract_risks(parsed)
    print("risks:", json.dumps(result["risks"], ensure_ascii=True))
    print("risk_level:", result["risk_level"])
    print("summary:", json.dumps(result["summary"], ensure_ascii=True))


if __name__ == "__main__":
    run_contract_risk_test()
