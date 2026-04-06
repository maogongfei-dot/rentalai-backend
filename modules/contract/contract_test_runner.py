"""
Contract analysis demo, batch regression, expected vs actual checks, and assertions (Phase 3 Part 22).

Uses ``run_contract_analysis`` from ``contract_service`` (Part 24); presenter for display (Part 25).
"""

from __future__ import annotations

from typing import Any

from modules.contract.contract_presenter import print_contract_result
from modules.contract.contract_service import run_contract_analysis


def run_contract_demo() -> None:
    """
    Standalone contract analysis demo — no chat routing or intent detection (Phase 3 Part 17).

    Runs two sample texts: higher-signal clauses, then a broader safer-style paragraph.
    """
    print("=== Contract Demo ===")
    sample_high = (
        "The tenant must pay a non-refundable fee. "
        "The landlord may terminate the agreement immediately with notice."
    )
    sample_safe = (
        "The tenant will pay rent monthly. The deposit is protected. "
        "Notice is required before termination. Repair responsibilities are described."
    )
    for label, text in (
        ("Sample 1 (higher-risk wording)", sample_high),
        ("Sample 2 (broader / safer wording)", sample_safe),
    ):
        print()
        print("---", label, "---")
        final_output = run_contract_analysis(text)
        print_contract_result(final_output)


def compare_contract_case_result(
    expected: dict[str, Any], final_output: dict[str, Any]
) -> dict[str, Any]:
    """
    Compare declared expectations to actual pipeline output (Phase 3 Part 20).

    ``expected`` should include ``ok``, ``risk_level``, and ``verdict_status`` when used in batch tests.
    """
    exp = expected or {}
    actual_ok = final_output.get("ok")
    actual_risk = (final_output.get("summary") or {}).get("risk_level")
    actual_verdict = (final_output.get("verdict") or {}).get("status")
    actual = {
        "ok": actual_ok,
        "risk_level": actual_risk,
        "verdict_status": actual_verdict,
    }
    checks = {
        "ok": exp.get("ok") == actual_ok,
        "risk_level": exp.get("risk_level") == actual_risk,
        "verdict_status": exp.get("verdict_status") == actual_verdict,
    }
    match = all(checks.values())
    return {
        "match": match,
        "checks": checks,
        "expected": exp,
        "actual": actual,
    }


