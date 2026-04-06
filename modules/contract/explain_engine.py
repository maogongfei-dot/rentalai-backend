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


def _format_issue_list(items: list[str]) -> str:
    """Join up to three issue strings for a single sentence."""
    cleaned = [x.strip() for x in items if x and str(x).strip()][:3]
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0]
    if len(cleaned) == 2:
        return f"{cleaned[0]} and {cleaned[1]}"
    return f"{cleaned[0]}, {cleaned[1]}, and {cleaned[2]}"


def build_human_readable_explanation(risk: dict) -> str:
    """
    Rule-based narrative from ``analyze_contract_risks`` output (Phase 4 Part 1).

    Uses ``risk_level``, optional ``issues``, ``risks[].message``, and optional ``score``
    (reserved for future use).
    """
    if not isinstance(risk, dict):
        return "The contract analysis result is unclear."

    risk_level = risk.get("risk_level")
    _ = risk.get("score")  # optional; reserved for future scoring

    issue_strings: list[str] = []
    raw_issues = risk.get("issues")
    if isinstance(raw_issues, list) and raw_issues:
        for x in raw_issues[:3]:
            s = str(x).strip()
            if s:
                issue_strings.append(s)
    else:
        raw_risks = risk.get("risks")
        if isinstance(raw_risks, list):
            for item in raw_risks:
                if not isinstance(item, dict):
                    continue
                msg = item.get("message")
                if msg:
                    issue_strings.append(str(msg).strip())
                if len(issue_strings) >= 3:
                    break

    level = (str(risk_level).lower() if risk_level is not None else "") or ""

    if level == "high":
        opening = "This contract appears to contain high-risk terms."
        closing = "You should review these clauses carefully before signing."
    elif level == "medium":
        opening = "This contract has some potentially risky or unclear terms."
        closing = "Consider reviewing the unclear terms before proceeding."
    elif level == "low":
        opening = "This contract appears relatively low risk overall."
        closing = "You should still review the contract before signing."
    else:
        opening = "The contract analysis result is unclear."
        closing = ""

    parts: list[str] = [opening]
    concerns = _format_issue_list(issue_strings[:3])
    if concerns:
        parts.append(f" Key concerns include: {concerns}.")
    if closing:
        parts.append(f" {closing}")

    return "".join(parts).strip()


def _empty_explain_result() -> dict[str, Any]:
    return {
        "overall_explanation": "",
        "human_explanation": "",
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

    human = build_human_readable_explanation(risk_result)

    return {
        "overall_explanation": overall,
        "human_explanation": human,
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
    print("human_explanation:", explained.get("human_explanation"))
    print(
        "risk_explanations:",
        json.dumps(explained["risk_explanations"], ensure_ascii=True),
    )


if __name__ == "__main__":
    run_explain_engine_test()
