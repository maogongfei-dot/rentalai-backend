"""Unified formatting for legal compliance outputs (Phase 0 output layer)."""

from __future__ import annotations

import re
from typing import Any

from .compliance_types import ComplianceAnalysisResult, RuleEvaluation

_EMPTY_EXPLANATION_FALLBACK = (
    "This clause may need further review because the wording is unclear."
)


def format_legal_status_label(is_legal: bool | None) -> str:
    if is_legal is True:
        return "Likely compliant"
    if is_legal is False:
        return "Potentially non-compliant"
    return "Needs review"


def format_risk_label(risk_level: str) -> str:
    key = (risk_level or "").strip().lower()
    if key == "low":
        return "Low risk"
    if key == "medium":
        return "Medium risk"
    if key == "high":
        return "High risk"
    return "Needs review"


def normalize_explanation_text(text: str) -> str:
    if text is None or not str(text).strip():
        return _EMPTY_EXPLANATION_FALLBACK
    s = re.sub(r"\s+", " ", str(text).strip())
    return s


def _normalize_summary_plain(text: str) -> str:
    """Strip and collapse whitespace to one paragraph (no empty fallback)."""
    if text is None or not str(text).strip():
        return ""
    return re.sub(r"\s+", " ", str(text).strip())


def build_rule_output(rule_result: RuleEvaluation) -> dict[str, Any]:
    return {
        "rule_id": rule_result.rule_id,
        "title": rule_result.title,
        "legal_status": format_legal_status_label(rule_result.is_legal),
        "risk_level": format_risk_label(rule_result.risk_level),
        "explanation_plain": normalize_explanation_text(rule_result.explanation_plain),
        "matched_red_flags": list(rule_result.matched_red_flags),
        "matched_key_points": list(rule_result.matched_key_points),
        "confidence": rule_result.confidence,
    }


def build_overall_output(result: ComplianceAnalysisResult) -> dict[str, Any]:
    rule_results = [build_rule_output(r) for r in result.rule_results]
    return {
        "overall_legal_status": format_legal_status_label(result.overall_is_legal),
        "overall_risk_level": format_risk_label(result.overall_risk_level),
        "summary_plain": _normalize_summary_plain(result.summary_plain),
        "disclaimer": result.disclaimer,
        "rule_results": rule_results,
    }
