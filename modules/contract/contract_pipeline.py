"""
Contract analysis pipeline (Phase 3 Part 4) — single entry: parse → risk → explain.

Public API: ``analyze_contract_pipeline``.
"""

from __future__ import annotations

from typing import Any

from modules.contract.contract_parser import parse_contract_text
from modules.contract.risk_engine import analyze_contract_risks
from modules.contract.explain_engine import build_risk_explanations


def analyze_contract_pipeline(text: str) -> dict[str, Any]:
    """
    Run ``parse_contract_text`` → ``analyze_contract_risks`` → ``build_risk_explanations``.

    Empty text is allowed; the parser returns an empty-shaped result.

    On any exception, returns ``ok: False`` and ``data: None`` with a string ``error``.
    """
    try:
        parsed = parse_contract_text(text)
        risk = analyze_contract_risks(parsed)
        explanations = build_risk_explanations(risk)
        return {
            "ok": True,
            "data": {
                "parsed": parsed,
                "risk": risk,
                "explanations": explanations,
            },
            "error": None,
        }
    except Exception as exc:
        return {
            "ok": False,
            "data": None,
            "error": str(exc),
        }


def run_contract_pipeline_test() -> None:
    text = (
        "The deposit is £500. The term is 12 months. "
        "Termination notice period is 2 months. Repair and maintenance obligations apply."
    )
    result = analyze_contract_pipeline(text)
    print("OK:", result["ok"])
    if result["ok"] and result.get("data"):
        print("Risk level:", result["data"]["risk"]["risk_level"])
        print("Explanation:", result["data"]["explanations"]["overall_explanation"])
    else:
        print("error:", result.get("error"))


if __name__ == "__main__":
    run_contract_pipeline_test()
