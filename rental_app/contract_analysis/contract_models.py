"""
Phase 3 合同分析：输入与结构化数据模型。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, TypedDict


@dataclass
class ContractInput:
    """合同分析入口入参（最小字段，后续可扩展）。"""

    contract_text: str
    monthly_rent: Optional[float] = None
    deposit_amount: Optional[float] = None
    fixed_term_months: Optional[int] = None


class ContractRiskItem(TypedDict, total=False):
    """单条风险（与 analyze_contract_text 返回的 risks 元素一致）。"""

    rule_id: str
    title: str
    severity: str
    reason: str


class ContractExplainBundle(TypedDict, total=False):
    """explain_contract_analysis 输出。"""

    overall_conclusion: str
    key_risk_summary: str
    missing_clause_summary: str
    action_advice: list[str]


class ContractAnalysisResult(TypedDict, total=False):
    """analyze_contract_text 返回结构（仅第一层）。"""

    summary: str
    risks: list[ContractRiskItem]
    missing_items: list[str]
    recommendations: list[str]
    detected_topics: list[str]


class ContractPresentationBundle(TypedDict, total=False):
    """build_contract_presentation 输出（展示层）。"""

    product_title: str
    phase: str
    decision_style: str
    layers: dict[str, str]
    sections: list[dict[str, Any]]
    plain_text: str


class ContractPhase3PipelineResult(TypedDict, total=False):
    """analyze_contract_with_explain 完整返回（两层 + presentation）。"""

    structured_analysis: ContractAnalysisResult
    explain: ContractExplainBundle
    presentation: ContractPresentationBundle
