"""
Phase 3 合同分析：输入与结构化数据模型。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, TypedDict


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


class ContractAnalysisResult(TypedDict, total=False):
    """analyze_contract_text 返回结构（便于类型标注与 IDE 提示）。"""

    summary: str
    risks: list[ContractRiskItem]
    missing_items: list[str]
    recommendations: list[str]
    detected_topics: list[str]
