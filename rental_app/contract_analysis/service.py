"""
Phase 3 合同分析：对外服务包装（供 API / CLI 调用，与 MVP 房源流程隔离）。
"""

from __future__ import annotations

from typing import Any

from .contract_analyzer import analyze_contract_text as _analyze_contract_text
from .contract_models import ContractInput


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
