"""
Phase 3 合同分析：对外服务包装（供 API / CLI 调用，与 MVP 房源流程隔离）。
"""

from __future__ import annotations

from typing import Any

from .contract_analyzer import analyze_contract_text as _analyze_contract_text
from .contract_explainer import explain_contract_analysis
from .contract_models import ContractInput
from .presentation import build_contract_presentation


def analyze_contract(
    *,
    contract_text: str,
    monthly_rent: float | None = None,
    deposit_amount: float | None = None,
    fixed_term_months: int | None = None,
) -> dict[str, Any]:
    """
    合同分析统一入口：返回 summary / risks / missing_items / recommendations。

    与根目录 ``contract_text_analyzer``（Phase B）区分：本函数仅走 ``contract_analysis`` 规则引擎。
    """
    inp = ContractInput(
        contract_text=contract_text or "",
        monthly_rent=monthly_rent,
        deposit_amount=deposit_amount,
        fixed_term_months=fixed_term_months,
    )
    return _analyze_contract_text(inp)


def analyze_contract_with_explain(
    *,
    contract_text: str,
    monthly_rent: float | None = None,
    deposit_amount: float | None = None,
    fixed_term_months: int | None = None,
) -> dict[str, Any]:
    """
    完整 Phase 3 输出（两层 + 展示层）：

    - ``structured_analysis``：第一层，原始结构化结果（summary / risks / missing_items / …）。
    - ``explain``：第二层，人话说明（overall_conclusion / key_risk_summary / …）。
    - ``presentation``：产品化分段与 ``plain_text``，便于终端或前端直接展示。
    """
    base = analyze_contract(
        contract_text=contract_text,
        monthly_rent=monthly_rent,
        deposit_amount=deposit_amount,
        fixed_term_months=fixed_term_months,
    )
    ex = explain_contract_analysis(base)
    pres = build_contract_presentation(base, ex)
    return {
        "structured_analysis": base,
        "explain": ex,
        "presentation": pres,
    }
