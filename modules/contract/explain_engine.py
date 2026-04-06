"""
Risk explanation engine (Phase 3 Part 3) — template-based human-readable text.

Public API: ``build_risk_explanations``.
"""

from __future__ import annotations

import json
from typing import Any

try:
    from .contract_parser import parse_contract_text
    from .risk_engine import analyze_contract_risks
except ImportError:
    from contract_parser import parse_contract_text
    from risk_engine import analyze_contract_risks

_RISK_TYPE_EXPLANATIONS: dict[str, str] = {
    "deposit": (
        "This contract includes a deposit clause, which may affect your upfront cost."
    ),
    "term": "This contract has a fixed term, which may limit flexibility.",
    "termination": (
        "This contract includes termination or notice clauses. Please review carefully "
        "as they may impact your ability to leave."
    ),
    "maintenance": (
        "This contract defines maintenance responsibilities. Make sure you understand "
        "who is responsible for repairs."
    ),
}

_OVERALL_BY_LEVEL: dict[str, str] = {
    "high": (
        "This contract has high risk. You should review it carefully before proceeding."
    ),
    "medium": (
        "This contract has some risks. Please review key clauses carefully."
    ),
    "low": (
        "This contract appears relatively low risk, but still review important terms."
    ),
}


def _empty_explain_result() -> dict[str, Any]:
    return {
        "overall_explanation": "",
        "risk_explanations": [],
    }


def build_risk_explanations(risk_result: dict) -> dict[str, Any]:
    """
    Turn ``analyze_contract_risks`` output into templated explanations.

    Non-dict input returns an empty-shaped result (no exception).
    Missing ``risks`` is treated as an empty list.
    """
    if not isinstance(risk_result, dict):
        return _empty_explain_result()

    raw_risks = risk_result.get("risks")
    if not isinstance(raw_risks, list):
        raw_risks = []

    level = risk_result.get("risk_level")
    if level not in _OVERALL_BY_LEVEL:
        level = "low"
    overall = _OVERALL_BY_LEVEL[level]

    risk_explanations: list[dict[str, str]] = []
    for item in raw_risks:
        if not isinstance(item, dict):
            continue
        t = item.get("type")
        if not isinstance(t, str):
            continue
        explanation = _RISK_TYPE_EXPLANATIONS.get(t)
        if explanation is None:
            continue
        lv = item.get("level")
        if lv not in ("high", "medium", "low"):
            lv = "low"
        risk_explanations.append(
            {
                "type": t,
                "level": str(lv),
                "explanation": explanation,
            }
        )

    return {
        "overall_explanation": overall,
        "risk_explanations": risk_explanations,
    }


def run_explain_engine_test() -> None:
    sample = (
        "The deposit is £500. The term is 12 months. "
        "Termination notice period is 2 months. Repair and maintenance obligations apply."
    )
    parsed = parse_contract_text(sample)
    risk_result = analyze_contract_risks(parsed)
    explained = build_risk_explanations(risk_result)
    print("overall_explanation:", explained["overall_explanation"])
    print(
        "risk_explanations:",
        json.dumps(explained["risk_explanations"], ensure_ascii=True),
    )


if __name__ == "__main__":
    run_explain_engine_test()
