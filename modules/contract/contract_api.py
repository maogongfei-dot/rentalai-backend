"""
Contract analysis public API (Phase 3 Part 5) — thin wrapper over the pipeline.

Public API: ``analyze_contract``.
"""

from __future__ import annotations

from typing import Any

from modules.contract.contract_pipeline import analyze_contract_pipeline


def analyze_contract(text: str) -> dict[str, Any]:
    """
    Unified entry for contract analysis; delegates to ``analyze_contract_pipeline``.

    Empty strings are passed through. On unexpected failure, returns the same
    error envelope as the pipeline layer.
    """
    try:
        return analyze_contract_pipeline(text)
    except Exception as exc:
        return {
            "ok": False,
            "data": None,
            "error": str(exc),
        }


def run_contract_api_test() -> None:
    text = (
        "The deposit is £500. The term is 12 months. "
        "Termination notice period is 2 months. Repair and maintenance obligations apply."
    )
    result = analyze_contract(text)
    print("OK:", result["ok"])
    if result["ok"]:
        print("Risk level:", result["data"]["risk"]["risk_level"])
        print("Explanation:", result["data"]["explanations"]["overall_explanation"])
    else:
        print("Error:", result["error"])


if __name__ == "__main__":
    run_contract_api_test()
