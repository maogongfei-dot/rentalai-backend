"""
Phase 3：合同分析子模块（与项目根目录 ``contract_*.py`` 管线区分，用于新阶段扩展）。
"""

from __future__ import annotations

from .contract_analyzer import analyze_contract_text
from .contract_models import ContractAnalysisResult, ContractInput, ContractRiskItem
from .contract_rules import BASIC_CONTRACT_RISK_RULES
from .service import analyze_contract

__all__ = [
    "BASIC_CONTRACT_RISK_RULES",
    "ContractAnalysisResult",
    "ContractInput",
    "ContractRiskItem",
    "analyze_contract",
    "analyze_contract_text",
]
