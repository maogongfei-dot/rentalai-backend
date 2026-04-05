"""Phase 0 legal compliance rules library (England baseline + dated variants)."""

from __future__ import annotations

from .compliance_engine import (
    analyze_legal_compliance,
    build_disclaimer,
    compute_overall_result,
    detect_relevant_rules,
    evaluate_against_rule,
    normalize_text,
)
from .compliance_types import ComplianceAnalysisResult, LegalInput, RuleEvaluation
from .legal_result_builder import (
    build_empty_legal_response,
    build_error_legal_response,
    build_legal_analysis_response,
)
from .output_formatter import (
    build_overall_output,
    build_rule_output,
    format_legal_status_label,
    format_risk_label,
    normalize_explanation_text,
)
from .phase0_entry import run_phase0_analysis
from .phase0_natural_display import build_phase0_readable_report
from .phase0_unified_display import (
    build_phase0_unified_from_compliance_result,
    build_phase0_unified_from_legal_response,
    build_risk_badge,
    format_phase0_display_text,
    normalize_raw_risk_level,
)
from .rules_registry import get_rule as get_rule
from .rules_registry import get_ruleset as get_ruleset
from .rules_schema import LegalRule, LegalRuleSet, RuleCheckExample

__all__ = [
    "ComplianceAnalysisResult",
    "LegalInput",
    "LegalRule",
    "LegalRuleSet",
    "RuleCheckExample",
    "RuleEvaluation",
    "analyze_legal_compliance",
    "build_disclaimer",
    "build_empty_legal_response",
    "build_error_legal_response",
    "build_legal_analysis_response",
    "build_overall_output",
    "build_rule_output",
    "compute_overall_result",
    "detect_relevant_rules",
    "evaluate_against_rule",
    "format_legal_status_label",
    "format_risk_label",
    "get_rule",
    "get_ruleset",
    "normalize_explanation_text",
    "normalize_raw_risk_level",
    "normalize_text",
    "run_phase0_analysis",
    "build_phase0_readable_report",
    "build_phase0_unified_from_compliance_result",
    "build_phase0_unified_from_legal_response",
    "build_risk_badge",
    "format_phase0_display_text",
]
