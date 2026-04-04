"""Builds canonical legal compliance response dicts (Phase 0 output layer)."""

from __future__ import annotations

from typing import Any

from .compliance_engine import build_disclaimer
from .compliance_types import ComplianceAnalysisResult
from .output_formatter import build_overall_output


def build_legal_analysis_response(result: ComplianceAnalysisResult) -> dict[str, Any]:
    overall_block = build_overall_output(result)
    rule_results = overall_block["rule_results"]
    overall_inner = {
        "overall_legal_status": overall_block["overall_legal_status"],
        "overall_risk_level": overall_block["overall_risk_level"],
        "summary_plain": overall_block["summary_plain"],
        "disclaimer": overall_block["disclaimer"],
    }
    return {
        "module": "legal_compliance",
        "has_legal_disclaimer": True,
        "overall": overall_inner,
        "rules": rule_results,
        "meta": {
            "jurisdiction": result.jurisdiction,
            "target_date": result.target_date,
            "source_type": result.source_type,
            "rule_count": len(rule_results),
        },
    }


def build_empty_legal_response(
    jurisdiction: str = "england",
    source_type: str = "contract_clause",
) -> dict[str, Any]:
    disclaimer = build_disclaimer()
    return {
        "module": "legal_compliance",
        "has_legal_disclaimer": True,
        "overall": {
            "overall_legal_status": "Needs review",
            "overall_risk_level": "Medium risk",
            "summary_plain": (
                "No clear legal rule match was found, so this text should be reviewed manually."
            ),
            "disclaimer": disclaimer,
        },
        "rules": [],
        "meta": {
            "jurisdiction": jurisdiction,
            "target_date": None,
            "source_type": source_type,
            "rule_count": 0,
        },
    }


def build_error_legal_response(
    error_message: str,
    jurisdiction: str = "england",
    source_type: str = "contract_clause",
) -> dict[str, Any]:
    disclaimer = build_disclaimer()
    return {
        "module": "legal_compliance",
        "has_legal_disclaimer": True,
        "overall": {
            "overall_legal_status": "Needs review",
            "overall_risk_level": "Medium risk",
            "summary_plain": (
                "The legal compliance check could not be completed automatically."
            ),
            "disclaimer": disclaimer,
        },
        "rules": [],
        "meta": {
            "jurisdiction": jurisdiction,
            "target_date": None,
            "source_type": source_type,
            "rule_count": 0,
            "error_message": error_message,
        },
    }
