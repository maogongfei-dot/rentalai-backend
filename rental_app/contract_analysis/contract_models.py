"""
Phase 3 合同分析：输入与结构化数据模型（骨架）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ContractInput:
    """合同分析入口入参（最小字段，后续可扩展）。"""

    contract_text: str
    monthly_rent: Optional[float] = None
    deposit_amount: Optional[float] = None
    fixed_term_months: Optional[int] = None
