"""
Phase 3：合同分析子模块（与项目根目录 ``contract_*.py`` 管线区分，用于新阶段扩展）。
"""

from __future__ import annotations

from .contract_analyzer import analyze_contract_text
from .contract_document_reader import (
    MINIMAL_CONTRACT_PDF_TEXT_BYTES,
    ContractReadOutcome,
    extract_contract_text,
    extract_contract_text_outcome,
    infer_contract_source_type_from_path,
    read_contract_from_docx,
    read_contract_from_pdf,
    read_contract_from_txt,
)
from .contract_explainer import explain_contract_analysis, format_contract_analysis_output
from .contract_models import (
    ContractAnalysisMeta,
    ContractAnalysisResult,
    ContractExplainBundle,
    ContractExplainResult,
    ContractInput,
    ContractPhase3PipelineResult,
    ContractPresentationBundle,
    ContractRiskItem,
    ContractSourceType,
    coerce_contract_source_type,
)
from .contract_rules import BASIC_CONTRACT_RISK_RULES
from .demo_contract_document_readers import (
    run_contract_file_demo,
    sample_contract_paths,
    test_contract_document_readers,
)
from .demo_contract_file_analysis import (
    run_contract_file_analysis_demo,
    validate_contract_file_analysis_demo,
)
from .demo_contract_samples import (
    run_contract_analysis_demo,
    test_contract_analysis_samples,
    validate_contract_analysis_samples,
)
from .presentation import build_contract_presentation, format_contract_analysis_cli_report
from .service import (
    analyze_contract,
    analyze_contract_file,
    analyze_contract_file_with_explain,
    analyze_contract_with_explain,
    build_contract_input_from_file,
)
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
    "ContractAnalysisMeta",
    "ContractAnalysisResult",
    "ContractExplainBundle",
    "ContractExplainResult",
    "ContractInput",
    "ContractPhase3PipelineResult",
    "ContractPresentationBundle",
    "ContractReadOutcome",
    "ContractRiskItem",
    "ContractSourceType",
    "coerce_contract_source_type",
    "MINIMAL_CONTRACT_PDF_TEXT_BYTES",
    "extract_contract_text",
    "extract_contract_text_outcome",
    "infer_contract_source_type_from_path",
    "read_contract_from_docx",
    "read_contract_from_pdf",
    "read_contract_from_txt",
    "analyze_contract",
    "analyze_contract_file",
    "analyze_contract_file_with_explain",
    "analyze_contract_text",
    "analyze_contract_with_explain",
    "build_contract_input_from_file",
    "build_contract_presentation",
    "explain_contract_analysis",
    "format_contract_analysis_cli_report",
    "format_contract_analysis_output",
    "run_contract_analysis_demo",
    "run_contract_file_analysis_demo",
    "run_contract_file_demo",
    "sample_contract_paths",
    "SAMPLE_CONTRACT_DEPOSIT_HEAVY",
    "SAMPLE_CONTRACT_HIDDEN_FEES_PENALTY",
    "SAMPLE_CONTRACT_HIGH_RISK",
    "SAMPLE_CONTRACT_MEDIUM_RISK",
    "SAMPLE_CONTRACT_MISSING_NOTICE_REPAIR",
    "SAMPLE_CONTRACT_SAFE",
    "SAMPLE_CONTRACT_UNFAIR_ENTRY",
    "test_contract_analysis_samples",
    "test_contract_document_readers",
    "validate_contract_analysis_samples",
    "validate_contract_file_analysis_demo",
]
