"""
Phase 3：合同分析子模块（与项目根目录 ``contract_*.py`` 管线区分，用于新阶段扩展）。
"""

from __future__ import annotations

from .contract_analyzer import analyze_contract_text
from .contract_explainer import explain_contract_analysis, format_contract_analysis_output
from .contract_models import (
    ContractAnalysisResult,
    ContractExplainBundle,
    ContractInput,
    ContractPhase3PipelineResult,
    ContractPresentationBundle,
    ContractRiskItem,
)
from .contract_rules import BASIC_CONTRACT_RISK_RULES
from .demo_contract_samples import (
    run_contract_analysis_demo,
    test_contract_analysis_samples,
    validate_contract_analysis_samples,
)
from .presentation import build_contract_presentation, format_contract_analysis_cli_report
from .service import analyze_contract, analyze_contract_with_explain
from .sample_contracts_data import (
    SAMPLE_CONTRACT_DEPOSIT_HEAVY,
    SAMPLE_CONTRACT_HIDDEN_FEES_PENALTY,
    SAMPLE_CONTRACT_HIGH_RISK,
    SAMPLE_CONTRACT_MEDIUM_RISK,
    SAMPLE_CONTRACT_MISSING_NOTICE_REPAIR,
    SAMPLE_CONTRACT_SAFE,
    SAMPLE_CONTRACT_UNFAIR_ENTRY,
)

__all__ = [
    "BASIC_CONTRACT_RISK_RULES",
    "ContractAnalysisResult",
    "ContractExplainBundle",
    "ContractInput",
    "ContractPhase3PipelineResult",
    "ContractPresentationBundle",
    "ContractRiskItem",
    "analyze_contract",
    "analyze_contract_text",
    "analyze_contract_with_explain",
    "build_contract_presentation",
    "explain_contract_analysis",
    "format_contract_analysis_cli_report",
    "format_contract_analysis_output",
    "run_contract_analysis_demo",
    "SAMPLE_CONTRACT_DEPOSIT_HEAVY",
    "SAMPLE_CONTRACT_HIDDEN_FEES_PENALTY",
    "SAMPLE_CONTRACT_HIGH_RISK",
    "SAMPLE_CONTRACT_MEDIUM_RISK",
    "SAMPLE_CONTRACT_MISSING_NOTICE_REPAIR",
    "SAMPLE_CONTRACT_SAFE",
    "SAMPLE_CONTRACT_UNFAIR_ENTRY",
    "test_contract_analysis_samples",
    "validate_contract_analysis_samples",
]
