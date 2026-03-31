"""
Phase 3 聚合入口（薄封装，无新逻辑）。

推荐 Phase 4 使用::

    from contract_analysis.entrypoints import (
        analyze_contract_with_explain,
        analyze_contract_file_with_explain,
        explain_contract_analysis,
    )

说明：``analyze_contract_text`` 需 ``ContractInput``；多数场景更宜用 ``analyze_contract`` / ``analyze_contract_with_explain``（见 ``service``）。
"""

from __future__ import annotations

from .contract_analyzer import analyze_contract_text
from .contract_explainer import explain_contract_analysis, format_contract_analysis_output
from .service import (
    analyze_contract,
    analyze_contract_file,
    analyze_contract_file_with_explain,
    analyze_contract_with_explain,
    build_contract_input_from_file,
)

__all__ = [
    "analyze_contract_text",
    "analyze_contract",
    "analyze_contract_with_explain",
    "analyze_contract_file",
    "analyze_contract_file_with_explain",
    "build_contract_input_from_file",
    "explain_contract_analysis",
    "format_contract_analysis_output",
]
