"""Dataclasses for legal compliance analysis (Phase 0 compliance engine)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LegalInput:
    text: str
    rule_ids: list[str] | None = None
    jurisdiction: str = "england"
    target_date: str | None = None
    source_type: str = "contract_clause"


@dataclass
class RuleEvaluation:
    rule_id: str
    title: str
    is_legal: bool | None
    risk_level: str
    explanation_plain: str
    matched_red_flags: list[str]
    matched_key_points: list[str]
    confidence: float


@dataclass
class ComplianceAnalysisResult:
    jurisdiction: str
    target_date: str | None
    source_type: str
    overall_is_legal: bool | None
    overall_risk_level: str
    summary_plain: str
    disclaimer: str
    rule_results: list[RuleEvaluation] = field(default_factory=list)
