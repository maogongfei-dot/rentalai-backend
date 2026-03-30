"""
Phase 3 合同分析：对外服务包装（供 API / CLI 调用，与 MVP 房源流程隔离）。
"""

from __future__ import annotations

from typing import cast

from .contract_analyzer import analyze_contract_text as _analyze_contract_text
from .contract_explainer import explain_contract_analysis
from .contract_models import (
    ContractAnalysisResult,
    ContractInput,
    ContractPhase3PipelineResult,
    coerce_contract_source_type,
)
from .presentation import build_contract_presentation


def analyze_contract(
    *,
    contract_text: str,
    monthly_rent: float | None = None,
    deposit_amount: float | None = None,
    fixed_term_months: int | None = None,
    source_type: str = "text",
    source_name: str | None = None,
) -> ContractAnalysisResult:
    """
    合同分析统一入口：返回 ``ContractAnalysisResult`` 形状（含 ``meta``）。

    与根目录 ``contract_text_analyzer``（Phase B）区分：本函数仅走 ``contract_analysis`` 规则引擎。
    """
    inp = ContractInput(
        contract_text=contract_text or "",
        monthly_rent=monthly_rent,
        deposit_amount=deposit_amount,
        fixed_term_months=fixed_term_months,
        source_type=coerce_contract_source_type(source_type),
        source_name=source_name,
    )
    return _analyze_contract_text(inp)


def analyze_contract_with_explain(
    *,
    contract_text: str,
    monthly_rent: float | None = None,
    deposit_amount: float | None = None,
    fixed_term_months: int | None = None,
    source_type: str = "text",
    source_name: str | None = None,
) -> ContractPhase3PipelineResult:
    """
    完整 Phase 3 输出（两层 + 展示层），形状见 ``ContractPhase3PipelineResult``：

    - ``structured_analysis``：第一层（含 ``meta``）。
    - ``explain``：第二层，人话说明。
    - ``presentation``：产品化分段与 ``plain_text``。
    """
    base = analyze_contract(
        contract_text=contract_text,
        monthly_rent=monthly_rent,
        deposit_amount=deposit_amount,
        fixed_term_months=fixed_term_months,
        source_type=source_type,
        source_name=source_name,
    )
    ex = explain_contract_analysis(base)
    pres = build_contract_presentation(base, ex)
    return cast(
        ContractPhase3PipelineResult,
        {
            "structured_analysis": base,
            "explain": ex,
            "presentation": pres,
        },
    )
