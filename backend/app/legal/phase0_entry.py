"""
Phase 0 standard entry point for future AI / orchestration (wrapper only).

Chains: LegalInput → analyze_legal_compliance → build_legal_analysis_response
→ phase0_unified + phase0_natural_text, without changing rule logic.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .compliance_engine import analyze_legal_compliance
from .compliance_types import ComplianceAnalysisResult, LegalInput
from .legal_result_builder import build_legal_analysis_response
from .phase0_unified_display import build_risk_badge, normalize_raw_risk_level


def _suggested_followup(raw_level: str) -> str:
    rl = normalize_raw_risk_level(raw_level)
    if rl == "high":
        return (
            "You may also want to compare these terms with another property listing or "
            "ask a housing adviser to review the full agreement before you commit."
        )
    if rl == "medium":
        return (
            "You may also want to gather missing details in writing and keep a dated record "
            "of what was agreed."
        )
    return (
        "You may also want to compare the property terms with another listing or review "
        "deposit protection details when relevant."
    )


def _failure(
    *,
    input_text: str,
    error_message: str,
    error_code: str,
) -> dict[str, Any]:
    if error_code == "empty":
        display = (
            "I could not analyse this issue because no valid input was provided."
        )
    else:
        display = f"I could not complete the analysis: {error_message}"
    return {
        "module": "phase0_legal_risk",
        "success": False,
        "input_text": input_text,
        "error": error_message,
        "error_code": error_code,
        "display_text": display,
        "raw_result": None,
        "normalized_result": None,
        "risk_level": "unknown",
        "risk_badge": build_risk_badge("unknown"),
        "recommended_actions": [],
        "legal_basis": [],
        "suggested_followup": "",
        "next_step_hint": "",
        "legal_compliance": None,
    }


def run_phase0_analysis(
    text: str,
    *,
    jurisdiction: str = "england",
    target_date: str | None = None,
    source_type: str = "contract_clause",
    rule_ids: list[str] | None = None,
) -> dict[str, Any]:
    """
    Single entry for Phase 0 legal/risk screening (text in → structured + display out).

    Future home-page AI can call: ``result = run_phase0_analysis(user_text)``.
    """
    trimmed = (text or "").strip()
    if not trimmed:
        return _failure(
            input_text=text or "",
            error_message="No valid input provided.",
            error_code="empty",
        )

    try:
        payload = LegalInput(
            text=trimmed,
            rule_ids=rule_ids,
            jurisdiction=jurisdiction,
            target_date=target_date,
            source_type=source_type,
        )
        compliance: ComplianceAnalysisResult = analyze_legal_compliance(payload)
        legal_response = build_legal_analysis_response(compliance)
    except Exception as exc:
        return _failure(
            input_text=trimmed,
            error_message=str(exc),
            error_code="analysis_error",
        )

    norm = legal_response.get("phase0_unified")
    if not isinstance(norm, dict):
        norm = {}

    raw_level = str(norm.get("raw_level") or "unknown")
    follow = _suggested_followup(raw_level)

    return {
        "module": "phase0_legal_risk",
        "success": True,
        "input_text": trimmed,
        "error": None,
        "error_code": None,
        "raw_result": asdict(compliance),
        "normalized_result": norm,
        "display_text": str(legal_response.get("phase0_natural_text") or ""),
        "risk_level": raw_level,
        "risk_badge": str(norm.get("risk_badge") or build_risk_badge(raw_level)),
        "recommended_actions": list(norm.get("recommended_actions") or []),
        "legal_basis": list(norm.get("legal_basis") or []),
        "suggested_followup": follow,
        "next_step_hint": follow,
        "legal_compliance": legal_response,
    }