def summarize_contract_test_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Aggregate batch case rows for regression dashboards (Phase 3 Part 19–20).

    ``unknown_risk`` counts cases whose ``risk_level`` is not high / medium / low (including missing).
    """
    total = len(results)
    success = sum(1 for r in results if r.get("ok") is True)
    failed = total - success
    high_risk = sum(1 for r in results if r.get("risk_level") == "high")
    medium_risk = sum(1 for r in results if r.get("risk_level") == "medium")
    low_risk = sum(1 for r in results if r.get("risk_level") == "low")
    unknown_risk = sum(
        1 for r in results if r.get("risk_level") not in ("high", "medium", "low")
    )
    matched_cases = sum(
        1 for r in results if (r.get("comparison") or {}).get("match") is True
    )
    mismatched_cases = total - matched_cases
    return {
        "total": total,
        "success": success,
        "failed": failed,
        "high_risk": high_risk,
        "medium_risk": medium_risk,
        "low_risk": low_risk,
        "unknown_risk": unknown_risk,
        "matched_cases": matched_cases,
        "mismatched_cases": mismatched_cases,
        "cases": results,
    }


def build_contract_test_assertions(summary: dict[str, Any]) -> dict[str, Any]:
    """
    Turn a batch regression summary into a pass/fail verdict (Phase 3 Part 21).

    ``summary`` must be the return value of ``summarize_contract_test_results`` (includes ``cases``
    with ``comparison`` from Part 20).
    """
    mismatched = int(summary.get("mismatched_cases") or 0)
    passed = mismatched == 0
    cases = summary.get("cases") or []
    failed_case_names: list[str] = []
    failed_check_details: list[dict[str, Any]] = []
    for item in cases:
        comparison = item.get("comparison") or {}
        if comparison.get("match") is not True:
            name = str(item.get("case_name") or "")
            failed_case_names.append(name)
            failed_check_details.append(
                {
                    "case_name": name,
                    "checks": comparison.get("checks") or {},
                }
            )
    return {
        "passed": passed,
        "total_cases": summary.get("total", 0),
        "matched_cases": summary.get("matched_cases", 0),
        "mismatched_cases": summary.get("mismatched_cases", 0),
        "failed_case_names": failed_case_names,
        "failed_check_details": failed_check_details,
    }


def run_contract_batch_test() -> None:
    """
    Run several contract texts through the full pipeline for quick regression (Phase 3 Part 18–21).

    Expected fields are aligned to current rule-based engine + main verdict layer; update them if
    core contract modules change. Does not use intent detection or chat routing.
    """
    # Expected values track current pipeline behaviour for regression (Part 20).
    cases: tuple[dict[str, Any], ...] = (
        {
            "case_name": "high risk",
            "text": (
                "The tenant must pay a non-refundable fee. "
                "The landlord may terminate the agreement immediately."
            ),
            "expected": {
                "ok": True,
                "risk_level": "low",
                "verdict_status": "review_needed",
            },
        },
        {
            "case_name": "medium / review",
            "text": (
                "The landlord may increase rent with notice. "
                "The tenant must follow additional terms."
            ),
            "expected": {
                "ok": True,
                "risk_level": "high",
                "verdict_status": "high_risk",
            },
        },
        {
            "case_name": "low risk",
            "text": (
                "The tenant will pay rent monthly. The deposit is protected. "
                "Notice is required before termination. Repair responsibilities are described."
            ),
            "expected": {
                "ok": True,
                "risk_level": "high",
                "verdict_status": "high_risk",
            },
        },
        {
            "case_name": "empty input",
            "text": "",
            "expected": {
                "ok": True,
                "risk_level": "low",
                "verdict_status": "review_needed",
            },
        },
        {
            "case_name": "whitespace-only input",
            "text": "   ",
            "expected": {
                "ok": True,
                "risk_level": "low",
                "verdict_status": "review_needed",
            },
        },
    )
    results: list[dict[str, Any]] = []
    for case in cases:
        case_name = case["case_name"]
        text = case["text"]
        expected = case["expected"]
        print()
        print("=== Contract Batch Test ===")
        print("Case name:", case_name)
        print("Input:", repr(text))
        final_output = run_contract_analysis(text)
        comparison = compare_contract_case_result(expected, final_output)
        print("Module:", final_output["module"])
        print("OK:", final_output["ok"])
        if final_output.get("verdict"):
            print("Verdict status:", final_output["verdict"]["status"])
            print("Verdict title:", final_output["verdict"]["title"])
        if final_output["ok"]:
            summary = final_output.get("summary") or {}
            print("Risk level:", summary.get("risk_level"))
            print("Explanation:", summary.get("overall_explanation"))
            print("Actions count:", len(final_output.get("actions") or []))
            print("Missing clauses count:", len(final_output.get("missing_clauses") or []))
            print("Flagged clauses count:", len(final_output.get("flagged_clauses") or []))
        else:
            print("Error:", final_output.get("error"))
        print("Expected vs Actual match:", comparison["match"])
        print("Check details:", comparison["checks"])
        results.append(
            {
                "case_name": case_name,
                "ok": final_output.get("ok"),
                "risk_level": (final_output.get("summary") or {}).get("risk_level"),
                "verdict_status": (final_output.get("verdict") or {}).get("status"),
                "error": final_output.get("error"),
                "comparison": comparison,
            }
        )

    summary = summarize_contract_test_results(results)
    assertions = build_contract_test_assertions(summary)
    print()
    print("=== Contract Regression Summary ===")
    print("Total cases:", summary["total"])
    print("Success:", summary["success"])
    print("Failed:", summary["failed"])
    print("High risk:", summary["high_risk"])
    print("Medium risk:", summary["medium_risk"])
    print("Low risk:", summary["low_risk"])
    print("Unknown risk:", summary["unknown_risk"])
    print("Matched cases:", summary["matched_cases"])
    print("Mismatched cases:", summary["mismatched_cases"])
    print()
    print("Case results:")
    for item in summary["cases"]:
        print(
            f'- {item["case_name"]}: ok={item["ok"]}, '
            f'risk={item["risk_level"]}, verdict={item["verdict_status"]}, '
            f'match={item["comparison"]["match"]}, error={item["error"]}'
        )

    print()
    print("=== Contract Test Assertions ===")
    print("Passed:", assertions["passed"])
    print("Total cases:", assertions["total_cases"])
    print("Matched cases:", assertions["matched_cases"])
    print("Mismatched cases:", assertions["mismatched_cases"])
    if assertions["failed_case_names"]:
        print("Failed case names:")
        for name in assertions["failed_case_names"]:
            print("-", name)
    else:
        print("Failed case names: None")
    if assertions["failed_check_details"]:
        print("Failed check details:")
        for item in assertions["failed_check_details"]:
            print(f'- {item["case_name"]}: {item["checks"]}')
    else:
        print("Failed check details: None")

    if assertions["passed"]:
        print()
        print("FINAL TEST STATUS: PASS")
    else:
        print()
        print("FINAL TEST STATUS: FAIL")
