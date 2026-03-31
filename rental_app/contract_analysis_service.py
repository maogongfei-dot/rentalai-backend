"""
Phase 4：合同分析正式对外入口。

API、脚本与前端应优先通过本模块调用，**不要**直接引用 ``contract_analysis.contract_analyzer`` /
``contract_explainer`` 内部实现（便于替换与单测打桩）。

返回键名统一为 ``analysis_result`` / ``explain_result``（可选 ``presentation``），与
``contract_analysis.service`` 中的 ``structured_analysis`` / ``explain`` 对应同一数据。
"""

from __future__ import annotations

import os
from typing import TypedDict, cast

from contract_analysis.contract_models import (
    ContractAnalysisResult,
    ContractExplainResult,
    ContractPhase3PipelineResult,
    ContractPresentationBundle,
)
from contract_analysis.service import (
    analyze_contract_file_with_explain,
    analyze_contract_with_explain,
)


class ContractAnalysisFacadeResult(TypedDict, total=False):
    """正式门面返回值（与管线内容一致，仅键名面向 API）。"""

    analysis_result: ContractAnalysisResult
    explain_result: ContractExplainResult
    presentation: ContractPresentationBundle


def _facade_from_pipeline(full: ContractPhase3PipelineResult) -> ContractAnalysisFacadeResult:
    return cast(
        ContractAnalysisFacadeResult,
        {
            "analysis_result": full["structured_analysis"],
            "explain_result": full["explain"],
            "presentation": full.get("presentation"),
        },
    )


def analyze_contract_text(
    *,
    contract_text: str,
    monthly_rent: float | None = None,
    deposit_amount: float | None = None,
    fixed_term_months: int | None = None,
    source_type: str = "text",
    source_name: str | None = None,
) -> ContractAnalysisFacadeResult:
    """
    内存文本 → 结构化分析 + explain + 展示层（封装 ``analyze_contract_with_explain``）。

    返回:
        - **analysis_result**: 第一层 ``ContractAnalysisResult``
        - **explain_result**: ``ContractExplainResult``
        - **presentation**: 分段展示（与 ``build_contract_presentation`` 一致）
    """
    full = analyze_contract_with_explain(
        contract_text=contract_text,
        monthly_rent=monthly_rent,
        deposit_amount=deposit_amount,
        fixed_term_months=fixed_term_months,
        source_type=source_type,
        source_name=source_name,
    )
    return _facade_from_pipeline(full)


def analyze_contract_file(
    *,
    file_path: str | os.PathLike[str],
    monthly_rent: float | None = None,
    deposit_amount: float | None = None,
    fixed_term_months: int | None = None,
    source_type: str | None = None,
    source_name: str | None = None,
) -> ContractAnalysisFacadeResult:
    """
    文件路径（txt/pdf/docx）→ 抽取文本 → 与 :func:`analyze_contract_text` 相同管线、相同返回键。

    ``source_name``：可选，写入 ``meta.source_name``（上传场景传入原始文件名）。
    """
    full = analyze_contract_file_with_explain(
        file_path=file_path,
        monthly_rent=monthly_rent,
        deposit_amount=deposit_amount,
        fixed_term_months=fixed_term_months,
        source_type=source_type,
        source_name=source_name,
    )
    return _facade_from_pipeline(full)
