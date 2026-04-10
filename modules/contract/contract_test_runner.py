"""
Contract analysis demo, batch regression, expected vs actual checks, and assertions (Phase 3 Part 22).

Uses ``run_contract_analysis`` from ``contract_service`` (Part 24); presenter for display (Part 25).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from modules.contract.contract_presenter import (
    build_analysis_completeness,
    build_blocking_factors,
    build_confidence_reason,
    build_direct_answer,
    build_direct_answer_short,
    build_final_display,
    build_human_confidence_notice,
    build_human_decision_factors_notice,
    build_human_missing_info_guidance,
    build_human_urgency_notice,
    build_key_decision_drivers,
    build_missing_information,
    build_priority_actions,
    build_recommended_decision,
    build_result_confidence,
    build_supporting_factors,
    build_urgency_level,
    build_urgency_reason,
    format_contract_result_text,
    print_contract_result,
)
from modules.contract.contract_service import (
    build_human_evidence_checklist,
    build_human_next_steps,
    build_human_risk_warning,
    run_contract_analysis,
)


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


def run_contract_human_output_test() -> None:
    """
    Phase 4 Part 4 — human_next_steps / human_evidence_checklist / human_risk_warning wiring.

    Asserts stable types, safe behaviour on empty input, and prints one sample for CLI review.
    """
    assert build_human_next_steps({}) == []
    assert build_human_risk_warning({}) == ""
    assert isinstance(build_human_evidence_checklist({}), list)

    empty = run_contract_analysis("")
    assert isinstance(empty.get("human_next_steps"), list)
    assert isinstance(empty.get("human_evidence_checklist"), list)
    assert isinstance(empty.get("human_risk_warning"), str)

    sample = (
        "The deposit is £500. The tenant may terminate with notice. "
        "Repair and maintenance obligations apply."
    )
    out = run_contract_analysis(sample)
    assert isinstance(out.get("human_next_steps"), list)
    assert isinstance(out.get("human_evidence_checklist"), list)
    assert isinstance(out.get("human_risk_warning"), str)
    assert len(out.get("human_next_steps") or []) >= 1

    print()
    print("=== Contract Human Output Smoke (Phase 4 Part 4) ===")
    print("human_risk_warning:", (out.get("human_risk_warning") or "")[:160])
    print("human_next_steps count:", len(out.get("human_next_steps") or []))
    print("human_evidence_checklist count:", len(out.get("human_evidence_checklist") or []))
    print()
    print("--- Presenter preview ---")
    print_contract_result(out)
    print("--- End preview ---")


def run_contract_final_display_test() -> None:
    """
    Phase 4 Part 5 — ``final_display`` dict, safe fallbacks, presenter unified vs legacy paths.
    """
    fd0 = build_final_display({})
    assert isinstance(fd0, dict)
    assert "title" in fd0 and "meta_block" in fd0

    sparse = run_contract_analysis("deposit")
    fd = sparse.get("final_display")
    assert isinstance(fd, dict)
    assert isinstance(fd.get("summary_block"), str)

    minimal: dict[str, Any] = {"ok": True, "summary": {}, "verdict": {}}
    assert isinstance(build_final_display(minimal).get("summary_block"), str)

    legacy = dict(sparse)
    legacy.pop("final_display", None)
    legacy_text = format_contract_result_text(legacy)
    assert "=== Contract Analysis Result ===" in legacy_text

    rich = run_contract_analysis(
        "The deposit is £500. Termination notice 2 months. Repair obligations."
    )
    rfd = rich.get("final_display")
    if isinstance(rfd, dict) and isinstance(rfd.get("meta_block"), dict):
        rfd["meta_block"]["source"] = "cli_test"
        rfd["meta_block"]["request_id"] = str(uuid.uuid4())
        rfd["meta_block"]["timestamp"] = datetime.utcnow().isoformat()
    print()
    print("=== Contract Final Display (Phase 4 Part 5) ===")
    print_contract_result(rich)
    print("=== End final display demo ===")


def run_contract_completeness_test() -> None:
    """Phase 4 Part 6 — analysis_completeness / missing_information / guidance."""
    assert build_analysis_completeness({}) == "low"
    assert build_missing_information({}) == []
    assert build_human_missing_info_guidance({}) == ""

    low = run_contract_analysis("deposit")
    assert low.get("analysis_completeness") == "low"
    assert isinstance(low.get("missing_information"), list)
    assert isinstance(low.get("human_missing_info_guidance"), str)
    fd_low = low.get("final_display") or {}
    assert "completeness_block" in fd_low

    high_text = (
        "The tenant shall pay rent monthly. The deposit is £800 held in a scheme. "
        "Notice period is two months. The landlord may not terminate without notice. "
        "Repair and maintenance obligations are set out in the schedule. "
        "Fees may apply for late payment. Termination and end of tenancy terms apply."
    )
    hi = run_contract_analysis(high_text)
    assert hi.get("analysis_completeness") in ("high", "medium")

    med = run_contract_analysis("Rent is £500 monthly. Deposit £400. Notice one month.")
    assert med.get("analysis_completeness") in ("low", "medium", "high")

    print()
    print("=== Completeness demo (Phase 4 Part 6) — low input ===")
    print("analysis_completeness:", low.get("analysis_completeness"))
    print_contract_result(low)
    print()
    print("=== Completeness demo — richer input ===")
    print("analysis_completeness:", hi.get("analysis_completeness"))
    print_contract_result(hi)
    print("=== End completeness demo ===")


def run_contract_direct_answer_test() -> None:
    """Phase 4 Part 7 — direct_answer / recommended_decision / final_display blocks."""
    assert build_recommended_decision({}) == "pause"
    assert isinstance(build_direct_answer({}), str)
    assert isinstance(build_direct_answer_short({}), str)

    pause_case = run_contract_analysis("deposit")
    assert pause_case.get("recommended_decision") == "pause"
    fd_p = pause_case.get("final_display") or {}
    assert fd_p.get("decision_block") == "建议先暂停确认"
    assert _fd_has_direct(pause_case)

    esc_text = (
        "The tenant must pay a non-refundable fee. "
        "The landlord may terminate the agreement immediately without notice."
    )
    esc = run_contract_analysis(esc_text)
    assert esc.get("recommended_decision") == "escalate"
    assert (esc.get("final_display") or {}).get("decision_block") == "建议升级处理"

    print()
    print("=== Direct answer demo — pause (short input) ===")
    print("recommended_decision:", pause_case.get("recommended_decision"))
    print_contract_result(pause_case)
    print()
    print("=== Direct answer demo — escalate (high-risk wording) ===")
    print("recommended_decision:", esc.get("recommended_decision"))
    print_contract_result(esc)
    print("=== End direct answer demo ===")


def _fd_has_direct(out: dict[str, Any]) -> bool:
    fd = out.get("final_display")
    return isinstance(fd, dict) and bool((fd.get("direct_answer_block") or "").strip())


def run_contract_confidence_test() -> None:
    """Phase 4 Part 8 — result_confidence / confidence_reason / human_confidence_notice."""
    assert build_result_confidence({}) == "low"
    assert isinstance(build_confidence_reason({}), str)
    assert isinstance(build_human_confidence_notice({}), str)

    low = run_contract_analysis("deposit")
    assert low.get("result_confidence") == "low"
    assert (low.get("final_display") or {}).get("confidence_block") == "参考度较低"

    high_text = (
        "The tenant shall pay rent monthly. The deposit is £800 held in a scheme. "
        "Notice period is two months. The landlord may not terminate without notice. "
        "Repair and maintenance obligations are set out in the schedule. "
        "Fees may apply for late payment. Termination and end of tenancy terms apply."
    )
    hi = run_contract_analysis(high_text)
    assert hi.get("result_confidence") in ("high", "medium")

    risky_short = "non-refundable fee. The landlord may terminate immediately without notice."
    rs = run_contract_analysis(risky_short)
    if rs.get("analysis_completeness") == "low":
        assert rs.get("result_confidence") == "low"

    print()
    print("=== Confidence demo — low (short input) ===")
    print("result_confidence:", low.get("result_confidence"))
    print_contract_result(low)
    print()
    print("=== Confidence demo — richer input ===")
    print("result_confidence:", hi.get("result_confidence"))
    print_contract_result(hi)
    print("=== End confidence demo ===")


def _synthetic_low_urgency_envelope() -> dict[str, Any]:
    """Pipeline rarely yields proceed+low risk; this envelope exercises urgency_level=low paths."""
    return {
        "ok": True,
        "module": "contract",
        "summary": {
            "risk_level": "low",
            "overall_explanation": "（演示）低风险、可继续推进的示例。",
            "human_explanation": "",
        },
        "verdict": {"status": "acceptable_with_review", "title": "", "message": ""},
        "details": {},
        "actions": [],
        "missing_clauses": [],
        "flagged_clauses": [],
        "recommended_decision": "proceed",
        "analysis_completeness": "high",
        "human_next_steps": ["先核对租期与押金条款。", "保留重要沟通记录。"],
        "human_evidence_checklist": [],
        "human_risk_warning": "",
        "missing_information": [],
        "human_missing_info_guidance": "",
        "direct_answer": "",
        "direct_answer_short": "",
        "result_confidence": "medium",
        "confidence_reason": "",
        "human_confidence_notice": "",
    }


def run_contract_urgency_test() -> None:
    """Phase 4 Part 9 — urgency_level / urgency_reason / priority_actions / human_urgency_notice."""
    assert build_urgency_level({}) == "medium"
    assert isinstance(build_urgency_reason({}), str)
    assert isinstance(build_priority_actions({}), list)
    assert len(build_priority_actions({})) <= 3
    assert isinstance(build_human_urgency_notice({}), str)

    dup_case = {
        "ok": True,
        "recommended_decision": "caution",
        "human_next_steps": ["先保存合同。", "先保存合同。", "先标出条款。", "第四条再读一遍。"],
    }
    pa_dup = build_priority_actions(dup_case)
    assert len(pa_dup) <= 3
    assert len(pa_dup) == len(set(pa_dup))

    pause_high_risk_low_info = {
        "ok": True,
        "recommended_decision": "pause",
        "analysis_completeness": "low",
        "summary": {"risk_level": "high"},
        "human_next_steps": [],
        "human_risk_warning": "材料不齐时先别急着升级。",
    }
    assert build_urgency_level(pause_high_risk_low_info) == "medium"

    low_syn = _synthetic_low_urgency_envelope()
    assert build_urgency_level(low_syn) == "low"
    low_syn["urgency_level"] = build_urgency_level(low_syn)
    low_syn["urgency_reason"] = build_urgency_reason(low_syn)
    low_syn["priority_actions"] = build_priority_actions(low_syn)
    low_syn["human_urgency_notice"] = build_human_urgency_notice(low_syn)
    low_syn["final_display"] = build_final_display(low_syn)
    fd_lo = low_syn.get("final_display") or {}
    assert fd_lo.get("urgency_block") == "可按正常节奏处理"
    assert len(fd_lo.get("priority_actions_block") or []) <= 3
    txt_lo = format_contract_result_text(low_syn)
    assert "可按正常节奏处理" in txt_lo
    assert "处理紧急度：" in txt_lo
    assert "urgency_level" not in txt_lo

    high_text = (
        "The tenant must pay a non-refundable fee. "
        "The landlord may terminate the agreement immediately without notice."
    )
    hi = run_contract_analysis(high_text)
    assert hi.get("urgency_level") == "high"
    fd_hi = hi.get("final_display") or {}
    assert fd_hi.get("urgency_block") == "需要尽快处理"
    assert isinstance(fd_hi.get("priority_actions_block"), list)
    assert len((fd_hi.get("priority_actions_block") or [])) <= 3
    txt_hi = format_contract_result_text(hi)
    assert "需要尽快处理" in txt_hi
    assert "优先先做这几件事：" in txt_hi
    assert "urgency_level" not in txt_hi

    med = run_contract_analysis("Rent is £500 monthly. Deposit £400.")
    assert med.get("urgency_level") in ("high", "medium", "low")

    print()
    print("=== Urgency demo — low (synthetic proceed + low risk, shows 可按正常节奏处理) ===")
    print("urgency_level (envelope):", low_syn.get("urgency_level"))
    print_contract_result(low_syn)
    print()
    print("=== Urgency demo — high (live pipeline, escalate-style wording) ===")
    print("urgency_level:", hi.get("urgency_level"))
    print_contract_result(hi)
    print("=== End urgency demo ===")


def run_contract_decision_factors_test() -> None:
    """Phase 4 Part 10 — supporting_factors / blocking_factors / key_decision_drivers / notice."""
    assert build_supporting_factors({}) == []
    assert build_blocking_factors({}) == []
    assert len(build_key_decision_drivers({})) == 0
    assert isinstance(build_human_decision_factors_notice({}), str)

    dup_sf = {
        "ok": True,
        "recommended_decision": "caution",
        "direct_answer": "x",
        "verdict": {"status": "review_needed"},
        "human_next_steps": ["a"],
        "summary": {"risk_level": "medium"},
    }
    sf = build_supporting_factors(dup_sf)
    assert len(sf) == len(set(sf))
    assert 2 <= len(sf) <= 5

    pause_case = {
        "ok": True,
        "recommended_decision": "pause",
        "analysis_completeness": "low",
        "missing_information": ["租金条款"],
        "result_confidence": "low",
        "human_next_steps": [],
    }
    bf_pause = build_blocking_factors(pause_case)
    assert bf_pause
    assert any("缺口" in x or "完整" in x for x in bf_pause)

    esc_case = {
        "ok": True,
        "recommended_decision": "escalate",
        "summary": {"risk_level": "high"},
        "human_risk_warning": "不要拖太久",
        "flagged_clauses": ["x"],
        "urgency_level": "high",
    }
    bf_esc = build_blocking_factors(esc_case)
    assert bf_esc
    assert any("正式" in x or "风险" in x for x in bf_esc)

    kd = build_key_decision_drivers(esc_case)
    assert len(kd) <= 3

    pause_live = run_contract_analysis("deposit")
    assert pause_live.get("recommended_decision") == "pause"
    fd_p = pause_live.get("final_display") or {}
    assert isinstance(fd_p.get("supporting_factors_block"), list)
    assert isinstance(fd_p.get("blocking_factors_block"), list)
    assert len(fd_p.get("key_drivers_block") or []) <= 3

    esc_text = (
        "The tenant must pay a non-refundable fee. "
        "The landlord may terminate the agreement immediately without notice."
    )
    esc_live = run_contract_analysis(esc_text)
    assert esc_live.get("recommended_decision") == "escalate"
    txt_e = format_contract_result_text(esc_live)
    assert "为什么是这个结果：" in txt_e
    assert "当前对你有利的因素：" in txt_e
    assert "当前卡住你的因素：" in txt_e
    assert "判断说明：" in txt_e
    assert "supporting_factors" not in txt_e

    print()
    print("=== Decision factors demo — pause (short input) ===")
    print("recommended_decision:", pause_live.get("recommended_decision"))
    print_contract_result(pause_live)
    print()
    print("=== Decision factors demo — escalate (high-risk wording) ===")
    print("recommended_decision:", esc_live.get("recommended_decision"))
    print_contract_result(esc_live)
    print("=== End decision factors demo ===")

